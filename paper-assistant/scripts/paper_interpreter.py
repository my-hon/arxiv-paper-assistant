"""
论文解读模块
"""

from pathlib import Path
from typing import Any, Dict, Optional

import pdfplumber
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel, Field

from .arxiv_crawler import ArXivCrawler, PaperInfo
from .config import settings


# 解读结果数据模型
class PaperInterpretation(BaseModel):
    """论文结构化解读结果"""

    core_contributions: list[str] = Field(description="论文的核心贡献和创新点")
    research_methods: list[str] = Field(description="论文使用的研究方法和实验设计")
    datasets: list[str] = Field(description="实验使用的数据集")
    evaluation_metrics: list[str] = Field(description="使用的评估指标")
    main_results: list[str] = Field(description="主要实验结果和结论")
    limitations: list[str] = Field(description="论文的局限性和不足")
    future_work: list[str] = Field(description="未来的研究方向建议")


class PaperInterpreter:
    """论文解读器"""

    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.MODEL_NAME,
            temperature=0,
        )
        self.parser = PydanticOutputParser(pydantic_object=PaperInterpretation)

        # 构建提示模板
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是专业的学术论文解读助手。请仔细阅读论文内容，按照要求提取结构化信息。

解读要求：
1. 准确提取信息，不要添加幻觉内容
2. 每个要点简洁明了，不超过200字
3. 如果某个部分信息不明确，请返回["未明确说明"]
4. 严格按照输出格式返回JSON

输出格式要求：
{format_instructions}
""",
                ),
                (
                    "human",
                    """论文标题：{title}
论文摘要：{summary}
论文内容：
{content}

请对上述论文进行结构化解读。
""",
                ),
            ]
        )

        self.chain = self.prompt | self.llm | self.parser

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """从PDF文件中提取文本内容"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                # 提取前20页内容（避免过长）
                for page in pdf.pages[:20]:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"

            # 截断过长的文本
            if len(text) > 100000:
                text = text[:100000] + "\n[内容过长，已截断]"

            logger.info(f"PDF文本提取完成，共 {len(text)} 字符")
            return text
        except Exception as e:
            logger.error(f"PDF解析失败：{e}")
            raise

    async def interpret_paper(
        self,
        paper: PaperInfo,
        pdf_path: Optional[Path] = None,
        full_interpret: bool = False,
    ) -> Dict[str, Any]:
        """
        解读论文

        Args:
            paper: 论文信息
            pdf_path: PDF文件路径，如未提供则自动下载
            full_interpret: 是否进行完整解读（默认仅用摘要）

        Returns:
            结构化解读结果
        """
        # 下载PDF（如果需要完整解读且未提供路径）
        if full_interpret and not pdf_path:
            crawler = ArXivCrawler()
            pdf_path = await crawler.download_pdf(paper.paper_id)
            if not pdf_path:
                raise ValueError("PDF下载失败")

        # 获取内容
        if full_interpret and pdf_path:
            content = self.extract_text_from_pdf(pdf_path)
        else:
            content = paper.summary

        logger.info(f"开始解读论文：{paper.title}")

        try:
            result = self.chain.invoke(
                {
                    "title": paper.title,
                    "summary": paper.summary,
                    "content": content,
                    "format_instructions": self.parser.get_format_instructions(),
                }
            )

            logger.info("论文解读完成")
            return result.dict()
        except Exception as e:
            logger.error(f"论文解读失败：{e}")
            raise


def format_interpretation_result(paper: PaperInfo, result: Dict[str, Any]) -> str:
    """格式化解读结果为输出字符串"""
    output = [
        f"🔍 论文解读：{paper.title}",
        f"📄 arXiv ID：{paper.paper_id}",
        f"👥 作者：{', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}",
        f"📅 发表日期：{paper.published}",
        "=" * 70,
    ]

    sections = [
        ("🎯 核心贡献", "core_contributions"),
        ("🛠️ 研究方法", "research_methods"),
        ("📊 数据集", "datasets"),
        ("📈 评估指标", "evaluation_metrics"),
        ("✨ 主要结果", "main_results"),
        ("⚠️ 局限性", "limitations"),
        ("🔮 未来工作", "future_work"),
    ]

    for title, key in sections:
        items = result.get(key, [])
        if items and items != ["未明确说明"]:
            output.append(f"\n{title}:")
            for i, item in enumerate(items, 1):
                output.append(f"  {i}. {item}")
        else:
            output.append(f"\n{title}: 未明确说明")

    output.extend(["=" * 70, f"🔗 论文链接：https://arxiv.org/abs/{paper.paper_id}"])

    return "\n".join(output)


# 测试代码
if __name__ == "__main__":
    import asyncio

    crawler = ArXivCrawler()
    paper = crawler.get_paper_by_id("2310.06825")
    if paper:
        interpreter = PaperInterpreter()
        result = asyncio.run(interpreter.interpret_paper(paper))
        print(format_interpretation_result(paper, result))
