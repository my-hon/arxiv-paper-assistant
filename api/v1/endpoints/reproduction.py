"""
复现验证API接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List

from modules.reproduction.script_generator import ScriptGenerator
from db.database import get_db
from db.models import ReproductionTask

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
    try:
        generator = ScriptGenerator()
        result = await generator.generate_script(paper_id)
        
        if not result:
            raise HTTPException(status_code=500, detail="生成复现脚本失败")
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成脚本失败: {str(e)}")

@router.post("/run/{task_id}", response_model=RunReproductionResponse, summary="运行复现任务")
async def run_reproduction_task(task_id: str):
    """
    运行指定的复现任务
    """
    try:
        generator = ScriptGenerator()
        result = await generator.run_reproduction(task_id)
        
        if not result:
            raise HTTPException(status_code=500, detail="运行复现任务失败")
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"运行任务失败: {str(e)}")

@router.get("/task/{task_id}", summary="获取复现任务状态")
async def get_reproduction_task(task_id: str):
    """
    获取复现任务的状态和结果
    """
    try:
        db = next(get_db())
        task = db.query(ReproductionTask).filter(ReproductionTask.task_id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
            
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")

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
    try:
        db = next(get_db())
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")
