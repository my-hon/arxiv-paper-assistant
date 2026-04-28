"""
论文解读模块
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from loguru import logger
from PIL import Image
from pydantic import BaseModel, Field

from config.settings import settings
from db.database import get_db
from db.models import Paper, PaperInterpretation

# 提示词常量
SYSTEM_PROMPT = """
你是一位专业的学术论文解读专家，擅长从计算机科学、人工智能领域的论文中提取关键信息，特别关注论文的可复现性和工程实现细节。
请仔细阅读论文内容，按照要求提取结构化信息，确保准确、全面、客观。

核心提取要求：
1. **问题领域与数据集**：
   - 明确论文解决的具体领域问题和研究方向
   - 详细列出所有使用的数据集，包括名称、来源、规模、特点
   - 注意数据集的下载链接、预处理方法和使用方式

2. **方法实现与代码链接**：
   - 详细描述论文的技术方法和整体架构
   - 拆解每个核心算法的实现步骤和关键逻辑
   - 重点识别论文中提到的所有代码链接（GitHub、GitLab、项目主页、Zenodo等）
   - 说明每个算法的伪代码、核心公式和实现要点
   - 提取代码实现的关键注意事项、优化技巧和潜在坑点

3. **实验结果与评价指标**：
   - 列出所有使用的评价指标，包括明确定义和计算方法
   - 说明每个指标是否有现成的实现库（如sklearn、torchmetrics等），如果有则给出具体的调用方法
   - 提取论文中每个指标的具体实验结果数值
   - 记录实验的硬件环境、软件版本、训练参数等复现必要信息
   - 整理与基线方法的对比结果和优势分析

注意事项：
- 如果某个字段的信息在论文中没有明确提到，请返回空数组或空字符串
- 特别注意论文中的图表、图片说明、附录和补充材料中的信息
- 对于代码链接，即使是脚注或引用中提到的也要完整提取
- 对于评价指标，如果论文中没有明确说明实现方法，请根据常识给出标准实现建议
- 输出必须严格遵循指定的JSON格式，不要添加任何额外的解释或说明
- 确保所有信息准确无误，不要编造或推断论文中没有的内容
"""

HUMAN_PROMPT_TEMPLATE = """
请解读以下论文内容，按照要求提取结构化信息：

论文标题: {title}
论文作者: {authors}
发表日期: {publication_date}
来源: {source}

论文内容:
{content}

输出要求：
1. 严格按照给定的JSON格式输出，不要添加任何额外的解释
2. 重点关注方法的实现细节、代码链接、数据集信息和实验结果
3. 对于评价指标，特别说明如何实现，是否有现成的库可以调用
4. 如果信息不明确，请留空，不要编造内容

输出格式说明:
{format_instructions}
"""

# Markdown报告模板
MARKDOWN_REPORT_TEMPLATE = """# {title}

## 基本信息
- **论文ID**: {paper_id}
- **作者**: {authors}
- **发表日期**: {publication_date}
- **来源**: {source}
- **解读模型**: {model_name}
- **置信度**: {confidence_score:.2f}

---

## 🎯 问题领域
{problem_domain}

---

## 🌟 核心贡献
"""

# Markdown章节模板
SECTION_TEMPLATE = """
---

## {icon} {title}
"""

# 图表章节模板
FIGURE_SECTION_TEMPLATE = """
---

## 🖼️ 图表说明
"""

# 单个图表模板
FIGURE_TEMPLATE = """
### 图 {figure_num} (第 {page_num} 页)
![{desc}]({img_path})

{desc}
"""

# 无图图表模板
FIGURE_NO_IMAGE_TEMPLATE = """
### 图 {figure_num} (第 {page_num} 页)
{desc}
"""

# 其他图片章节模板
OTHER_IMAGES_TEMPLATE = """
### 其他图片
"""

# 单个其他图片模板
OTHER_IMAGE_TEMPLATE = """
#### 第 {page_num} 页 - 图片 {index}
![第 {page_num} 页图片 {index}]({img_path})
"""

# 参考文献章节模板
REFERENCES_SECTION_TEMPLATE = """
---

## 📚 关键参考文献
"""

# 报告页脚模板
REPORT_FOOTER_TEMPLATE = """
---

