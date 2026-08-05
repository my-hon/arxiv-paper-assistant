"""
论文管理API接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.core.errors import handle_api_errors
from src.core.serializers import serialize_interpretation, serialize_paper_summary
from src.db.database import session_scope
from src.db.models import Paper, PaperInterpretation
from src.modules.knowledge.vector_store import get_vector_store

router = APIRouter()

class PaperResponse(BaseModel):
    paper_id: str
    title: str
    authors: List[str]
    abstract: str
    doi: Optional[str]
    arxiv_id: Optional[str]
    publication_date: Optional[datetime]
    source: str
    categories: List[str]
    keywords: Optional[List[str]]
    url: str
    pdf_url: Optional[str]
    pdf_path: Optional[str]
    citation_count: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

@router.get("/", summary="获取论文列表")
@handle_api_errors("获取论文列表失败")
async def list_papers(
    source: Optional[str] = Query(None, description="来源过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    category: Optional[str] = Query(None, description="分类过滤"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取论文列表，支持分页和过滤
    """
    with session_scope() as db:
        query = db.query(Paper)

        if source:
            query = query.filter(Paper.source == source)
        if status:
            query = query.filter(Paper.status == status)
        if category:
            query = query.filter(Paper.categories.contains(category))
        if keyword:
            query = query.filter(Paper.title.contains(keyword) | Paper.abstract.contains(keyword))

        total = query.count()
        papers = query.order_by(Paper.publication_date.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "papers": [serialize_paper_summary(paper) for paper in papers]
        }

@router.get("/{paper_id}", response_model=PaperResponse, summary="获取论文详情")
@handle_api_errors("获取论文详情失败")
async def get_paper_detail(paper_id: str):
    """
    获取指定论文的详细信息
    """
    with session_scope() as db:
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()

        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")

        return PaperResponse.model_validate(paper, from_attributes=True)

@router.delete("/{paper_id}", summary="删除论文")
@handle_api_errors("删除论文失败")
async def delete_paper(paper_id: str):
    """
    删除指定论文及其相关数据
    """
    with session_scope() as db:
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()

        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")

        # 删除相关解读结果
        db.query(PaperInterpretation).filter(PaperInterpretation.paper_id == paper_id).delete()

        # 删除论文
        db.delete(paper)
        db.commit()

    # 从向量索引中删除
    vector_store = await get_vector_store()
    await vector_store.delete_paper_from_index(paper_id)

    return {
        "paper_id": paper_id,
        "message": "删除成功"
    }

@router.get("/{paper_id}/interpretation", summary="获取论文解读结果")
@handle_api_errors("获取解读结果失败")
async def get_paper_interpretation(paper_id: str):
    """
    获取指定论文的解读结果
    """
    with session_scope() as db:
        interpretation = db.query(PaperInterpretation).filter(
            PaperInterpretation.paper_id == paper_id
        ).first()

        if not interpretation:
            raise HTTPException(status_code=404, detail="论文尚未解读")

        return serialize_interpretation(interpretation)
