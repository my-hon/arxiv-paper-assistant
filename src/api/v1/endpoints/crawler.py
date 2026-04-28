"""
爬虫API接口
"""
import os
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from src.modules.crawler.arxiv_client import ArxivClient, AsyncArxivClient

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
    try:
        client = AsyncArxivClient()

        # 执行搜索
        results = client.search_papers(
            query=request.query,
            max_results=request.max_results,
            categories=request.categories,
            author=request.author
        )

        # 解析结果
        papers = []
        for result in results:
            paper = client.parse_result(result)
            if paper:
                papers.append(paper)

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.post("/download/{paper_id}", summary="下载论文PDF")
async def download_paper(paper_id: str):
    """
    下载指定论文的PDF
    """
    try:
        from src.db.database import get_db
        from src.db.models import Paper

        db = next(get_db())
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()

        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")

        if not paper.pdf_url:
            raise HTTPException(status_code=400, detail="论文没有PDF链接")

        # 如果已经下载过，直接返回路径
        if paper.pdf_path and os.path.exists(paper.pdf_path):
            return {
                "paper_id": paper_id,
                "pdf_path": paper.pdf_path,
                "message": "文件已存在，无需重复下载"
            }

        client = AsyncArxivClient()

        # 搜索论文获取最新信息
        arxiv_id = paper.arxiv_id
        result = client.search_by_id(arxiv_id)

        if not result:
            raise HTTPException(status_code=404, detail="未找到对应的arXiv论文")

        # 下载PDF
        pdf_path = client.download_pdf(result)

        if not pdf_path:
            raise HTTPException(status_code=500, detail="下载PDF失败")

        # 更新论文信息
        paper.pdf_path = pdf_path
        paper.status = "downloaded"
        db.commit()

        return {
            "paper_id": paper_id,
            "pdf_path": pdf_path,
            "message": "下载成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

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
    try:
        client = AsyncArxivClient()

        # 执行搜索
        papers = client.search_and_save(
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"高级搜索失败: {str(e)}")


@router.get("/search/arxiv/id/{arxiv_id}", summary="根据arXiv ID搜索论文")
async def search_by_arxiv_id(arxiv_id: str, save_to_db: bool = Query(True, description="是否保存到数据库")):
    """
    根据arXiv ID搜索单个论文
    """
    try:
        client = AsyncArxivClient()
        result = client.search_by_id(arxiv_id)

        if not result:
            raise HTTPException(status_code=404, detail="未找到该论文")

        paper = client.parse_result(result)

        if save_to_db and paper:
            client.save_papers_to_db([paper])

        return {
            "paper": paper
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


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
