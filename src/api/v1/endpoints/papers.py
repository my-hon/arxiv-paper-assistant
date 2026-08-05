"""
论文管理API接口
"""
from fastapi import APIRouter, Query
from loguru import logger
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.core.exceptions import NotFoundError, StorageError, VectorStoreError
from src.db.database import get_db
from src.db.models import Paper, PaperInterpretation
from src.modules.knowledge.vector_store import VectorStore

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
    db = next(get_db())
    try:
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
            "papers": [
                {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract,
                    "publication_date": paper.publication_date,
                    "source": paper.source,
                    "categories": paper.categories,
                    "citation_count": paper.citation_count,
                    "status": paper.status
                }
                for paper in papers
            ]
        }
    finally:
        db.close()

@router.get("/{paper_id}", response_model=PaperResponse, summary="获取论文详情")
async def get_paper_detail(paper_id: str):
    """
    获取指定论文的详细信息
    """
    db = next(get_db())
    try:
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()

        if not paper:
            raise NotFoundError(f"论文不存在: {paper_id}")

        return paper
    finally:
        db.close()

@router.delete("/{paper_id}", summary="删除论文")
async def delete_paper(paper_id: str):
    """
    删除指定论文及其相关数据

    数据库删除成功后，向量索引清理失败不会回滚删除，但会在响应中明确告知。
    """
    db = next(get_db())
    try:
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()

        if not paper:
            raise NotFoundError(f"论文不存在: {paper_id}")

        # 删除相关解读结果
        db.query(PaperInterpretation).filter(PaperInterpretation.paper_id == paper_id).delete()

        # 删除论文
        db.delete(paper)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception(f"删除论文失败 {paper_id}: {str(e)}")
            raise StorageError(f"删除论文失败: {str(e)}") from e
    finally:
        db.close()

    # 从向量索引中删除
    index_warning = None
    try:
        vector_store = VectorStore()
        await vector_store.initialize()
        await vector_store.delete_paper_from_index(paper_id)
    except VectorStoreError as e:
        index_warning = str(e)
        logger.warning(f"论文已删除但向量索引未清理 {paper_id}: {index_warning}")

    response = {
        "paper_id": paper_id,
        "message": "删除成功"
    }
    if index_warning:
        response["warning"] = f"向量索引清理失败: {index_warning}"
    return response

@router.get("/{paper_id}/interpretation", summary="获取论文解读结果")
async def get_paper_interpretation(paper_id: str):
    """
    获取指定论文的解读结果
    """
    db = next(get_db())
    try:
        interpretation = db.query(PaperInterpretation).filter(
            PaperInterpretation.paper_id == paper_id
        ).first()

        if not interpretation:
            raise NotFoundError(f"论文尚未解读: {paper_id}")

        return {
            "paper_id": interpretation.paper_id,
            "core_contributions": interpretation.core_contributions,
            "experimental_methods": interpretation.experimental_methods,
            "datasets": interpretation.datasets,
            "conclusions": interpretation.conclusions,
            "innovations": interpretation.innovations,
            "limitations": interpretation.limitations,
            "references": interpretation.references,
            "confidence_score": interpretation.confidence_score,
            "interpretation_time": interpretation.interpretation_time
        }
    finally:
        db.close()
