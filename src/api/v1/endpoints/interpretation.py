"""
论文解读API接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict

from src.modules.interpretation.paper_interpreter import PaperInterpreter
from src.db.database import get_db
from src.db.models import PaperInterpretation

router = APIRouter()

class InterpretationResponse(BaseModel):
    paper_id: str
    core_contributions: List[str]
    experimental_methods: List[str]
    datasets: List[str]
    conclusions: List[str]
    innovations: List[str]
    limitations: List[str]
    references: List[str]
    confidence_score: float
    interpretation_model: str
    interpretation_time: Optional[str]

@router.post("/{paper_id}", response_model=InterpretationResponse, summary="解读论文")
async def interpret_paper(
    paper_id: str,
    use_abstract_only: bool = Query(False, description="是否仅使用摘要解读")
):
    """
    对指定论文进行结构化解读
    """
    try:
        interpreter = PaperInterpreter()
        result = await interpreter.interpret_paper(paper_id, use_abstract_only)
        
        if not result:
            raise HTTPException(status_code=500, detail="论文解读失败")
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解读失败: {str(e)}")

@router.get("/{paper_id}", response_model=Optional[InterpretationResponse], summary="获取论文解读结果")
async def get_interpretation(paper_id: str):
    """
    获取已有的论文解读结果
    """
    try:
        db = next(get_db())
        interpretation = db.query(PaperInterpretation).filter(
            PaperInterpretation.paper_id == paper_id
        ).first()
        
        if not interpretation:
            return None
            
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
            "interpretation_model": interpretation.interpretation_model,
            "interpretation_time": interpretation.interpretation_time.isoformat() if interpretation.interpretation_time else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取解读结果失败: {str(e)}")

@router.post("/batch", summary="批量解读论文")
async def batch_interpret(
    paper_ids: List[str],
    use_abstract_only: bool = Query(False, description="是否仅使用摘要解读")
):
    """
    批量解读多篇论文
    """
    results = []
    failed = []
    
    for paper_id in paper_ids:
        try:
            interpreter = PaperInterpreter()
            result = await interpreter.interpret_paper(paper_id, use_abstract_only)
            if result:
                results.append(result)
            else:
                failed.append(paper_id)
        except Exception as e:
            failed.append(paper_id)
            continue
            
    return {
        "total": len(paper_ids),
        "success": len(results),
        "failed": len(failed),
        "failed_ids": failed,
        "results": results
    }