*本报告由AI自动生成，生成时间: {generated_at}*
"""

# 摘要模式文本提示
ABSTRACT_MODE_TEXT = "标题: {title}\n\n作者: {authors}\n\n摘要: {abstract}"


# 定义输出结构
class DatasetInfo(BaseModel):
    name: str = Field(description="数据集名称")
    source: str = Field(description="数据集来源/链接")
    scale: str = Field(description="数据集规模：样本数量、类别数量等")
    characteristics: str = Field(description="数据集特点、适用场景")

class EvaluationMetric(BaseModel):
    name: str = Field(description="评价指标名称")
    definition: str = Field(description="指标的定义和计算方法")
    existing_library: str = Field(description="是否有现成的实现库，如sklearn、torchmetrics等，有则给出库名和调用方法，没有则说明如何实现")
    paper_value: str = Field(description="论文中该指标达到的具体数值")

class ExperimentalResult(BaseModel):
    metric_name: str = Field(description="指标名称")
    value: str = Field(description="实验得到的数值")
    comparison: str = Field(description="与其他方法或基线的对比结果")
    significance: str = Field(description="结果的显著性分析和说明")

class CodeLink(BaseModel):
    url: str = Field(description="代码链接地址")
    description: str = Field(description="代码链接的描述，如官方实现、第三方复现、项目主页等")
    platform: str = Field(description="代码托管平台，如GitHub、GitLab、Zenodo等")

class MethodDetail(BaseModel):
    name: str = Field(description="方法/算法名称")
    description: str = Field(description="方法的详细描述")
    implementation_steps: list[str] = Field(description="代码实现的关键步骤")
    formula: str = Field(description="核心公式（如果有），用LaTeX格式表示")

class PaperInterpretationResult(BaseModel):
    # 问题领域
    problem_domain: str = Field(description="论文解决的具体领域问题，明确说明属于哪个研究方向，解决了什么具体痛点")

    # 核心贡献
    core_contributions: list[str] = Field(description="论文的核心贡献点，分点列出")
    innovations: list[str] = Field(description="论文的创新点，分点列出，说明与现有工作的区别")
    limitations: list[str] = Field(description="论文的局限性，分点列出")
    conclusions: list[str] = Field(description="论文的主要结论，分点列出")

    # 方法实现
    technical_approach: str = Field(description="整体技术方法和架构思路，宏观描述论文的解决方案")
    method_details: list[MethodDetail] = Field(description="具体的方法细节，包含每个算法、模型的详细描述和实现要点")
    implementation_notes: list[str] = Field(description="代码实现的关键注意事项、难点、优化技巧等")
    code_links: list[CodeLink] = Field(description="论文中提到的所有代码链接，包括官方实现、数据集、Demo等相关链接")

    # 数据集
    datasets: list[DatasetInfo] = Field(description="论文使用的所有数据集的详细信息")

    # 实验结果
    experimental_setup: list[str] = Field(description="实验设置：硬件环境、软件版本、训练参数、评估流程等")
    evaluation_metrics: list[EvaluationMetric] = Field(description="使用的所有评价指标，包含定义、实现方法和论文中的结果")
    experimental_results: list[ExperimentalResult] = Field(description="详细的实验结果，每个指标的具体数值和对比分析")
    baseline_comparison: list[str] = Field(description="与基线方法或现有SOTA的对比结果，说明论文方法的优势")

    # 辅助信息
    key_references: list[str] = Field(description="论文中提到的关键参考文献，分点列出")
    confidence_score: float = Field(description="解读结果的置信度，0-1之间")
    figure_descriptions: list[Dict] = Field(
        description="论文中图表的描述，包含图表位置和内容说明"
    )


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

    def extract_images_from_pdf(self, pdf_path: str, paper_id: str) -> List[Dict]:
        """
        从PDF中提取所有图片并保存到本地
        :param pdf_path: PDF文件路径
        :param paper_id: 论文ID，用于创建保存目录
        :return: 提取的图片信息列表，包含路径、页码、位置等
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF文件不存在: {pdf_path}")
            return []

        # 创建图片保存目录
        images_dir = os.path.join(settings.STORAGE_PATH, "papers", paper_id, "images")
        os.makedirs(images_dir, exist_ok=True)

        extracted_images = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 提取页面中的所有图片
                    for img_index, img in enumerate(page.images, 1):
                        try:
                            # 获取图片数据
                            img_data = img["stream"].get_data()

                            # 生成图片文件名
                            img_ext = img["type"] if "type" in img else "png"
                            img_filename = f"page_{page_num}_img_{img_index}.{img_ext}"
                            img_path = os.path.join(images_dir, img_filename)

                            # 保存图片
                            with open(img_path, "wb") as f:
                                f.write(img_data)

                            # 验证图片是否有效
                            try:
                                with Image.open(img_path) as img_obj:
                                    img_size = img_obj.size
                                    img_mode = img_obj.mode
                            except Exception as e:
                                logger.warning(f"图片 {img_path} 损坏，跳过: {str(e)}")
                                os.remove(img_path)
                                continue

                            # 记录图片信息
                            img_info = {
                                "path": img_path,
                                "filename": img_filename,
                                "page_num": page_num,
                                "index": img_index,
                                "width": img_size[0],
                                "height": img_size[1],
                                "mode": img_mode,
                                "bbox": (
                                    img["x0"],
                                    img["top"],
                                    img["x1"],
                                    img["bottom"],
                                ),
                            }
                            extracted_images.append(img_info)
                            logger.debug(f"成功提取图片: {img_path}")

                        except Exception as e:
                            logger.warning(
                                f"提取第 {page_num} 页第 {img_index} 张图片失败: {str(e)}"
                            )
                            continue

            logger.info(
                f"成功从PDF中提取 {len(extracted_images)} 张图片，保存到: {images_dir}"
            )
            return extracted_images

        except Exception as e:
            logger.error(f"提取PDF图片失败: {str(e)}")
            return []

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
                # 核心信息
                "problem_domain": existing_interpretation.problem_domain,
                "core_contributions": existing_interpretation.core_contributions,
                "innovations": existing_interpretation.innovations,
                "limitations": existing_interpretation.limitations,
                "conclusions": existing_interpretation.conclusions,

                # 方法实现
                "technical_approach": existing_interpretation.technical_approach,
                "method_details": existing_interpretation.method_details,
                "implementation_notes": existing_interpretation.implementation_notes,
                "code_links": existing_interpretation.code_links,

                # 数据集
                "datasets": existing_interpretation.datasets,

                # 实验结果
                "experimental_setup": existing_interpretation.experimental_setup,
                "evaluation_metrics": existing_interpretation.evaluation_metrics,
                "experimental_results": existing_interpretation.experimental_results,
                "baseline_comparison": existing_interpretation.baseline_comparison,

                # 辅助信息
                "references": existing_interpretation.references,
                "figure_descriptions": existing_interpretation.figure_descriptions,
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
            text = ABSTRACT_MODE_TEXT.format(
                title=paper.title,
                authors=", ".join(paper.authors),
                abstract=paper.abstract,
            )
        else:
            logger.info(f"使用全文解读论文: {paper_id}")
            full_text = self.extract_text_from_pdf(paper.pdf_path)
            if not full_text:
                logger.warning("全文提取失败，回退到使用摘要")
                text = ABSTRACT_MODE_TEXT.format(
                    title=paper.title,
                    authors=", ".join(paper.authors),
                    abstract=paper.abstract,
                )
            else:
                text = self._truncate_text(full_text)

        # 构建Prompt
        format_instructions = self.parser.get_format_instructions()

        human_prompt = HUMAN_PROMPT_TEMPLATE.format(
            title=paper.title,
            authors=", ".join(paper.authors),
            publication_date=paper.publication_date.strftime("%Y-%m-%d")
            if paper.publication_date
            else "未知",
            source=paper.source,
            content=text,
            format_instructions=format_instructions,
        )

        try:
            # 调用大模型
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=human_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            response_content = response.content

            # 解析输出
            result = self.parser.parse(response_content)

            # 保存到数据库
            interpretation = PaperInterpretation(
                paper_id=paper_id,
                # 核心信息
                problem_domain=result.problem_domain,
                core_contributions=result.core_contributions,
                innovations=result.innovations,
                limitations=result.limitations,
                conclusions=result.conclusions,

                # 方法实现
                technical_approach=result.technical_approach,
                method_details=[md.dict() for md in result.method_details],
                implementation_notes=result.implementation_notes,
                code_links=[cl.dict() for cl in result.code_links],

                # 数据集
                datasets=[ds.dict() for ds in result.datasets],

                # 实验结果
                experimental_setup=result.experimental_setup,
                evaluation_metrics=[em.dict() for em in result.evaluation_metrics],
                experimental_results=[er.dict() for er in result.experimental_results],
                baseline_comparison=result.baseline_comparison,

                # 辅助信息
                references=result.key_references,
                figure_descriptions=result.figure_descriptions,
                interpretation_model=settings.MODEL_NAME,
                confidence_score=result.confidence_score,
                raw_response=response_content,
            )

            db.add(interpretation)

            # 更新论文状态
            paper.status = "interpreted"
            db.commit()

            logger.info(f"论文解读完成: {paper_id}")

            # 提取PDF图片（如果是全文解读）
            extracted_images = []
            if (
                not use_abstract_only
                and paper.pdf_path
                and os.path.exists(paper.pdf_path)
            ):
                extracted_images = self.extract_images_from_pdf(
                    paper.pdf_path, paper_id
                )

            # 生成Markdown文档
            markdown_content = self.generate_markdown_report(
                paper, result, extracted_images
            )

            # 保存Markdown文件
            markdown_dir = os.path.join(settings.STORAGE_PATH, "papers", paper_id)
            os.makedirs(markdown_dir, exist_ok=True)
            markdown_path = os.path.join(markdown_dir, "interpretation.md")
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            logger.info(f"解读报告已保存到: {markdown_path}")

            return {
                "paper_id": paper_id,
                # 核心信息
                "problem_domain": result.problem_domain,
                "core_contributions": result.core_contributions,
                "innovations": result.innovations,
                "limitations": result.limitations,
                "conclusions": result.conclusions,

                # 方法实现
                "technical_approach": result.technical_approach,
                "method_details": [md.dict() for md in result.method_details],
                "implementation_notes": result.implementation_notes,
                "code_links": [cl.dict() for cl in result.code_links],

                # 数据集
                "datasets": [ds.dict() for ds in result.datasets],

                # 实验结果
                "experimental_setup": result.experimental_setup,
                "evaluation_metrics": [em.dict() for em in result.evaluation_metrics],
                "experimental_results": [er.dict() for er in result.experimental_results],
                "baseline_comparison": result.baseline_comparison,

                # 辅助信息
                "references": result.key_references,
                "figure_descriptions": result.figure_descriptions,
                "confidence_score": result.confidence_score,
                "interpretation_model": settings.MODEL_NAME,
                "markdown_path": markdown_path,
                "extracted_images": len(extracted_images),
            }

        except Exception as e:
            logger.error(f"论文解读失败: {str(e)}")
            db.rollback()
            return None

    def generate_markdown_report(
        self, paper: Paper, result: PaperInterpretationResult, images: List[Dict]
    ) -> str:
        """
        生成带图片引用的Markdown解读报告
        :param paper: 论文信息
        :param result: 解读结果
        :param images: 提取的图片列表
        :return: Markdown内容
        """
        # 构建图片映射：按页码分组
        images_by_page = {}
        for img in images:
            page_num = img["page_num"]
            if page_num not in images_by_page:
                images_by_page[page_num] = []
            images_by_page[page_num].append(img)

        # 构建Markdown内容
        markdown = MARKDOWN_REPORT_TEMPLATE.format(
            title=paper.title,
            paper_id=paper.paper_id,
            authors=", ".join(paper.authors),
            publication_date=paper.publication_date.strftime("%Y-%m-%d")
            if paper.publication_date
            else "未知",
            source=paper.source,
            model_name=settings.MODEL_NAME,
            confidence_score=result.confidence_score,
            problem_domain=result.problem_domain,
        )

        # 核心贡献
        for contrib in result.core_contributions:
            markdown += f"- {contrib}\n"

        # 创新点
        markdown += SECTION_TEMPLATE.format(icon="💡", title="创新点")
        for innovation in result.innovations:
            markdown += f"- {innovation}\n"

        # 技术方法
        markdown += SECTION_TEMPLATE.format(icon="🔬", title="技术方法")
        markdown += f"{result.technical_approach}\n\n"

        # 方法实现细节
        markdown += SECTION_TEMPLATE.format(icon="⚙️", title="实现细节")
        for method in result.method_details:
            markdown += f"### {method.name}\n"
            markdown += f"{method.description}\n\n"
            if method.formula:
                markdown += f"**核心公式**:\n```latex\n{method.formula}\n```\n\n"
            markdown += "**实现步骤**:\n"
            for step in method.implementation_steps:
                markdown += f"- {step}\n"
            markdown += "\n"

        # 实现要点
        if result.implementation_notes:
            markdown += SECTION_TEMPLATE.format(icon="💡", title="实现要点")
            for note in result.implementation_notes:
                markdown += f"- {note}\n"

        # 代码链接
        if result.code_links:
            markdown += SECTION_TEMPLATE.format(icon="🔗", title="代码链接")
            for code_link in result.code_links:
                markdown += f"- [{code_link.description}]({code_link.url}) ({code_link.platform})\n"

        # 数据集
        markdown += SECTION_TEMPLATE.format(icon="📊", title="数据集")
        for dataset in result.datasets:
            markdown += f"### {dataset.name}\n"
            markdown += f"- **来源**: {dataset.source}\n"
            markdown += f"- **规模**: {dataset.scale}\n"
            markdown += f"- **特点**: {dataset.characteristics}\n\n"

        # 实验设置
        if result.experimental_setup:
            markdown += SECTION_TEMPLATE.format(icon="🧪", title="实验设置")
            for setup in result.experimental_setup:
                markdown += f"- {setup}\n"

        # 评价指标
        if result.evaluation_metrics:
            markdown += SECTION_TEMPLATE.format(icon="📏", title="评价指标")
            for metric in result.evaluation_metrics:
                markdown += f"### {metric.name}\n"
                markdown += f"- **定义**: {metric.definition}\n"
                markdown += f"- **实现方法**: {metric.existing_library}\n"
                markdown += f"- **论文结果**: {metric.paper_value}\n\n"

        # 实验结果
        if result.experimental_results:
            markdown += SECTION_TEMPLATE.format(icon="📈", title="实验结果")
            for result_item in result.experimental_results:
                markdown += f"- **{result_item.metric_name}**: {result_item.value}\n"
                markdown += f"  - 对比: {result_item.comparison}\n"
                markdown += f"  - 显著性: {result_item.significance}\n"
            markdown += "\n"

        # 基线对比
        if result.baseline_comparison:
            markdown += SECTION_TEMPLATE.format(icon="📊", title="基线对比")
            for comparison in result.baseline_comparison:
                markdown += f"- {comparison}\n"

        # 主要结论
        markdown += SECTION_TEMPLATE.format(icon="🎓", title="主要结论")
        for conclusion in result.conclusions:
            markdown += f"- {conclusion}\n"

        # 局限性
        markdown += SECTION_TEMPLATE.format(icon="⚠️", title="局限性")
        for limitation in result.limitations:
            markdown += f"- {limitation}\n"

        # 添加图表部分
        if images or result.figure_descriptions:
            markdown += FIGURE_SECTION_TEMPLATE
            # 先添加描述中提到的图表
            for fig_desc in result.figure_descriptions:
                page_num = fig_desc.get("page_num", "未知")
                desc = fig_desc.get("description", "")
                figure_num = fig_desc.get("figure_num", "")
                # 查找对应页码的图片
                if page_num in images_by_page and images_by_page[page_num]:
                    img = images_by_page[page_num][0]  # 取该页第一张图片
                    img_rel_path = f"./images/{img['filename']}"
                    markdown += FIGURE_TEMPLATE.format(
                        figure_num=figure_num,
                        page_num=page_num,
                        desc=desc,
                        img_path=img_rel_path,
                    )
                    # 移除已使用的图片
                    images_by_page[page_num].pop(0)
                    if not images_by_page[page_num]:
                        del images_by_page[page_num]
                else:
                    markdown += FIGURE_NO_IMAGE_TEMPLATE.format(
                        figure_num=figure_num, page_num=page_num, desc=desc
                    )

            # 添加剩余未匹配的图片
            if images_by_page:
                markdown += OTHER_IMAGES_TEMPLATE
                for page_num in sorted(images_by_page.keys()):
                    for img in images_by_page[page_num]:
                        img_rel_path = f"./images/{img['filename']}"
                        markdown += OTHER_IMAGE_TEMPLATE.format(
                            page_num=page_num, index=img["index"], img_path=img_rel_path
                        )

        # 添加参考文献
        if result.key_references:
            markdown += REFERENCES_SECTION_TEMPLATE
            for ref in result.key_references:
                markdown += f"- {ref}\n"

        # 添加页脚
        generated_at = (
            paper.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            if paper.updated_at
            else "未知"
        )
        markdown += REPORT_FOOTER_TEMPLATE.format(generated_at=generated_at)

        return markdown
