"""
知识库API接口
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

from src.db.database import get_db
from src.db.models import Paper, ReproductionTask
from src.modules.knowledge.vector_store import VectorStore

router = APIRouter()

class SearchResponse(BaseModel):
    total: int
    papers: List[dict]

@router.post("/search", response_model=SearchResponse, summary="语义搜索论文")
async def search_papers(
    query: str = Query(..., description="搜索查询"),
    limit: int = Query(10, ge=1, le=100, description="返回结果数量"),
    source: Optional[str] = Query(None, description="来源过滤，如arxiv")
):
    """
    基于语义搜索论文知识库
    """
    vector_store = VectorStore()
    await vector_store.initialize()

    filter_conditions = {}
    if source:
        filter_conditions["source"] = source

    papers = await vector_store.search_papers(
        query=query,
        limit=limit,
        filter_conditions=filter_conditions if filter_conditions else None
    )

    return {
        "total": len(papers),
        "papers": papers
    }

@router.get("/similar/{paper_id}", response_model=SearchResponse, summary="获取相似论文")
async def get_similar_papers(
    paper_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回结果数量")
):
    """
    获取与指定论文相似的论文列表
    """
    vector_store = VectorStore()
    await vector_store.initialize()

    papers = await vector_store.get_similar_papers(
        paper_id=paper_id,
        limit=limit
    )

    return {
        "total": len(papers),
        "papers": papers
    }

@router.post("/index/{paper_id}", summary="将论文添加到索引")
async def add_paper_to_index(paper_id: str):
    """
    将指定论文添加到向量索引
    """
    vector_store = VectorStore()
    await vector_store.initialize()

    await vector_store.add_paper_to_index(paper_id)

    return {
        "paper_id": paper_id,
        "message": "添加成功"
    }

@router.delete("/index/{paper_id}", summary="从索引中删除论文")
async def delete_paper_from_index(paper_id: str):
    """
    从向量索引中删除指定论文
    """
    vector_store = VectorStore()
    await vector_store.initialize()

    await vector_store.delete_paper_from_index(paper_id)

    return {
        "paper_id": paper_id,
        "message": "删除成功"
    }

@router.get("/stats", summary="获取知识库统计信息")
async def get_knowledge_stats():
    """
    获取知识库的统计信息
    """
    vector_store = VectorStore()
    await vector_store.initialize()

    stats = vector_store.get_index_stats()

    db = next(get_db())
    try:
        total_papers = db.query(Paper).count()
        interpreted_papers = db.query(Paper).filter(Paper.status == "interpreted").count()
        reproduced_papers = db.query(ReproductionTask).filter(ReproductionTask.status == "success").count()
    finally:
        db.close()

    return {
        "indexed_papers": stats["count"],
        "total_papers": total_papers,
        "interpreted_papers": interpreted_papers,
        "reproduced_papers": reproduced_papers
    }
