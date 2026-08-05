"""
知识库API接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from src.core.errors import handle_api_errors
from src.db.database import session_scope
from src.db.models import Paper, ReproductionTask
from src.modules.knowledge.vector_store import get_vector_store

router = APIRouter()

class SearchResponse(BaseModel):
    total: int
    papers: List[dict]

@router.post("/search", response_model=SearchResponse, summary="语义搜索论文")
@handle_api_errors("搜索失败")
async def search_papers(
    query: str = Query(..., description="搜索查询"),
    limit: int = Query(10, ge=1, le=100, description="返回结果数量"),
    source: Optional[str] = Query(None, description="来源过滤，如arxiv")
):
    """
    基于语义搜索论文知识库
    """
    vector_store = await get_vector_store()

    papers = await vector_store.search_papers(
        query=query,
        limit=limit,
        filter_conditions={"source": source} if source else None
    )

    return {
        "total": len(papers),
        "papers": papers
    }

@router.get("/similar/{paper_id}", response_model=SearchResponse, summary="获取相似论文")
@handle_api_errors("获取相似论文失败")
async def get_similar_papers(
    paper_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回结果数量")
):
    """
    获取与指定论文相似的论文列表
    """
    vector_store = await get_vector_store()

    papers = await vector_store.get_similar_papers(
        paper_id=paper_id,
        limit=limit
    )

    return {
        "total": len(papers),
        "papers": papers
    }

@router.post("/index/{paper_id}", summary="将论文添加到索引")
@handle_api_errors("添加索引失败")
async def add_paper_to_index(paper_id: str):
    """
    将指定论文添加到向量索引
    """
    vector_store = await get_vector_store()

    if not await vector_store.add_paper_to_index(paper_id):
        raise HTTPException(status_code=500, detail="添加索引失败")

    return {
        "paper_id": paper_id,
        "message": "添加成功"
    }

@router.delete("/index/{paper_id}", summary="从索引中删除论文")
@handle_api_errors("删除索引失败")
async def delete_paper_from_index(paper_id: str):
    """
    从向量索引中删除指定论文
    """
    vector_store = await get_vector_store()

    if not await vector_store.delete_paper_from_index(paper_id):
        raise HTTPException(status_code=500, detail="删除索引失败")

    return {
        "paper_id": paper_id,
        "message": "删除成功"
    }

@router.get("/stats", summary="获取知识库统计信息")
@handle_api_errors("获取统计信息失败")
async def get_knowledge_stats():
    """
    获取知识库的统计信息
    """
    vector_store = await get_vector_store()
    stats = vector_store.get_index_stats()

    with session_scope() as db:
        total_papers = db.query(Paper).count()
        interpreted_papers = db.query(Paper).filter(Paper.status == "interpreted").count()
        reproduced_papers = db.query(ReproductionTask).filter(ReproductionTask.status == "success").count()

    return {
        "indexed_papers": stats["count"],
        "total_papers": total_papers,
        "interpreted_papers": interpreted_papers,
        "reproduced_papers": reproduced_papers
    }
