#!/usr/bin/env python3
"""
命令行接口
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from arxiv_crawler import ArXivCrawler, format_paper_list
from paper_interpreter import PaperInterpreter, format_interpretation_result
from reproduction_generator import ReproductionGenerator, format_reproduction_result
from vector_store import VectorStore, format_search_results

from config import check_config, init_config, show_config


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="AI论文助手 - 一站式学术论文处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  🔍 搜索论文：paper-assistant search "large language model" --max-results 5
  📝 解读论文：paper-assistant interpret 2310.06825 --full
  🔬 生成复现脚本：paper-assistant reproduce 2310.06825
  🧠 语义搜索：paper-assistant search-semantic "chain of thought"
  📚 相似论文推荐：paper-assistant similar 2310.06825
  ⚙️  初始化配置：paper-assistant init
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="可用命令")

    # 初始化配置
    subparsers.add_parser("init", help="初始化配置文件")

    # 显示配置
    subparsers.add_parser("config", help="显示当前配置")

    # 搜索论文
    search_parser = subparsers.add_parser("search", help="搜索arXiv论文")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument(
        "--max-results", type=int, default=10, help="返回结果数量"
    )
    search_parser.add_argument("--categories", help="分类过滤，逗号分隔，如cs.CL,cs.AI")
    search_parser.add_argument(
        "--save", action="store_true", help="保存结果到向量数据库"
    )

    # 解读论文
    interpret_parser = subparsers.add_parser("interpret", help="解读论文")
    interpret_parser.add_argument("paper_id", help="arXiv论文ID")
    interpret_parser.add_argument("--pdf", help="本地PDF文件路径")
    interpret_parser.add_argument(
        "--full", action="store_true", help="完整解读（需要下载PDF）"
    )
    interpret_parser.add_argument(
        "--output",
        choices=["text", "json", "markdown"],
        default="text",
        help="输出格式",
    )

    # 生成复现脚本
    reproduce_parser = subparsers.add_parser("reproduce", help="生成论文复现代码")
    reproduce_parser.add_argument("paper_id", help="arXiv论文ID")
    reproduce_parser.add_argument(
        "--docker", action="store_true", default=True, help="生成Dockerfile（默认）"
    )
    reproduce_parser.add_argument(
        "--venv", action="store_true", help="生成虚拟环境配置"
    )
    reproduce_parser.add_argument("--run", action="store_true", help="自动执行复现脚本")

    # 语义搜索
    search_semantic_parser = subparsers.add_parser(
        "search-semantic", help="语义搜索论文"
    )
    search_semantic_parser.add_argument("query", help="搜索文本")
    search_semantic_parser.add_argument(
        "--limit", type=int, default=5, help="返回结果数量"
    )
    search_semantic_parser.add_argument(
        "--threshold", type=float, default=0.7, help="相似度阈值"
    )

    # 相似论文推荐
    similar_parser = subparsers.add_parser("similar", help="推荐相似论文")
    similar_parser.add_argument("paper_id", help="arXiv论文ID")
    similar_parser.add_argument("--limit", type=int, default=10, help="推荐数量")

    # 知识图谱生成（预留）
    graph_parser = subparsers.add_parser("graph", help="生成论文知识图谱")
    graph_parser.add_argument("paper_id", help="arXiv论文ID")
    graph_parser.add_argument("--depth", type=int, default=2, help="扩展深度")
    graph_parser.add_argument("--output", help="导出HTML路径")

    args = parser.parse_args()

    # 初始化配置
    if args.command == "init":
        init_config()
        return 0

    # 显示配置
    if args.command == "config":
        show_config()
        return 0

    # 检查配置是否完整
    if not check_config():
        return 1

    crawler = ArXivCrawler()
    interpreter = PaperInterpreter()
    vector_store = VectorStore()
    reproduction_generator = ReproductionGenerator()

    # 搜索论文
    if args.command == "search":
        categories = args.categories.split(",") if args.categories else None
        papers = crawler.search(
            args.query, max_results=args.max_results, categories=categories
        )
        print(format_paper_list(papers))

        if args.save and papers:
            vector_store.add_papers(papers)
            print(f"\n✅ 已将 {len(papers)} 篇论文保存到向量数据库")
        return 0

    # 解读论文
    if args.command == "interpret":
        paper = crawler.get_paper_by_id(args.paper_id)
        if not paper:
            print(f"❌ 论文不存在：{args.paper_id}")
            return 1

        pdf_path = Path(args.pdf) if args.pdf else None
        if pdf_path and not pdf_path.exists():
            print(f"❌ PDF文件不存在：{args.pdf}")
            return 1

        print(f"🔍 正在解读论文：{paper.title}...")
        result = asyncio.run(interpreter.interpret_paper(paper, pdf_path, args.full))

        if args.output == "json":
            import json

            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.output == "markdown":
            print(format_interpretation_result(paper, result))
        else:
            print(format_interpretation_result(paper, result))

        # 自动添加到向量库
        vector_store.add_paper(paper)
        return 0

    # 生成复现脚本
    if args.command == "reproduce":
        paper = crawler.get_paper_by_id(args.paper_id)
        if not paper:
            print(f"❌ 论文不存在：{args.paper_id}")
            return 1

        print(f"🔬 正在生成复现代码：{paper.title}...")
        result = asyncio.run(reproduction_generator.generate_code(paper))
        save_dir = reproduction_generator.save_to_files(args.paper_id, result)
        print(format_reproduction_result(paper, save_dir))
        return 0

    # 语义搜索
    if args.command == "search-semantic":
        results = vector_store.semantic_search(
            args.query, limit=args.limit, threshold=args.threshold
        )
        print(format_search_results(results))
        return 0

    # 相似论文推荐
    if args.command == "similar":
        # 先确保论文在向量库中
        paper = crawler.get_paper_by_id(args.paper_id)
        if not paper:
            print(f"❌ 论文不存在：{args.paper_id}")
            return 1
        vector_store.add_paper(paper)

        results = vector_store.get_similar_papers(args.paper_id, limit=args.limit)
        if not results:
            print("❌ 未找到相似论文，请先添加更多论文到向量库")
            return 0

        output = [f"📚 与 {args.paper_id} 相似的论文（共 {len(results)} 篇）", "=" * 60]
        for i, paper in enumerate(results, 1):
            output.extend(
                [
                    f"\n{i}. **{paper['title']}** (arXiv:{paper['paper_id']})",
                    f"   🔢 相似度：{paper['similarity_score']:.4f}",
                    f"   👥 作者：{', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}",
                    f"   📅 发表日期：{paper['published']}",
                    f"   🔗 链接：https://arxiv.org/abs/{paper['paper_id']}",
                ]
            )
        print("\n".join(output))
        return 0

    # 知识图谱生成（预留功能）
    if args.command == "graph":
        print("⚠️  知识图谱功能开发中，敬请期待")
        return 0

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
