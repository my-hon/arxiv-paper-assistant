#!/usr/bin/env python3
"""
简化版测试脚本，避免编码问题
"""
import os
import json
import asyncio
from pathlib import Path
from modules.crawler.arxiv_client import ArxivClient
from modules.interpretation.paper_interpreter import PaperInterpreter

# 配置
OUTPUT_DIR = Path("D:/workspace/arxiv/edict-gongbu-v1.0.0/outputs")
PAPER_ID = "1706.03762"  # Attention is all you need

async def main():
    print("Starting test...")

    # 1. 获取论文信息
    print("\n1. Getting paper info...")
    client = ArxivClient()
    result = client.search_by_id(PAPER_ID)
    if not result:
        print(f"Paper {PAPER_ID} not found")
        return

    target_paper = client.parse_result(result)
    paper_id = target_paper["arxiv_id"]
    print(f"Found paper: {target_paper['title']}")

    # 2. 下载PDF
    print("\n2. Downloading PDF...")
    pdf_path = client.download_pdf(result, str(OUTPUT_DIR), filename=f"{paper_id}.pdf")
    if not pdf_path or not os.path.exists(pdf_path):
        print("PDF download failed")
        return
    print(f"PDF downloaded: {pdf_path}")

    # 3. 提取文本
    print("\n3. Extracting text from PDF...")
    interpreter = PaperInterpreter()
    pdf_text = interpreter.extract_text_from_pdf(pdf_path)
    if not pdf_text:
        print("Text extraction failed")
        return

    # 保存文本
    text_output_path = OUTPUT_DIR / f"{paper_id}_raw_text.txt"
    with open(text_output_path, "w", encoding="utf-8") as f:
        f.write(pdf_text)
    print(f"Raw text saved: {text_output_path}")
    print(f"Text length: {len(pdf_text)} characters")

    # 4. 提取图片
    print("\n4. Extracting images...")
    extracted_images = interpreter.extract_images_from_pdf(pdf_path, paper_id)
    print(f"Extracted {len(extracted_images)} images")

    # 5. 解析论文
    print("\n5. Parsing paper with LLM...")
    from langchain_core.output_parsers import PydanticOutputParser
    from langchain_core.messages import HumanMessage, SystemMessage
    from modules.interpretation.paper_interpreter import PaperInterpretationResult, SYSTEM_PROMPT, HUMAN_PROMPT_TEMPLATE

    parser = PydanticOutputParser(pydantic_object=PaperInterpretationResult)
    format_instructions = parser.get_format_instructions()

    truncated_text = interpreter._truncate_text(pdf_text)

    human_prompt = HUMAN_PROMPT_TEMPLATE.format(
        title=target_paper["title"],
        authors=", ".join(target_paper["authors"]),
        publication_date=target_paper["publication_date"].strftime("%Y-%m-%d"),
        source="arXiv",
        content=truncated_text,
        format_instructions=format_instructions
    )

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
        print(f"Raw LLM response saved: {raw_response_path}")

        # 解析结果
        result = parser.parse(response_content)

        # 保存结构化结果
        structured_result_path = OUTPUT_DIR / f"{paper_id}_structured_result.json"
        with open(structured_result_path, "w", encoding="utf-8") as f:
            json.dump(result.dict(), f, ensure_ascii=False, indent=2)
        print(f"Structured result saved: {structured_result_path}")

        # 6. 生成Markdown报告
        print("\n6. Generating Markdown report...")
        # 模拟paper对象
        class MockPaper:
            def __init__(self):
                self.paper_id = paper_id
                self.title = target_paper["title"]
                self.authors = target_paper["authors"]
                self.publication_date = target_paper["publication_date"]
                self.source = "arXiv"
                self.updated_at = None

        mock_paper = MockPaper()
        markdown_content = interpreter.generate_markdown_report(mock_paper, result, extracted_images)

        markdown_path = OUTPUT_DIR / f"{paper_id}_interpretation_report.md"
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"Markdown report saved: {markdown_path}")

        # 输出摘要
        print("\n" + "="*60)
        print("Parsing completed! Results summary:")
        print(f"Core contributions: {len(result.core_contributions)}")
        print(f"Experimental methods: {len(result.experimental_methods)}")
        print(f"Datasets: {len(result.datasets)}")
        print(f"Conclusions: {len(result.conclusions)}")
        print(f"Innovations: {len(result.innovations)}")
        print(f"Limitations: {len(result.limitations)}")
        print(f"References: {len(result.key_references)}")
        print(f"Figure descriptions: {len(result.figure_descriptions)}")
        print(f"Confidence score: {result.confidence_score:.2f}")
        print(f"Images extracted: {len(extracted_images)}")
        print(f"All results saved to: {OUTPUT_DIR}")
        print("="*60)

    except Exception as e:
        print(f"Error during parsing: {str(e)}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    asyncio.run(main())
