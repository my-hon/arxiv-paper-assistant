"""
复现验证API接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

from src.core.errors import handle_api_errors
from src.core.serializers import serialize_task_detail, serialize_task_summary
from src.db.database import session_scope
from src.db.models import ReproductionTask
from src.modules.reproduction.script_generator import ScriptGenerator

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
@handle_api_errors("生成脚本失败")
async def generate_reproduction_script(paper_id: str):
    """
    为指定论文生成复现脚本
    """
    generator = ScriptGenerator()
    result = await generator.generate_script(paper_id)

    if not result:
        raise HTTPException(status_code=500, detail="生成复现脚本失败")

    return result

@router.post("/run/{task_id}", response_model=RunReproductionResponse, summary="运行复现任务")
@handle_api_errors("运行任务失败")
async def run_reproduction_task(task_id: str):
    """
    运行指定的复现任务
    """
    generator = ScriptGenerator()
    result = await generator.run_reproduction(task_id)

    if not result:
        raise HTTPException(status_code=500, detail="运行复现任务失败")

    return result

@router.get("/task/{task_id}", summary="获取复现任务状态")
@handle_api_errors("获取任务状态失败")
async def get_reproduction_task(task_id: str):
    """
    获取复现任务的状态和结果
    """
    with session_scope() as db:
        task = db.query(ReproductionTask).filter(ReproductionTask.task_id == task_id).first()

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        return serialize_task_detail(task)

@router.get("/tasks", summary="获取复现任务列表")
@handle_api_errors("获取任务列表失败")
async def list_reproduction_tasks(
    status: Optional[str] = None,
    paper_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    获取复现任务列表
    """
    with session_scope() as db:
        query = db.query(ReproductionTask)

        if status:
            query = query.filter(ReproductionTask.status == status)
        if paper_id:
            query = query.filter(ReproductionTask.paper_id == paper_id)

        total = query.count()
        tasks = query.order_by(ReproductionTask.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "tasks": [serialize_task_summary(task) for task in tasks]
        }
