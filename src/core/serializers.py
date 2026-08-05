"""通用序列化与格式化工具。

集中放置各API接口和模块中重复出现的ORM对象转字典、日期/作者格式化等逻辑，
避免同一份序列化代码散落在多个文件中。
"""

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from src.db.models import Paper, PaperInterpretation, ReproductionTask

UNKNOWN_TEXT = "未知"


def iso_or_none(value: Optional[datetime]) -> Optional[str]:
    """将datetime转换为ISO格式字符串，值为空时返回None。"""
    return value.isoformat() if value else None


def format_date(value: Optional[datetime], default: str = UNKNOWN_TEXT) -> str:
    """将datetime格式化为``YYYY-MM-DD``，值为空时返回默认文案。"""
    return value.strftime("%Y-%m-%d") if value else default


def format_authors(authors: Optional[Iterable[str]]) -> str:
    """将作者列表拼接为逗号分隔的字符串。"""
    return ", ".join(authors) if authors else ""


def truncate_text(text: Optional[str], max_length: int = 200) -> str:
    """截断文本并追加省略号，长度未超限时原样返回。"""
    if not text:
        return ""
    return text[:max_length] + "..." if len(text) > max_length else text


def serialize_paper_summary(paper: Paper) -> Dict[str, Any]:
    """序列化论文列表项，仅保留概览字段。"""
    return {
        "paper_id": paper.paper_id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": truncate_text(paper.abstract),
        "publication_date": paper.publication_date,
        "source": paper.source,
        "categories": paper.categories,
        "citation_count": paper.citation_count,
        "status": paper.status,
    }


def serialize_interpretation(
    interpretation: PaperInterpretation,
) -> Dict[str, Any]:
    """序列化论文解读结果，字段与PaperInterpretation模型保持一致。"""
    return {
        "paper_id": interpretation.paper_id,
        # 核心信息
        "problem_domain": interpretation.problem_domain,
        "core_contributions": interpretation.core_contributions,
        "innovations": interpretation.innovations,
        "limitations": interpretation.limitations,
        "conclusions": interpretation.conclusions,
        # 方法实现
        "technical_approach": interpretation.technical_approach,
        "method_details": interpretation.method_details,
        "implementation_notes": interpretation.implementation_notes,
        "code_links": interpretation.code_links,
        # 数据集
        "datasets": interpretation.datasets,
        # 实验结果
        "experimental_setup": interpretation.experimental_setup,
        "evaluation_metrics": interpretation.evaluation_metrics,
        "experimental_results": interpretation.experimental_results,
        "baseline_comparison": interpretation.baseline_comparison,
        # 辅助信息
        "references": interpretation.references,
        "figure_descriptions": interpretation.figure_descriptions,
        "confidence_score": interpretation.confidence_score,
        "interpretation_model": interpretation.interpretation_model,
        "interpretation_time": iso_or_none(interpretation.interpretation_time),
    }


def serialize_task_summary(task: ReproductionTask) -> Dict[str, Any]:
    """序列化复现任务列表项。"""
    return {
        "task_id": task.task_id,
        "paper_id": task.paper_id,
        "status": task.status,
        "created_at": iso_or_none(task.created_at),
        "completed_at": iso_or_none(task.completed_at),
        "consistency_score": task.consistency_score,
    }


def serialize_task_detail(task: ReproductionTask) -> Dict[str, Any]:
    """序列化复现任务详情，在概览字段基础上补充执行信息。"""
    return {
        **serialize_task_summary(task),
        "started_at": iso_or_none(task.started_at),
        "report_path": task.report_path,
        "error_message": task.error_message,
    }


def bullet_list(items: Optional[Iterable[Any]]) -> str:
    """将条目渲染为Markdown无序列表。"""
    return "".join(f"- {item}\n" for item in items or [])


def model_dicts(models: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
    """将Pydantic模型列表转换为字典列表。"""
    return [model.dict() for model in models or []]
