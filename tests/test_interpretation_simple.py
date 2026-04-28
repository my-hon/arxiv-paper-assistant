#!/usr/bin/env python3
"""简单的论文解读测试，输出JSON结果到文件。"""
import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.modules.interpretation.paper_interpreter import PaperInterpreter
from src.db.database import get_db
from src.db.models import Paper


async def test_paper_interpretation(paper_id: str, output_file: str = None):
    """测试论文解读"""
    logger.info(f"开始解读论文: {paper_id}")

    # 获取论文信息
    db = next(get_db())
    paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()

    if not paper:
        logger.error(f"论文不存在: {paper_id}")
        return None

    logger.info(f"论文标题: {paper.title}")
    logger.info(f"论文摘要长度: {len(paper.abstract)} 字符")

    # 执行解读
    interpreter = PaperInterpreter()
    result = await interpreter.interpret_paper(paper_id, use_abstract_only=True)

    if not result:
        logger.error("解读失败")
        return None

    logger.info(f"解读完成，置信度: {result.get('confidence_score', 0)}")

    # 准备输出
    output = {
        "paper_info": {
            "paper_id": paper.paper_id,
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "categories": paper.categories,
            "publication_date": paper.publication_date.isoformat() if paper.publication_date else None
        },
        "interpretation_result": {k: v for k, v in result.items() if k != "interpretation_time"}
    }

    # 保存到文件
    if not output_file:
        output_file = f"interpretation_result_{paper.arxiv_id}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"结果已保存到: {os.path.abspath(output_file)}")

    # 打印关键信息
    print("\n" + "="*80)
    print("解读结果摘要:")
    print("="*80)
    print(f"置信度: {result.get('confidence_score', 0):.2f}")
    print(f"核心贡献数量: {len(result.get('core_contributions', []))}")
    print(f"实验方法数量: {len(result.get('experimental_methods', []))}")
    print(f"数据集数量: {len(result.get('datasets', []))}")
    print(f"结论数量: {len(result.get('conclusions', []))}")
    print(f"创新点数量: {len(result.get('innovations', []))}")
    print(f"局限性数量: {len(result.get('limitations', []))}")

    print("\n核心贡献:")
    for i, contrib in enumerate(result.get("core_contributions", [])[:3], 1):
        print(f"  {i}. {contrib[:100]}...")

    print("\n结论:")
    for i, conclusion in enumerate(result.get("conclusions", [])[:3], 1):
        print(f"  {i}. {conclusion[:100]}...")

    print("\n" + "="*80)
    print(f"完整结果请查看文件: {output_file}")
    print("="*80)

    return output


async def main():
    if len(sys.argv) > 1:
        paper_id = sys.argv[1]
    else:
        # 默认测试最新的论文
        db = next(get_db())
        latest_paper = db.query(Paper).order_by(Paper.id.desc()).first()
        if not latest_paper:
            logger.error("数据库中没有论文，请先爬取论文")
            return
        paper_id = latest_paper.paper_id
        logger.info(f"使用最新论文: {paper_id}")

    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    await test_paper_interpretation(paper_id, output_file)


if __name__ == "__main__":
    asyncio.run(main())
