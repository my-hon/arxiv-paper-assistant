"""
论文解读API接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from src.core.errors import handle_api_errors
from src.core.serializers import serialize_interpretation
from src.db.database import session_scope
from src.db.models import PaperInterpretation
from src.modules.interpretation.paper_interpreter import PaperInterpreter

router = APIRouter()

class InterpretationResponse(BaseModel):
    paper_id: str
    problem_domain: Optional[str] = None
    core_contributions: Optional[List[str]] = None
    innovations: Optional[List[str]] = None
    limitations: Optional[List[str]] = None
    conclusions: Optional[List[str]] = None
    technical_approach: Optional[str] = None
    method_details: Optional[List[Dict[str, Any]]] = None
    implementation_notes: Optional[List[str]] = None
    code_links: Optional[List[Dict[str, Any]]] = None
    datasets: Optional[List[Dict[str, Any]]] = None
    experimental_setup: Optional[List[str]] = None
    evaluation_metrics: Optional[List[Dict[str, Any]]] = None
    experimental_results: Optional[List[Dict[str, Any]]] = None
    baseline_comparison: Optional[List[str]] = None
    references: Optional[List[str]] = None
    figure_descriptions: Optional[List[Dict[str, Any]]] = None
    confidence_score: Optional[float] = None
    interpretation_model: Optional[str] = None
    interpretation_time: Optional[str] = None

@router.post("/{paper_id}", response_model=InterpretationResponse, summary="解读论文")
@handle_api_errors("解读失败")
async def interpret_paper(
    paper_id: str,
    use_abstract_only: bool = Query(False, description="是否仅使用摘要解读")
):
    """
    对指定论文进行结构化解读
    """
    interpreter = PaperInterpreter()
    result = await interpreter.interpret_paper(paper_id, use_abstract_only)

    if not result:
        raise HTTPException(status_code=500, detail="论文解读失败")

    return result

@router.get("/{paper_id}", response_model=Optional[InterpretationResponse], summary="获取论文解读结果")
@handle_api_errors("获取解读结果失败")
async def get_interpretation(paper_id: str):
    """
    获取已有的论文解读结果
    """
    with session_scope() as db:
        interpretation = db.query(PaperInterpretation).filter(
            PaperInterpretation.paper_id == paper_id
        ).first()

        if not interpretation:
            return None

        return serialize_interpretation(interpretation)

@router.post("/batch", summary="批量解读论文")
async def batch_interpret(
    paper_ids: List[str],
    use_abstract_only: bool = Query(False, description="是否仅使用摘要解读")
):
    """
    批量解读多篇论文
    """
    interpreter = PaperInterpreter()
    results = []
    failed = []

    for paper_id in paper_ids:
        try:
            result = await interpreter.interpret_paper(paper_id, use_abstract_only)
            if result:
                results.append(result)
            else:
                failed.append(paper_id)
        except Exception:
            failed.append(paper_id)

    return {
        "total": len(paper_ids),
        "success": len(results),
        "failed": len(failed),
        "failed_ids": failed,
        "results": results
    }
