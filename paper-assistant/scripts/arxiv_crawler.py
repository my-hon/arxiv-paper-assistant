"""
arXiv论文爬取模块
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import aiohttp
import arxiv
from loguru import logger

from .config import settings


@dataclass
class PaperInfo:
    """论文信息数据类"""

    paper_id: str
    title: str
    authors: List[str]
    summary: str
    published: str
    categories: List[str]
    pdf_url: str
    entry_id: str


class ArXivCrawler:
    """arXiv爬虫客户端"""

    def __init__(self):
        self.client = arxiv.Client(
            page_size=100, delay_seconds=settings.CRAWL_RATE_LIMIT, num_retries=3
        )

    def search(
        self, query: str, max_results: int = 10, categories: Optional[List[str]] = None
    ) -> List[PaperInfo]:
        """
        搜索arXiv论文

        Args:
            query: 搜索关键词
            max_results: 返回结果数量
            categories: 分类过滤，如["cs.CL", "cs.AI"]

        Returns:
            论文信息列表
        """
        # 构建搜索查询
        if categories:
            category_query = " OR ".join(f"cat:{cat}" for cat in categories)
            query = f"({query}) AND ({category_query})"

        logger.info(f"搜索论文：{query}")
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        for result in self.client.results(search):
            paper = PaperInfo(
                paper_id=result.entry_id.split("/")[-1].split("v")[0],
                title=result.title,
                authors=[author.name for author in result.authors],
                summary=result.summary,
                published=result.published.strftime("%Y-%m-%d"),
                categories=result.categories,
                pdf_url=result.pdf_url,
                entry_id=result.entry_id,
            )
            papers.append(paper)

        logger.info(f"找到 {len(papers)} 篇论文")
        return papers

    def get_paper_by_id(self, paper_id: str) -> Optional[PaperInfo]:
        """根据ID获取论文信息"""
        try:
            search = arxiv.Search(id_list=[paper_id], max_results=1)
            result = next(self.client.results(search))

            return PaperInfo(
                paper_id=paper_id,
                title=result.title,
                authors=[author.name for author in result.authors],
                summary=result.summary,
                published=result.published.strftime("%Y-%m-%d"),
                categories=result.categories,
                pdf_url=result.pdf_url,
                entry_id=result.entry_id,
            )
        except Exception as e:
            logger.error(f"获取论文信息失败：{e}")
            return None

    async def download_pdf(
        self, paper_id: str, save_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        下载论文PDF

        Args:
            paper_id: arXiv论文ID
            save_path: 保存路径，默认使用STORAGE_PATH/pdfs/

        Returns:
            下载后的文件路径
        """
        if save_path is None:
            save_path = settings.STORAGE_PATH / "pdfs" / f"{paper_id}.pdf"

        # 检查文件是否已存在
        if save_path.exists():
            logger.info(f"PDF已存在：{save_path}")
            return save_path

        # 获取论文信息
        paper = self.get_paper_by_id(paper_id)
        if not paper:
            logger.error(f"论文不存在：{paper_id}")
            return None

        logger.info(f"下载PDF：{paper.pdf_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    paper.pdf_url, timeout=settings.CRAWL_TIMEOUT
                ) as response:
                    if response.status == 200:
                        content = await response.read()
                        save_path.parent.mkdir(parents=True, exist_ok=True)
                        save_path.write_bytes(content)
                        logger.info(f"PDF下载完成：{save_path}")
                        return save_path
                    else:
                        logger.error(f"下载失败，状态码：{response.status}")
                        return None
        except Exception as e:
            logger.error(f"下载PDF失败：{e}")
            return None


def format_paper_list(papers: List[PaperInfo]) -> str:
    """格式化论文列表为输出字符串"""
    if not papers:
        return "未找到相关论文"

    output = [f"📚 搜索结果（共 {len(papers)} 篇）", "=" * 50]

    for i, paper in enumerate(papers, 1):
        output.extend(
            [
                f"\n{i}. **{paper.title}** (arXiv:{paper.paper_id})",
                f"   👥 作者：{', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}",
                f"   📅 发表日期：{paper.published}",
                f"   🏷️  分类：{', '.join(paper.categories[:3])}",
                f"   🔗 链接：https://arxiv.org/abs/{paper.paper_id}",
            ]
        )
        # 显示摘要前200字
        summary = paper.summary[:200].replace("\n", " ")
        if len(paper.summary) > 200:
            summary += "..."
        output.append(f"   📄 摘要：{summary}")

    return "\n".join(output)


# 测试代码
if __name__ == "__main__":
    crawler = ArXivCrawler()
    papers = crawler.search("large language model", max_results=5)
    print(format_paper_list(papers))

    if papers:
        asyncio.run(crawler.download_pdf(papers[0].paper_id))
