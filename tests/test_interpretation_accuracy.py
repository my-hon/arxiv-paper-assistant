#!/usr/bin/env python3
"""论文解读准确度测试工具。

功能：
1. 支持单篇/多篇论文解读测试
2. 输出详细的结构化解析结果
3. 对比原文信息和解析结果
4. 生成测试报告
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from modules.crawler.arxiv_client import ArxivClient
from modules.interpretation.paper_interpreter import PaperInterpreter
from db.database import get_db
from db.models import Paper, PaperInterpretation


class InterpretationTester:
    """论文解读准确度测试器"""

    def __init__(self, output_dir: str = "./test_reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.crawler = ArxivClient()
        self.interpreter = PaperInterpreter()
        self.db = next(get_db())

    async def test_by_arxiv_id(
        self,
        arxiv_id: str,
        use_abstract_only: bool = True,
        force_reparse: bool = False,
        save_report: bool = True
    ) -> Dict:
        """测试指定arXiv ID的论文解读"""
        logger.info(f"{'='*60}")
        logger.info(f"测试论文解读: {arxiv_id}")
        logger.info(f"{'='*60}")

        # 1. 获取论文信息
        paper = self._get_or_download_paper(arxiv_id)
        if not paper:
            logger.error(f"无法获取论文信息: {arxiv_id}")
            return {"success": False, "error": "无法获取论文信息"}

        # 2. 检查是否已解析
        if not force_reparse:
            existing_interp = self._get_existing_interpretation(paper.paper_id)
            if existing_interp:
                logger.info(f"使用已有解析结果 (ID: {existing_interp.id})")
                result = self._convert_interpretation_to_dict(existing_interp)
                self._print_interpretation_result(result, paper)
                if save_report:
                    self._save_test_report(paper, result)
                return {"success": True, "paper": paper, "interpretation": result}

        # 3. 执行解析
        logger.info(f"开始解析论文: {paper.title}")
        logger.info(f"解析模式: {'仅摘要' if use_abstract_only else '全文'}")

        try:
            result = await self.interpreter.interpret_paper(paper.paper_id, use_abstract_only)
            if not result:
                logger.error("论文解析失败")
                return {"success": False, "error": "解析失败"}

            logger.info(f"解析完成，置信度: {result.get('confidence_score', 0)}")

            # 4. 输出结果
            self._print_interpretation_result(result, paper)

            # 5. 保存报告
            if save_report:
                self._save_test_report(paper, result)

            return {
                "success": True,
                "paper": {
                    "paper_id": paper.paper_id,
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "categories": paper.categories,
                    "publication_date": paper.publication_date.isoformat() if paper.publication_date else None
                },
                "interpretation": result
            }

        except Exception as e:
            logger.error(f"解析过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _get_or_download_paper(self, arxiv_id: str) -> Optional[Paper]:
        """获取论文信息，不存在则搜索"""
        # 先查数据库
        paper = self.db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
        if paper:
            logger.info(f"从数据库获取论文: {paper.title}")
            return paper

        # 搜索论文
        logger.info(f"搜索arXiv论文: {arxiv_id}")
        results = list(self.crawler.search_papers(
            query="",
            id_list=[arxiv_id],
            max_results=1
        ))

        if not results:
            return None

        paper_data = self.crawler.parse_result(results[0])
        papers = [paper_data]
        self.crawler.save_papers_to_db(papers)

        if not papers:
            return None

        # 重新查询数据库获取完整的Paper对象
        return self.db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()

    def _get_existing_interpretation(self, paper_id: str) -> Optional[PaperInterpretation]:
        """获取已有的解析结果"""
        return self.db.query(PaperInterpretation).filter(
            PaperInterpretation.paper_id == paper_id
        ).order_by(PaperInterpretation.id.desc()).first()

    def _convert_interpretation_to_dict(self, interp: PaperInterpretation) -> Dict:
        """将数据库中的解析结果转换为字典"""
        return {
            "core_contributions": interp.core_contributions,
            "experimental_methods": interp.experimental_methods,
            "datasets": interp.datasets,
            "conclusions": interp.conclusions,
            "innovations": interp.innovations,
            "limitations": interp.limitations,
            "key_references": interp.references,
            "confidence_score": interp.confidence_score,
            "interpretation_model": interp.interpretation_model,
            "interpretation_time": interp.interpretation_time.isoformat()
        }

    def _print_interpretation_result(self, result: Dict, paper: Paper):
        """打印解析结果"""
        print("\n" + "="*80)
        print("论文基本信息")
        print("="*80)
        print(f"标题: {paper.title}")
        print(f"作者: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}")
        print(f"分类: {', '.join(paper.categories)}")
        print(f"发表日期: {paper.publication_date.strftime('%Y-%m-%d') if paper.publication_date else '未知'}")
        print(f"论文ID: {paper.paper_id}")
        print(f"arXiv链接: https://arxiv.org/abs/{paper.arxiv_id}")

        print("\n" + "="*80)
        print("论文摘要")
        print("="*80)
        print(paper.abstract[:500] + "..." if len(paper.abstract) > 500 else paper.abstract)

        print("\n" + "="*80)
        print(f"大模型解析结果 (置信度: {result.get('confidence_score', 0):.2f} | 模型: {result.get('interpretation_model', settings.MODEL_NAME)})")
        print("="*80)

        # 核心贡献
        if result.get("core_contributions"):
            print("\n核心贡献:")
            for i, contrib in enumerate(result["core_contributions"], 1):
                print(f"  {i}. {contrib}")

        # 实验方法
        if result.get("experimental_methods"):
            print("\n实验方法:")
            for i, method in enumerate(result["experimental_methods"], 1):
                print(f"  {i}. {method}")

        # 使用的数据集
        if result.get("datasets"):
            print("\n数据集:")
            for i, dataset in enumerate(result["datasets"], 1):
                print(f"  {i}. {dataset}")

        # 结论
        if result.get("conclusions"):
            print("\n结论:")
            for i, conclusion in enumerate(result["conclusions"], 1):
                print(f"  {i}. {conclusion}")

        # 创新点
        if result.get("innovations"):
            print("\n创新点:")
            for i, innovation in enumerate(result["innovations"], 1):
                print(f"  {i}. {innovation}")

        # 局限性
        if result.get("limitations"):
            print("\n局限性:")
            for i, limitation in enumerate(result["limitations"], 1):
                print(f"  {i}. {limitation}")

        # 关键参考文献
        if result.get("key_references"):
            print("\n关键参考文献:")
            for i, ref in enumerate(result["key_references"][:5], 1):  # 只显示前5个
                print(f"  {i}. {ref}")
            if len(result["key_references"]) > 5:
                print(f"  ... 还有 {len(result['key_references']) - 5} 个参考文献")

        print("\n" + "="*80)
        print("解析完成！你可以根据以上结果评估解析准确度。")
        print("="*80)

    def _save_test_report(self, paper: Paper, result: Dict):
        """保存测试报告到文件"""
        report = {
            "paper_info": {
                "paper_id": paper.paper_id,
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "categories": paper.categories,
                "publication_date": paper.publication_date.isoformat() if paper.publication_date else None
            },
            "interpretation_result": result,
            "metadata": {
                "model": result.get("interpretation_model", settings.MODEL_NAME),
                "confidence_score": result.get("confidence_score", 0),
                "test_time": result.get("interpretation_time", "unknown")
            }
        }

        filename = f"interpretation_test_{paper.arxiv_id}_{result.get('interpretation_time', '').replace(':', '-')[:19]}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"测试报告已保存到: {filepath}")

    async def test_batch(self, arxiv_ids: List[str], use_abstract_only: bool = True) -> List[Dict]:
        """批量测试多篇论文"""
        logger.info(f"开始批量测试 {len(arxiv_ids)} 篇论文")
        results = []

        for i, arxiv_id in enumerate(arxiv_ids, 1):
            logger.info(f"\n[{i}/{len(arxiv_ids)}] 处理论文: {arxiv_id}")
            try:
                result = await self.test_by_arxiv_id(arxiv_id, use_abstract_only, save_report=True)
                results.append(result)
            except Exception as e:
                logger.error(f"处理论文 {arxiv_id} 失败: {str(e)}")
                results.append({"success": False, "arxiv_id": arxiv_id, "error": str(e)})

            # 避免请求过于频繁
            if i < len(arxiv_ids):
                await asyncio.sleep(1)

        # 统计结果
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"\n{'='*60}")
        logger.info(f"批量测试完成: 成功 {success_count}/{len(results)}")
        logger.info(f"{'='*60}")

        return results

    async def test_by_search_query(self, query: str, max_results: int = 5, categories: List[str] = None) -> List[Dict]:
        """搜索论文并测试"""
        logger.info(f"搜索论文: {query} (最多 {max_results} 篇)")

        papers = self.crawler.search_and_save(
            query=query,
            max_results=max_results,
            categories=categories or ["cs.LG"],
            download_pdfs=False
        )

        if not papers:
            logger.warning("未搜索到论文")
            return []

        arxiv_ids = [p["arxiv_id"] for p in papers]
        return await self.test_batch(arxiv_ids)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="论文解读准确度测试工具")
    parser.add_argument("--id", type=str, help="要测试的论文arXiv ID")
    parser.add_argument("--batch", type=str, nargs="+", help="批量测试的论文ID列表")
    parser.add_argument("--query", type=str, help="搜索关键词，测试搜索到的论文")
    parser.add_argument("--max-results", type=int, default=5, help="搜索时返回的最大结果数")
    parser.add_argument("--categories", type=str, nargs="+", default=["cs.LG"], help="搜索分类")
    parser.add_argument("--full-pdf", action="store_true", help="使用全文解析（需要先下载PDF）")
    parser.add_argument("--force-reparse", action="store_true", help="强制重新解析，忽略已有结果")
    parser.add_argument("--output-dir", type=str, default="./test_reports", help="测试报告输出目录")

    args = parser.parse_args()

    tester = InterpretationTester(output_dir=args.output_dir)

    if args.id:
        # 单个论文测试
        await tester.test_by_arxiv_id(
            args.id,
            use_abstract_only=not args.full_pdf,
            force_reparse=args.force_reparse
        )
    elif args.batch:
        # 批量测试
        await tester.test_batch(
            args.batch,
            use_abstract_only=not args.full_pdf
        )
    elif args.query:
        # 搜索测试
        await tester.test_by_search_query(
            args.query,
            max_results=args.max_results,
            categories=args.categories
        )
    else:
        # 默认测试：解析Transformer论文
        logger.info("使用默认测试论文：Attention Is All You Need (1706.03762)")
        await tester.test_by_arxiv_id("1706.03762", use_abstract_only=True)


if __name__ == "__main__":
    asyncio.run(main())
