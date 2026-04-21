"""
论文解读模块
"""

import os
from typing import Dict, Optional

import pdfplumber
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings
from db.database import get_db
from db.models import Paper, PaperInterpretation


# 定义输出结构
class PaperInterpretationResult(BaseModel):
    core_contributions: list[str] = Field(description="论文的核心贡献点，分点列出")
    experimental_methods: list[str] = Field(description="论文使用的实验方法，分点列出")
    datasets: list[str] = Field(description="论文使用的数据集，分点列出")
    conclusions: list[str] = Field(description="论文的主要结论，分点列出")
    innovations: list[str] = Field(description="论文的创新点，分点列出")
    limitations: list[str] = Field(description="论文的局限性，分点列出")
    key_references: list[str] = Field(description="论文中提到的关键参考文献，分点列出")
    confidence_score: float = Field(description="解读结果的置信度，0-1之间")


class PaperInterpreter:
    """论文解读器"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            max_tokens=settings.MAX_TOKENS,
            temperature=settings.TEMPERATURE,
        )
        self.parser = PydanticOutputParser(pydantic_object=PaperInterpretationResult)

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        从PDF中提取文本
        :param pdf_path: PDF文件路径
        :return: 提取的文本内容
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF文件不存在: {pdf_path}")
            return None

        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"

            logger.info(f"成功提取PDF文本，共 {len(text)} 字符")
            return text

        except Exception as e:
            logger.error(f"提取PDF文本失败: {str(e)}")
            return None

    def _truncate_text(self, text: str, max_length: int = 15000) -> str:
        """截断文本，避免超过大模型上下文限制"""
        if len(text) <= max_length:
            return text

        # 优先保留摘要、介绍、方法、结论部分
        # 简单实现：取前7500和后7500字符
        truncated = text[:7500] + "\n\n...[内容截断]...\n\n" + text[-7500:]
        logger.warning(f"文本过长，已从 {len(text)} 字符截断为 {len(truncated)} 字符")
        return truncated

    async def interpret_paper(
        self, paper_id: str, use_abstract_only: bool = False
    ) -> Optional[Dict]:
        """
        解读论文
        :param paper_id: 论文ID
        :param use_abstract_only: 是否仅使用摘要进行解读（用于快速预览）
        :return: 解读结果
        """
        db = next(get_db())
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()

        if not paper:
            logger.error(f"论文不存在: {paper_id}")
            return None

        # 检查是否已解读过
        existing_interpretation = (
            db.query(PaperInterpretation)
            .filter(PaperInterpretation.paper_id == paper_id)
            .first()
        )

        if existing_interpretation:
            logger.info(f"论文已解读过: {paper_id}")
            return {
                "paper_id": paper_id,
                "core_contributions": existing_interpretation.core_contributions,
                "experimental_methods": existing_interpretation.experimental_methods,
                "datasets": existing_interpretation.datasets,
                "conclusions": existing_interpretation.conclusions,
                "innovations": existing_interpretation.innovations,
                "limitations": existing_interpretation.limitations,
                "references": existing_interpretation.references,
                "confidence_score": existing_interpretation.confidence_score,
                "interpretation_time": existing_interpretation.interpretation_time,
                "interpretation_model": existing_interpretation.interpretation_model,
            }

        # 获取文本内容
        if (
            use_abstract_only
            or not paper.pdf_path
            or not os.path.exists(paper.pdf_path)
        ):
            logger.info(f"使用摘要解读论文: {paper_id}")
            text = f"标题: {paper.title}\n\n作者: {', '.join(paper.authors)}\n\n摘要: {paper.abstract}"
        else:
            logger.info(f"使用全文解读论文: {paper_id}")
            full_text = self.extract_text_from_pdf(paper.pdf_path)
            if not full_text:
                logger.warning("全文提取失败，回退到使用摘要")
                text = f"标题: {paper.title}\n\n作者: {', '.join(paper.authors)}\n\n摘要: {paper.abstract}"
            else:
                text = self._truncate_text(full_text)

        # 构建Prompt
        system_prompt = """
你是一位专业的学术论文解读专家，擅长从计算机科学、人工智能领域的论文中提取关键信息。
请仔细阅读论文内容，按照要求提取结构化信息，确保准确、全面、客观。
如果某个字段的信息在论文中没有明确提到，请返回空数组。
输出必须严格遵循指定的JSON格式，不要添加任何额外的解释或说明。
"""

        format_instructions = self.parser.get_format_instructions()

        human_prompt = f"""
请解读以下论文内容，提取关键信息：

论文标题: {paper.title}
论文作者: {", ".join(paper.authors)}
发表日期: {paper.publication_date.strftime("%Y-%m-%d") if paper.publication_date else "未知"}
来源: {paper.source}

论文内容:
{text}

输出要求:
{format_instructions}
"""

        try:
            # 调用大模型
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            response_content = response.content

            # 解析输出
            result = self.parser.parse(response_content)

            # 保存到数据库
            interpretation = PaperInterpretation(
                paper_id=paper_id,
                core_contributions=result.core_contributions,
                experimental_methods=result.experimental_methods,
                datasets=result.datasets,
                conclusions=result.conclusions,
                innovations=result.innovations,
                limitations=result.limitations,
                references=result.key_references,
                interpretation_model=settings.MODEL_NAME,
                confidence_score=result.confidence_score,
                raw_response=response_content,
            )

            db.add(interpretation)

            # 更新论文状态
            paper.status = "interpreted"
            db.commit()

            logger.info(f"论文解读完成: {paper_id}")

            return {
                "paper_id": paper_id,
                "core_contributions": result.core_contributions,
                "experimental_methods": result.experimental_methods,
                "datasets": result.datasets,
                "conclusions": result.conclusions,
                "innovations": result.innovations,
                "limitations": result.limitations,
                "references": result.key_references,
                "confidence_score": result.confidence_score,
                "interpretation_model": settings.MODEL_NAME,
            }

        except Exception as e:
            logger.error(f"论文解读失败: {str(e)}")
            db.rollback()
            return None
