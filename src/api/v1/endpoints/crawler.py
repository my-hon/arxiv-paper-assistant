"""
爬虫API接口
"""
import os
from fastapi import APIRouter, Query
from loguru import logger
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from src.core.exceptions import NotFoundError, StorageError, ValidationError
from src.db.database import get_db
from src.db.models import Paper
from src.modules.crawler.arxiv_client import AsyncArxivClient

router = APIRouter()

class SearchRequest(BaseModel):
    query: str = Query("", description="搜索关键词")
    start: int = Query(0, ge=0, description="起始索引")
    max_results: int = Query(10, ge=1, le=100, description="最大返回结果数")
    categories: Optional[List[str]] = Query(None, description="分类列表，如['cs.AI', 'cs.CV']")
    author: Optional[str] = Query(None, description="作者名")
    start_date: Optional[datetime] = Query(None, description="开始日期")
    end_date: Optional[datetime] = Query(None, description="结束日期")
    save_to_db: bool = Query(True, description="是否保存到数据库")

class SearchResponse(BaseModel):
    total: int
    papers: List[dict]
    saved_count: int

@router.post("/search/arxiv", response_model=SearchResponse, summary="搜索arXiv论文")
async def search_arxiv(request: SearchRequest):
    """
    从arXiv搜索论文
    """
    client = AsyncArxivClient()

    papers = await client.search_papers(
        query=request.query,
        max_results=request.max_results,
        categories=request.categories,
        author=request.author
    )

    # 支持分页（简单实现，跳过前面的结果）
    if request.start > 0 and len(papers) > request.start:
        papers = papers[request.start:]

    saved_count = 0
    if request.save_to_db and papers:
        saved_count = client.save_papers_to_db(papers)

    return {
        "total": len(papers),
        "papers": papers,
        "saved_count": saved_count
    }

@router.post("/download/{paper_id}", summary="下载论文PDF")
async def download_paper(paper_id: str):
    """
    下载指定论文的PDF
    """
    db = next(get_db())
    try:
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()

        if not paper:
            raise NotFoundError(f"论文不存在: {paper_id}")

        if not paper.pdf_url:
            raise ValidationError(f"论文没有PDF链接: {paper_id}")

        # 如果已经下载过，直接返回路径
        if paper.pdf_path and os.path.exists(paper.pdf_path):
            return {
                "paper_id": paper_id,
                "pdf_path": paper.pdf_path,
                "message": "文件已存在，无需重复下载"
            }

        client = AsyncArxivClient()
        pdf_path = await client.download_pdf_by_id(paper.arxiv_id)

        if not pdf_path:
            raise NotFoundError(f"未找到对应的arXiv论文: {paper.arxiv_id}")

        # 更新论文信息
        paper.pdf_path = pdf_path
        paper.status = "downloaded"
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception(f"更新论文PDF信息失败 {paper_id}: {str(e)}")
            raise StorageError(f"PDF已下载但更新论文记录失败: {str(e)}") from e

        return {
            "paper_id": paper_id,
            "pdf_path": pdf_path,
            "message": "下载成功"
        }
    finally:
        db.close()

class AdvancedSearchRequest(BaseModel):
    """高级搜索请求模型"""
    query: Optional[str] = Query("", description="通用搜索关键词")
    max_results: int = Query(10, ge=1, le=100, description="最大返回结果数")
    categories: Optional[List[str]] = Query(None, description="分类列表，如['cs.AI', 'cs.CV']")
    author: Optional[str] = Query(None, description="作者名")
    title: Optional[str] = Query(None, description="标题关键词")
    abstract: Optional[str] = Query(None, description="摘要关键词")
    journal_reference: Optional[str] = Query(None, description="期刊引用关键词")
    save_to_db: bool = Query(True, description="是否保存到数据库")
    download_pdfs: bool = Query(False, description="是否同时下载PDF文件")


@router.post("/search/arxiv/advanced", summary="高级搜索arXiv论文")
async def advanced_search_arxiv(request: AdvancedSearchRequest):
    """
    高级搜索arXiv论文，支持多维度筛选
    """
    client = AsyncArxivClient()

    papers = await client.search_and_save(
        query=request.query,
        max_results=request.max_results,
        categories=request.categories,
        author=request.author,
        title=request.title,
        abstract=request.abstract,
        journal_reference=request.journal_reference,
        download_pdfs=request.download_pdfs
    )

    return {
        "total": len(papers),
        "papers": papers,
        "saved_count": len(papers),
        "downloaded_pdfs": sum(1 for p in papers if p.get("local_pdf_path"))
    }


@router.get("/search/arxiv/id/{arxiv_id}", summary="根据arXiv ID搜索论文")
async def search_by_arxiv_id(arxiv_id: str, save_to_db: bool = Query(True, description="是否保存到数据库")):
    """
    根据arXiv ID搜索单个论文
    """
    client = AsyncArxivClient()
    paper = await client.search_by_id(arxiv_id)

    if not paper:
        raise NotFoundError(f"未找到该论文: {arxiv_id}")

    if save_to_db:
        client.save_papers_to_db([paper])

    return {
        "paper": paper
    }


@router.get("/sources", summary="获取支持的数据源")
async def get_supported_sources():
    """
    获取系统支持的论文数据源列表
    """
    return {
        "sources": [
            {
                "id": "arxiv",
                "name": "arXiv",
                "description": "康奈尔大学开放获取预印本平台",
                "supported": True,
                "features": ["搜索", "下载PDF", "高级筛选"]
            },
            {
                "id": "semantic_scholar",
                "name": "Semantic Scholar",
                "description": "AI驱动的学术搜索引擎",
                "supported": False,
                "notice": "开发中"
            },
            {
                "id": "ieee_xplore",
                "name": "IEEE Xplore",
                "description": "IEEE电子图书馆",
                "supported": False,
                "notice": "开发中"
            }
        ]
    }
