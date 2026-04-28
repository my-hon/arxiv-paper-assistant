#!/usr/bin/env python3
"""
测试Attention is all you need论文解析全流程
"""

import asyncio
import json
import os
from pathlib import Path

from modules.crawler.arxiv_client import ArxivClient
from modules.interpretation.paper_interpreter import PaperInterpreter

# 配置
OUTPUT_DIR = Path("D:/workspace/arxiv/edict-gongbu-v1.0.0/outputs")
PAPER_TITLE = "Attention is all you need"
PAPER_ID = "1706.03762"  # 已知的论文ID


async def main():
    print("Starting test for Attention paper parsing...")

    # 1. 检索论文
    print("\nStep 1: Searching paper...")
    client = ArxivClient()

    # 直接根据ID搜索论文（准确）
    result = client.search_by_id(PAPER_ID)
    if not result:
        print(f"❌ 未找到论文 {PAPER_ID}")
        return

    target_paper = client.parse_result(result)
    paper_id = target_paper["arxiv_id"]
    print(f"\nFound target paper: {target_paper['title']} (ID: {paper_id})")
    print(
        f"Authors: {', '.join(target_paper['authors'][:3])}{'...' if len(target_paper['authors']) > 3 else ''}"
    )
    print(f"Published: {target_paper['publication_date'].strftime('%Y-%m-%d')}")

    # 2. 下载PDF
    print("\nStep 2: Downloading PDF...")
    pdf_path = client.download_pdf(result, str(OUTPUT_DIR), filename=f"{paper_id}.pdf")

    if not pdf_path or not os.path.exists(pdf_path):
        print("❌ PDF下载失败")
        return

    print(f"✅ PDF下载完成: {pdf_path}")

    # 3. 提取PDF文本
    print("\n📄 步骤3: 提取PDF文本...")
    interpreter = PaperInterpreter()
    pdf_text = interpreter.extract_text_from_pdf(pdf_path)

    if not pdf_text:
        print("❌ PDF文本提取失败")
        return

    # 保存原始文本
    text_output_path = OUTPUT_DIR / f"{paper_id}_raw_text.txt"
    with open(text_output_path, "w", encoding="utf-8") as f:
        f.write(pdf_text)

    print(f"✅ PDF文本提取完成，保存到: {text_output_path}")
    print(f"   文本长度: {len(pdf_text)} 字符")

    # 4. 大模型解析论文
    print("\n🧠 步骤4: 大模型解析论文...")
    # 这里直接调用解析逻辑，不通过数据库
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.output_parsers import PydanticOutputParser

    from modules.interpretation.paper_interpreter import (
        HUMAN_PROMPT_TEMPLATE,
        SYSTEM_PROMPT,
        PaperInterpretationResult,
    )

    parser = PydanticOutputParser(pydantic_object=PaperInterpretationResult)
    format_instructions = parser.get_format_instructions()

    # 截断文本
    truncated_text = interpreter._truncate_text(pdf_text)

    # 构建提示词
    human_prompt = HUMAN_PROMPT_TEMPLATE.format(
        title=target_paper["title"],
        authors=", ".join(target_paper["authors"]),
        publication_date=target_paper["published"],
        source="arXiv",
        content=truncated_text,
        format_instructions=format_instructions,
    )

    # 调用大模型
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_prompt),
    ]

    try:
        response = await interpreter.llm.ainvoke(messages)
        response_content = response.content

        # 保存原始响应
        raw_response_path = OUTPUT_DIR / f"{paper_id}_llm_raw_response.json"
        with open(raw_response_path, "w", encoding="utf-8") as f:
            f.write(response_content)

        print(f"✅ 大模型响应已保存: {raw_response_path}")

        # 解析结果
        result = parser.parse(response_content)

        # 保存结构化结果
        structured_result_path = OUTPUT_DIR / f"{paper_id}_structured_result.json"
        with open(structured_result_path, "w", encoding="utf-8") as f:
            json.dump(result.dict(), f, ensure_ascii=False, indent=2)

        print(f"✅ 结构化解析结果已保存: {structured_result_path}")

        # 5. 生成带图片的Markdown报告
        print("\n📝 步骤5: 生成Markdown报告...")

        # 先提取图片
        extracted_images = interpreter.extract_images_from_pdf(pdf_path, paper_id)
        print(f"✅ 提取到 {len(extracted_images)} 张图片")

        # 模拟paper对象
        class MockPaper:
            def __init__(self):
                self.paper_id = paper_id
                self.title = target_paper["title"]
                self.authors = target_paper["authors"]
                self.publication_date = target_paper["published_parsed"]
                self.source = "arXiv"
                self.updated_at = None

        mock_paper = MockPaper()

        # 生成报告
        markdown_content = interpreter.generate_markdown_report(
            mock_paper, result, extracted_images
        )

        # 保存Markdown报告
        markdown_path = OUTPUT_DIR / f"{paper_id}_interpretation_report.md"
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"✅ Markdown解析报告已保存: {markdown_path}")

        # 6. 输出结果摘要
        print("\n🎉 测试完成！结果摘要:")
        print("=" * 60)
        print(f"📄 论文标题: {target_paper['title']}")
        print(
            f"👥 作者: {', '.join(target_paper['authors'][:3])}{'...' if len(target_paper['authors']) > 3 else ''}"
        )
        print(f"📅 发表日期: {target_paper['published']}")
        print(f"🎯 核心贡献点: {len(result.core_contributions)} 个")
        print(f"🔬 实验方法: {len(result.experimental_methods)} 个")
        print(f"📊 数据集: {len(result.datasets)} 个")
        print(f"📈 主要结论: {len(result.conclusions)} 个")
        print(f"💡 创新点: {len(result.innovations)} 个")
        print(f"⚠️ 局限性: {len(result.limitations)} 个")
        print(f"📚 参考文献: {len(result.key_references)} 个")
        print(f"🖼️ 图表描述: {len(result.figure_descriptions)} 个")
        print(f"📊 置信度: {result.confidence_score:.2f}")
        print(f"🖼️ 提取图片: {len(extracted_images)} 张")
        print("=" * 60)
        print(f"所有结果已保存到: {OUTPUT_DIR}")

    except Exception as e:
        print(f"❌ 解析过程出错: {str(e)}")
        import traceback

        traceback.print_exc()
        return


if __name__ == "__main__":
    asyncio.run(main())
