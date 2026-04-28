"""
数据库模型定义
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.sql import func
from datetime import datetime

from src.db.database import Base


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
    # 核心信息
    problem_domain = Column(String, comment="问题领域：论文解决的具体领域问题")
    core_contributions = Column(JSON, comment="核心贡献")
    innovations = Column(JSON, comment="创新点")
    limitations = Column(JSON, comment="局限性")
    conclusions = Column(JSON, comment="结论")

    # 方法实现
    technical_approach = Column(JSON, comment="技术方法：整体技术架构和思路")
    method_details = Column(JSON, comment="方法细节：具体的算法、模型、公式描述")
    implementation_notes = Column(JSON, comment="实现要点：代码实现的关键步骤和注意事项")
    code_links = Column(JSON, comment="代码链接：论文中提到的所有代码仓库、项目主页链接")

    # 数据集
    datasets = Column(JSON, comment="使用的数据集列表，包含数据集名称、来源、规模、特点")

    # 实验结果
    experimental_setup = Column(JSON, comment="实验设置：硬件环境、软件版本、训练参数等")
    evaluation_metrics = Column(JSON, comment="评价指标：使用的所有评价指标定义和计算方法")
    experimental_results = Column(JSON, comment="实验结果：各指标的具体数值、对比结果、显著性分析")
    baseline_comparison = Column(JSON, comment="基线对比：与现有方法的对比结果和优势分析")

    # 辅助信息
    references = Column(JSON, comment="关键参考文献")
    figure_descriptions = Column(JSON, comment="图表描述信息")
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
