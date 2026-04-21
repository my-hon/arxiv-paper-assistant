"""
复现代码生成模块
"""

from pathlib import Path
from typing import Any, Dict, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel, Field

from .arxiv_crawler import PaperInfo
from .config import settings


# 复现结果数据模型
class ReproductionCode(BaseModel):
    """生成的复现代码结构"""

    main_code: str = Field(description="主Python代码")
    requirements: list[str] = Field(description="依赖包列表")
    dockerfile: str = Field(description="Dockerfile内容")
    readme: str = Field(description="使用说明文档")
    expected_output: str = Field(description="预期输出说明")


class ReproductionGenerator:
    """复现代码生成器"""

    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.MODEL_NAME,
            temperature=0,
        )
        self.parser = JsonOutputParser(pydantic_object=ReproductionCode)

        # 构建提示模板
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是专业的机器学习实验复现专家。请根据论文信息生成可直接运行的复现代码。

生成要求：
1. 代码必须完整、可运行，包含所有必要的导入和配置
2. 依赖包版本要合理，尽可能使用稳定版本
3. Dockerfile使用Python 3.10-slim基础镜像
4. README包含详细的运行说明和预期结果解释
5. 如果有数据集，提供下载链接或模拟数据生成代码
6. 代码要添加必要的注释，易于理解

输出格式要求：
{format_instructions}
""",
                ),
                (
                    "human",
                    """论文标题：{title}
论文摘要：{summary}
论文方法描述：
{content}

请生成可直接运行的复现代码，包含主程序、依赖配置、Dockerfile和使用说明。
""",
                ),
            ]
        )

        self.chain = self.prompt | self.llm | self.parser

    async def generate_code(
        self, paper: PaperInfo, content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成复现代码

        Args:
            paper: 论文信息
            content: 论文方法部分内容（可选）

        Returns:
            生成的代码结构
        """
        logger.info(f"开始生成复现代码：{paper.title}")

        try:
            result = self.chain.invoke(
                {
                    "title": paper.title,
                    "summary": paper.summary,
                    "content": content if content else paper.summary,
                    "format_instructions": self.parser.get_format_instructions(),
                }
            )

            logger.info("复现代码生成完成")
            return result
        except Exception as e:
            logger.error(f"代码生成失败：{e}")
            raise

    def save_to_files(self, paper_id: str, code_data: Dict[str, Any]) -> Path:
        """
        将生成的代码保存到文件

        Args:
            paper_id: 论文ID
            code_data: 生成的代码数据

        Returns:
            保存目录路径
        """
        save_dir = settings.STORAGE_PATH / "scripts" / paper_id
        save_dir.mkdir(parents=True, exist_ok=True)

        # 保存主代码
        main_file = save_dir / "main.py"
        main_file.write_text(code_data["main_code"], encoding="utf-8")

        # 保存依赖
        requirements_file = save_dir / "requirements.txt"
        requirements_content = "\n".join(code_data["requirements"])
        requirements_file.write_text(requirements_content, encoding="utf-8")

        # 保存Dockerfile
        dockerfile = save_dir / "Dockerfile"
        dockerfile.write_text(code_data["dockerfile"], encoding="utf-8")

        # 保存README
        readme_file = save_dir / "README.md"
        readme_file.write_text(code_data["readme"], encoding="utf-8")

        # 保存预期输出
        expected_file = save_dir / "EXPECTED_OUTPUT.md"
        expected_file.write_text(code_data["expected_output"], encoding="utf-8")

        logger.info(f"代码已保存到：{save_dir}")
        return save_dir


def format_reproduction_result(paper: PaperInfo, save_dir: Path) -> str:
    """格式化复现结果为输出字符串"""
    output = [
        "🔬 复现脚本生成成功！",
        f"📄 论文：{paper.title} (arXiv:{paper.paper_id})",
        "=" * 60,
        f"\n📁 生成的文件位于：{save_dir}",
        "   ├── main.py          # 主执行脚本",
        "   ├── requirements.txt # Python依赖包",
        "   ├── Dockerfile       # Docker镜像配置",
        "   ├── README.md        # 详细使用说明",
        "   └── EXPECTED_OUTPUT.md # 预期输出说明",
        "\n🚀 运行方式：",
        "\n方法1：使用Docker（推荐）",
        f"   cd {save_dir}",
        "   docker build -t reproduce-{paper_id} .",
        "   docker run reproduce-{paper_id}",
        "\n方法2：本地运行",
        f"   cd {save_dir}",
        "   pip install -r requirements.txt",
        "   python main.py",
        "\n⚠️  注意事项：",
        "   - 复现结果可能因随机种子和环境差异略有不同",
        "   - 大型数据集可能需要手动下载",
        "   - 如遇问题请参考README.md中的说明",
        "=" * 60,
    ]

    return "\n".join(output).format(paper_id=paper.paper_id)


# 测试代码
if __name__ == "__main__":
    import asyncio

    from .arxiv_crawler import ArXivCrawler

    crawler = ArXivCrawler()
    paper = crawler.get_paper_by_id("2310.06825")
    if paper:
        generator = ReproductionGenerator()
        result = asyncio.run(generator.generate_code(paper))
        save_dir = generator.save_to_files(paper.paper_id, result)
        print(format_reproduction_result(paper, save_dir))
