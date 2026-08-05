"""arXiv论文搜索和下载模块，基于官方arxiv.py库实现。

提供简洁可靠的arXiv API访问，支持论文搜索、元数据解析和PDF下载功能。
符合arXiv API使用规范，内置速率限制和重试机制。
"""

import asyncio
import os
from typing import Dict, List, Optional

import arxiv
from loguru import logger

from src.config.settings import settings
from src.core.exceptions import CrawlerError, StorageError
from src.db.database import get_db


class ArxivClient:
    """arXiv API客户端，封装官方arxiv.py库的功能。

    提供论文搜索、元数据解析、PDF下载和数据库持久化功能，
    内置速率限制和重试机制，符合arXiv API使用规范。
    """

    def __init__(self):
        """初始化arXiv客户端，配置速率限制和重试策略。

        从settings中读取CRAWL_RATE_LIMIT和CRAWL_MAX_RETRIES配置，
        初始化arxiv.Client实例。
        """
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=settings.CRAWL_RATE_LIMIT,
            num_retries=settings.CRAWL_MAX_RETRIES,
        )
        logger.info("arxiv.py客户端初始化完成")

    async def search_papers(
        self,
        query: str,
        max_results: int = 10,
        categories: Optional[List[str]] = None,
        author: Optional[str] = None,
        title: Optional[str] = None,
        abstract: Optional[str] = None,
        comment: Optional[str] = None,
        journal_reference: Optional[str] = None,
        subject_category: Optional[str] = None,
        report_number: Optional[str] = None,
        id_list: Optional[List[str]] = None,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
        sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending,
    ) -> List[Dict]:
        """根据条件搜索arXiv论文。

        Args:
            query: 通用搜索关键词，在所有字段中匹配。
            max_results: 最大返回结果数，默认10。
            categories: 分类列表，如["cs.AI", "cs.CV"]，支持多分类OR查询。
            author: 作者名，支持部分匹配。
            title: 标题关键词。
            abstract: 摘要关键词。
            comment: 论文评论字段关键词。
            journal_reference: 期刊引用关键词。
            subject_category: 主题分类，单分类精确匹配。
            report_number: 报告编号。
            id_list: arXiv ID列表，提供时直接根据ID精确搜索，忽略其他条件。
            sort_by: 排序字段，可选值：SubmittedDate, LastUpdatedDate, Relevance，
                默认按提交日期。
            sort_order: 排序顺序，可选值：Ascending, Descending，默认降序。

        Returns:
            List[Dict]: 标准化的论文信息字典列表。

        Raises:
            CrawlerError: 当arXiv API请求失败时抛出。
        """
        # 构建高级查询字符串
        query_parts = []

        # 如果提供了id_list，不需要其他查询条件
        if not id_list:
            if query:
                query_parts.append(f"all:{query}")
            if author:
                query_parts.append(f"au:{author}")
            if title:
                query_parts.append(f"ti:{title}")
            if abstract:
                query_parts.append(f"abs:{abstract}")
            if comment:
                query_parts.append(f"co:{comment}")
            if journal_reference:
                query_parts.append(f"jr:{journal_reference}")
            if subject_category:
                query_parts.append(f"cat:{subject_category}")
            if report_number:
                query_parts.append(f"rn:{report_number}")
            if categories:
                cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
                query_parts.append(f"({cat_query})")

        search_query = " AND ".join(query_parts) if query_parts else ""

        logger.info(f"构建搜索查询: {search_query}")

        search = arxiv.Search(
            query=search_query,
            id_list=id_list or [],
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        loop = asyncio.get_event_loop()
        try:
            # 在单独的线程中运行同步的arxiv搜索
            results = await loop.run_in_executor(None, list, self.client.results(search))
            papers = []
            for result in results:
                paper = {
                    "paper_id": result.entry_id.split("/")[-1],
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "abstract": result.summary,
                    "publication_date": result.published,
                    "updated_date": result.updated,
                    "categories": result.categories,
                    "url": result.entry_id,
                    "pdf_url": result.pdf_url,
                    "doi": result.doi,
                    "comment": result.comment,
                    "journal_ref": result.journal_ref,
                }
                papers.append(paper)
            logger.info(f"搜索完成，找到 {len(papers)} 篇论文")
            return papers
        except Exception as e:
            logger.exception(f"搜索论文失败: {str(e)}")
            raise CrawlerError(f"arXiv搜索失败: {str(e)}") from e

    async def search_by_id(self, arxiv_id: str) -> Optional[Dict]:
        """根据arXiv ID精确搜索单个论文。

        Args:
            arxiv_id: arXiv论文ID，如"2310.06825"，可包含版本号或不包含。

        Returns:
            Optional[Dict]: 找到返回标准化的论文信息字典，未找到返回None。

        Raises:
            CrawlerError: arXiv接口调用失败时抛出。
        """
        results = await self.search_papers(query="", id_list=[arxiv_id], max_results=1)
        return results[0] if results else None

    @staticmethod
    def parse_result(result: arxiv.Result) -> Dict:
        """将arxiv.Result对象解析为标准化的字典格式。

        提取核心元数据字段，统一格式以便后续处理和数据库存储。

        Args:
            result: arxiv.Result对象，包含论文完整元数据。

        Returns:
            Dict: 标准化的论文信息字典，包含以下字段：
                paper_id: 统一格式的论文ID，前缀为"arxiv_"
                title: 论文标题，已去除换行符
                authors: 作者名列表
                abstract: 论文摘要，已去除换行符
                arxiv_id: 原始arXiv ID
                publication_date: 发布日期，datetime对象
                updated_date: 最后更新日期，datetime对象
                source: 数据来源，固定为"arxiv"
                categories: 分类标签列表
                url: 论文详情页URL
                pdf_url: PDF下载链接
                doi: DOI编号（如有）
                journal_ref: 期刊引用信息（如有）
                comment: 论文评论信息（如有）
                primary_category: 主要分类标签（如有）

        Raises:
            CrawlerError: 结果字段缺失或格式异常导致解析失败时抛出。
        """
        try:
            # 提取arXiv ID，去掉版本号
            arxiv_id = result.entry_id.split("/")[-1].split("v")[0]

            paper = {
                "paper_id": f"arxiv_{arxiv_id}",
                "title": result.title.replace("\n", " ").strip(),
                "authors": [author.name for author in result.authors],
                "abstract": result.summary.replace("\n", " ").strip(),
                "arxiv_id": arxiv_id,
                "publication_date": result.published,
                "updated_date": result.updated,
                "source": "arxiv",
                "categories": result.categories,
                "url": result.entry_id,
                "pdf_url": result.pdf_url,
                "doi": result.doi,
            }

            # 可选字段，只有存在时才添加
            if hasattr(result, "journal_ref") and result.journal_ref:
                paper["journal_ref"] = result.journal_ref
            if hasattr(result, "comment") and result.comment:
                paper["comment"] = result.comment
            if hasattr(result, "primary_category") and result.primary_category:
                paper["primary_category"] = result.primary_category

            return paper

        except Exception as e:
            logger.exception(f"解析论文结果失败: {str(e)}")
            raise CrawlerError(f"解析arXiv论文结果失败: {str(e)}") from e

    def download_pdf(
        self,
        result: arxiv.Result,
        save_dir: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """下载论文PDF文件到本地。

        自动检查文件是否已存在，避免重复下载；自动创建保存目录。

        Args:
            result: arxiv.Result对象，包含PDF下载链接。
            save_dir: 保存目录，默认使用settings.PDF_STORAGE_PATH。
            filename: 保存文件名，默认使用"arxiv_{id}.pdf"格式。

        Returns:
            Optional[str]: 下载成功返回本地文件路径，论文没有PDF链接时返回None。

        Raises:
            CrawlerError: 下载过程失败时抛出。
        """
        if not result.pdf_url:
            logger.warning(f"论文 {result.entry_id} 没有PDF链接")
            return None

        if not save_dir:
            save_dir = settings.PDF_STORAGE_PATH

        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)

        if not filename:
            arxiv_id = result.entry_id.split("/")[-1].split("v")[0]
            filename = f"arxiv_{arxiv_id}.pdf"

        save_path = os.path.join(save_dir, filename)

        # 如果文件已存在，直接返回路径
        if os.path.exists(save_path):
            logger.info(f"PDF已存在: {save_path}")
            return save_path

        try:
            logger.info(f"开始下载PDF: {result.title}")
            downloaded_path = result.download_pdf(dirpath=save_dir, filename=filename)
            logger.info(f"PDF下载完成: {downloaded_path}")
            return downloaded_path

        except Exception as e:
            logger.exception(f"下载PDF失败 {result.title}: {str(e)}")
            raise CrawlerError(f"下载PDF失败 {result.title}: {str(e)}") from e

    async def download_pdf_by_id(
        self,
        arxiv_id: str,
        save_dir: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """根据arXiv ID下载论文PDF。

        Args:
            arxiv_id: arXiv论文ID。
            save_dir: 保存目录，默认使用settings.PDF_STORAGE_PATH。
            filename: 保存文件名。

        Returns:
            Optional[str]: 下载成功返回本地文件路径，未找到论文时返回None。

        Raises:
            CrawlerError: arXiv接口调用或下载失败时抛出。
        """
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None, list, self.client.results(arxiv.Search(id_list=[arxiv_id]))
            )
        except Exception as e:
            logger.exception(f"根据ID获取arXiv论文失败 {arxiv_id}: {str(e)}")
            raise CrawlerError(f"根据ID获取arXiv论文失败 {arxiv_id}: {str(e)}") from e

        if not results:
            return None

        return await loop.run_in_executor(
            None, lambda: self.download_pdf(results[0], save_dir, filename)
        )

    def save_papers_to_db(self, papers: List[Dict]) -> int:
        """批量保存论文信息到数据库。

        自动检查论文是否已存在（根据paper_id），避免重复存储。
        自动过滤Paper模型不支持的字段，保证兼容性。

        Args:
            papers: 标准化的论文信息字典列表。

        Returns:
            int: 实际保存成功的论文数量。

        Raises:
            StorageError: 数据库提交失败时抛出。
        """
        from src.db.models import Paper

        db = next(get_db())
        saved_count = 0
        failed_ids: List[str] = []

        # 获取Paper模型的所有字段
        model_fields = {c.name for c in Paper.__table__.columns}

        for paper_data in papers:
            if not paper_data.get("paper_id"):
                continue

            # 检查是否已存在
            existing = (
                db.query(Paper).filter(Paper.paper_id == paper_data["paper_id"]).first()
            )
            if existing:
                logger.info(f"论文已存在: {paper_data['paper_id']}")
                continue

            try:
                # 只保留Paper模型中存在的字段
                filtered_data = {
                    k: v for k, v in paper_data.items() if k in model_fields
                }

                paper = Paper(**filtered_data)
                db.add(paper)
                saved_count += 1
            except Exception as e:
                logger.exception(f"保存论文失败 {paper_data['paper_id']}: {str(e)}")
                failed_ids.append(paper_data["paper_id"])
                db.rollback()
                continue

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception(f"提交论文数据失败: {str(e)}")
            raise StorageError(f"保存论文到数据库失败: {str(e)}") from e
        finally:
            db.close()

        if failed_ids:
            logger.warning(f"以下论文保存失败: {', '.join(failed_ids)}")

        logger.info(f"成功保存 {saved_count} 篇论文到数据库")
        return saved_count

    async def search_and_save(
        self,
        query: str,
        max_results: int = 10,
        categories: Optional[List[str]] = None,
        author: Optional[str] = None,
        title: Optional[str] = None,
        abstract: Optional[str] = None,
        journal_reference: Optional[str] = None,
        download_pdfs: bool = False,
    ) -> List[Dict]:
        """搜索论文并批量保存到数据库的便捷方法。

        整合搜索、解析、保存三个步骤，支持可选的PDF下载功能。

        Args:
            query: 通用搜索关键词。
            max_results: 最大返回结果数，默认10。
            categories: 分类列表，如["cs.AI", "cs.CV"]。
            author: 作者名。
            title: 标题关键词。
            abstract: 摘要关键词。
            journal_reference: 期刊引用关键词。
            download_pdfs: 是否同时下载PDF文件，默认False。

        Returns:
            List[Dict]: 保存成功的论文信息列表。

        Raises:
            CrawlerError: 搜索失败时抛出。
            StorageError: 写入数据库失败时抛出。
        """
        logger.info(f"开始搜索论文，关键词: {query}, 最大结果数: {max_results}")

        papers = await self.search_papers(
            query=query,
            max_results=max_results,
            categories=categories,
            author=author,
            title=title,
            abstract=abstract,
            journal_reference=journal_reference,
        )

        if download_pdfs:
            for paper in papers:
                paper["local_pdf_path"] = await self.download_pdf_by_id(
                    paper["paper_id"]
                )

        if papers:
            self.save_papers_to_db(papers)

        logger.info(f"搜索完成，共获取 {len(papers)} 篇论文")
        return papers


# 兼容别名，保持与原有导入路径一致
AsyncArxivClient = ArxivClient
