"""单元测试的公共fixture，提供内存数据库和外部依赖的替身。"""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db.database import Base
from src.db.models import Paper, PaperInterpretation, ReproductionTask


@pytest.fixture
def db_session():
    """返回一个基于内存SQLite的数据库会话。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def patch_get_db(monkeypatch, db_session):
    """把指定模块中的get_db替换为返回测试会话的生成器。"""

    def _patch(module):
        def fake_get_db():
            yield db_session

        monkeypatch.setattr(module, "get_db", fake_get_db)
        return db_session

    return _patch


@pytest.fixture
def sample_paper(db_session):
    """写入一条论文记录并返回。"""
    paper = Paper(
        paper_id="arxiv_1706.03762",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        abstract="The dominant sequence transduction models...",
        arxiv_id="1706.03762",
        publication_date=datetime(2017, 6, 12),
        source="arxiv",
        categories=["cs.CL", "cs.LG"],
        url="http://arxiv.org/abs/1706.03762",
        pdf_url="http://arxiv.org/pdf/1706.03762",
        citation_count=100,
        status="new",
    )
    db_session.add(paper)
    db_session.commit()
    return paper


@pytest.fixture
def sample_interpretation(db_session, sample_paper):
    """写入一条论文解读记录并返回。"""
    interpretation = PaperInterpretation(
        paper_id=sample_paper.paper_id,
        problem_domain="序列建模",
        core_contributions=["提出Transformer"],
        innovations=["自注意力机制"],
        limitations=["计算开销大"],
        conclusions=["优于RNN"],
        technical_approach="纯注意力架构",
        method_details=[{"name": "Multi-Head Attention"}],
        implementation_notes=["注意mask"],
        code_links=[{"url": "https://github.com/example"}],
        datasets=[{"name": "WMT 2014"}],
        experimental_setup=["8 GPU"],
        evaluation_metrics=[{"name": "BLEU"}],
        experimental_results=[{"metric_name": "BLEU", "value": "28.4"}],
        baseline_comparison=["优于ConvS2S"],
        references=["Bahdanau et al."],
        figure_descriptions=[],
        interpretation_model="gpt-3.5-turbo-1106",
        confidence_score=0.9,
    )
    db_session.add(interpretation)
    db_session.commit()
    return interpretation


@pytest.fixture
def sample_task(db_session, sample_paper, tmp_path):
    """写入一条复现任务记录并返回。"""
    script_path = tmp_path / "task" / "reproduce.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("print('hello')", encoding="utf-8")

    task = ReproductionTask(
        task_id="task-1",
        paper_id=sample_paper.paper_id,
        status="pending",
        script_path=str(script_path),
    )
    db_session.add(task)
    db_session.commit()
    return task
