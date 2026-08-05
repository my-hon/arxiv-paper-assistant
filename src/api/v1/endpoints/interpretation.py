"""
论文解读API接口
"""
from fastapi import APIRouter, Query
from loguru import logger
from pydantic import BaseModel
from typing import Optional, List

from src.core.exceptions import AppError, NotFoundError
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
    interpreter = PaperInterpreter()
    return await interpreter.interpret_paper(paper_id, use_abstract_only)

@router.get("/{paper_id}", response_model=InterpretationResponse, summary="获取论文解读结果")
async def get_interpretation(paper_id: str):
    """
    获取已有的论文解读结果
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
            "interpretation_model": interpretation.interpretation_model,
            "interpretation_time": interpretation.interpretation_time.isoformat() if interpretation.interpretation_time else None
        }
    finally:
        db.close()

@router.post("/batch", summary="批量解读论文")
async def batch_interpret(
    paper_ids: List[str],
    use_abstract_only: bool = Query(False, description="是否仅使用摘要解读")
):
    """
    批量解读多篇论文

    单篇失败不会中断整体流程，失败原因会随响应一并返回。
    """
    results = []
    failed = []

    interpreter = PaperInterpreter()
    for paper_id in paper_ids:
        try:
            results.append(await interpreter.interpret_paper(paper_id, use_abstract_only))
        except AppError as e:
            logger.warning(f"批量解读失败 {paper_id}: {e.message}")
            failed.append({"paper_id": paper_id, "error": e.message})
        except Exception as e:
            logger.exception(f"批量解读发生未预期错误 {paper_id}: {str(e)}")
            failed.append({"paper_id": paper_id, "error": str(e)})

    return {
        "total": len(paper_ids),
        "success": len(results),
        "failed": len(failed),
        "failed_papers": failed,
        "results": results
    }
