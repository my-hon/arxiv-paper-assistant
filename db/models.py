"""
数据库模型定义
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.sql import func
from datetime import datetime

from db.database import Base


class Paper(Base):
    """论文表"""

    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(String, unique=True, index=True, comment="论文唯一ID")
    title = Column(String, index=True, comment="论文标题")
    authors = Column(JSON, comment="作者列表")
    abstract = Column(Text, comment="摘要")
    doi = Column(String, index=True, comment="DOI")
    arxiv_id = Column(String, index=True, comment="arXiv ID")
    publication_date = Column(DateTime, comment="发表日期")
    updated_date = Column(DateTime, comment="更新日期")
    source = Column(String, comment="来源平台：arxiv/semantic_scholar等")
    categories = Column(JSON, comment="分类标签")
    keywords = Column(JSON, comment="关键词")
    url = Column(String, comment="论文链接")
    pdf_url = Column(String, comment="PDF下载链接")
    pdf_path = Column(String, comment="本地PDF存储路径")
    citation_count = Column(Integer, default=0, comment="引用次数")
    reference_count = Column(Integer, default=0, comment="参考文献数量")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(
        String, default="new", comment="状态：new/downloaded/interpreted/reproduced"
    )


class PaperInterpretation(Base):
    """论文解读结果表"""

    __tablename__ = "paper_interpretations"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(String, index=True, comment="关联论文ID")
    core_contributions = Column(JSON, comment="核心贡献")
    experimental_methods = Column(JSON, comment="实验方法")
    datasets = Column(JSON, comment="使用的数据集")
    conclusions = Column(JSON, comment="结论")
    innovations = Column(JSON, comment="创新点")
    limitations = Column(JSON, comment="局限性")
    references = Column(JSON, comment="关键参考文献")
    interpretation_model = Column(String, comment="使用的大模型")
    interpretation_time = Column(DateTime, default=datetime.utcnow)
    confidence_score = Column(Float, comment="解读置信度")
    raw_response = Column(Text, comment="大模型原始响应")


class ReproductionTask(Base):
    """复现任务表"""

    __tablename__ = "reproduction_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, comment="任务ID")
    paper_id = Column(String, index=True, comment="关联论文ID")
    status = Column(
        String, default="pending", comment="任务状态：pending/running/success/failed"
    )
    script_path = Column(String, comment="生成的脚本路径")
    dockerfile_path = Column(String, comment="Dockerfile路径")
    requirements_path = Column(String, comment="依赖文件路径")
    execution_log = Column(Text, comment="执行日志")
    result = Column(JSON, comment="复现结果")
    consistency_score = Column(Float, comment="结果一致性得分")
    report_path = Column(String, comment="复现报告路径")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime, comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    error_message = Column(Text, comment="错误信息")


class KnowledgeGraph(Base):
    """知识图谱表"""

    __tablename__ = "knowledge_graph"

    id = Column(Integer, primary_key=True, index=True)
    node_type = Column(
        String, index=True, comment="节点类型：paper/author/institution/dataset/method"
    )
    node_id = Column(String, unique=True, index=True, comment="节点唯一ID")
    properties = Column(JSON, comment="节点属性")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class GraphRelation(Base):
    """图谱关系表"""

    __tablename__ = "graph_relations"

    id = Column(Integer, primary_key=True, index=True)
    source_node_id = Column(String, index=True, comment="源节点ID")
    target_node_id = Column(String, index=True, comment="目标节点ID")
    relation_type = Column(
        String,
        index=True,
        comment="关系类型：cites/author_of/affiliated_with/uses_method/uses_dataset",
    )
    properties = Column(JSON, comment="关系属性")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
