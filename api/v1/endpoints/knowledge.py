"""
知识库API接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict

from modules.knowledge.vector_store import VectorStore

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
    try:
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.get("/similar/{paper_id}", response_model=SearchResponse, summary="获取相似论文")
async def get_similar_papers(
    paper_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回结果数量")
):
    """
    获取与指定论文相似的论文列表
    """
    try:
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取相似论文失败: {str(e)}")

@router.post("/index/{paper_id}", summary="将论文添加到索引")
async def add_paper_to_index(paper_id: str):
    """
    将指定论文添加到向量索引
    """
    try:
        vector_store = VectorStore()
        await vector_store.initialize()
        
        success = await vector_store.add_paper_to_index(paper_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="添加索引失败")
            
        return {
            "paper_id": paper_id,
            "message": "添加成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加索引失败: {str(e)}")

@router.delete("/index/{paper_id}", summary="从索引中删除论文")
async def delete_paper_from_index(paper_id: str):
    """
    从向量索引中删除指定论文
    """
    try:
        vector_store = VectorStore()
        await vector_store.initialize()
        
        success = await vector_store.delete_paper_from_index(paper_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="删除索引失败")
            
        return {
            "paper_id": paper_id,
            "message": "删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除索引失败: {str(e)}")

@router.get("/stats", summary="获取知识库统计信息")
async def get_knowledge_stats():
    """
    获取知识库的统计信息
    """
    try:
        vector_store = VectorStore()
        await vector_store.initialize()
        
        stats = vector_store.get_index_stats()
        
        from db.database import get_db
        from db.models import Paper, PaperInterpretation, ReproductionTask
        
        db = next(get_db())
        
        total_papers = db.query(Paper).count()
        interpreted_papers = db.query(Paper).filter(Paper.status == "interpreted").count()
        reproduced_papers = db.query(ReproductionTask).filter(ReproductionTask.status == "success").count()
        
        return {
            "indexed_papers": stats["count"],
            "total_papers": total_papers,
            "interpreted_papers": interpreted_papers,
            "reproduced_papers": reproduced_papers
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
