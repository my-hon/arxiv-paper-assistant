"""
复现验证API接口
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict

from src.core.exceptions import NotFoundError
from src.modules.reproduction.script_generator import ScriptGenerator
from src.db.database import get_db
from src.db.models import ReproductionTask

router = APIRouter()

class GenerateScriptResponse(BaseModel):
    task_id: str
    paper_id: str
    script_path: str
    requirements_path: Optional[str]
    dockerfile_path: Optional[str]

class RunReproductionResponse(BaseModel):
    task_id: str
    status: str
    exit_code: Optional[int]
    logs: Optional[str]
    result: Optional[Dict]
    error_message: Optional[str]

@router.post("/generate/{paper_id}", response_model=GenerateScriptResponse, summary="生成复现脚本")
async def generate_reproduction_script(paper_id: str):
    """
    为指定论文生成复现脚本
    """
    generator = ScriptGenerator()
    return await generator.generate_script(paper_id)

@router.post("/run/{task_id}", response_model=RunReproductionResponse, summary="运行复现任务")
async def run_reproduction_task(task_id: str):
    """
    运行指定的复现任务
    """
    generator = ScriptGenerator()
    return await generator.run_reproduction(task_id)

@router.get("/task/{task_id}", summary="获取复现任务状态")
async def get_reproduction_task(task_id: str):
    """
    获取复现任务的状态和结果
    """
    db = next(get_db())
    try:
        task = db.query(ReproductionTask).filter(ReproductionTask.task_id == task_id).first()

        if not task:
            raise NotFoundError(f"复现任务不存在: {task_id}")

        return {
            "task_id": task.task_id,
            "paper_id": task.paper_id,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "consistency_score": task.consistency_score,
            "report_path": task.report_path,
            "error_message": task.error_message
        }
    finally:
        db.close()

@router.get("/tasks", summary="获取复现任务列表")
async def list_reproduction_tasks(
    status: Optional[str] = None,
    paper_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    获取复现任务列表
    """
    db = next(get_db())
    try:
        query = db.query(ReproductionTask)

        if status:
            query = query.filter(ReproductionTask.status == status)
        if paper_id:
            query = query.filter(ReproductionTask.paper_id == paper_id)

        total = query.count()
        tasks = query.order_by(ReproductionTask.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "paper_id": task.paper_id,
                    "status": task.status,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "consistency_score": task.consistency_score
                }
                for task in tasks
            ]
        }
    finally:
        db.close()
