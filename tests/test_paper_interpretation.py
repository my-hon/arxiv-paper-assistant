#!/usr/bin/env python3
"""论文解读功能集成测试。

测试流程：
1. 搜索arXiv论文（机器学习领域近期论文）
2. 下载论文PDF文件
3. 调用论文解读接口
4. 验证数据库存储结果
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from loguru import logger

from modules.crawler.arxiv_client import ArxivClient
from modules.interpretation.paper_interpreter import PaperInterpreter
from db.database import get_db
from db.models import Paper, PaperInterpretation


@pytest.fixture(scope="module")
def arxiv_client():
    """创建ArxivClient实例"""
    return ArxivClient()


@pytest.fixture(scope="module")
def paper_interpreter():
    """创建PaperInterpreter实例"""
    return PaperInterpreter()


@pytest.fixture(scope="module")
def db_session():
    """创建数据库会话"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def test_search_paper(arxiv_client):
    """测试搜索arXiv论文"""
    logger.info("=== 测试论文搜索功能 ===")

    # 搜索机器学习领域近期论文
    papers = arxiv_client.search_and_save(
        query="machine learning",
        max_results=1,
        categories=["cs.LG"],
        download_pdfs=False
    )

    assert len(papers) > 0, "未搜索到论文"

    paper = papers[0]
    logger.info(f"搜索到论文: {paper['title']}")
    logger.info(f"论文ID: {paper['paper_id']}")
    logger.info(f"arXiv ID: {paper['arxiv_id']}")

    # 验证论文信息完整性
    assert "paper_id" in paper
    assert "title" in paper
    assert "authors" in paper
    assert "abstract" in paper
    assert "arxiv_id" in paper
    assert "pdf_url" in paper

    return paper


def test_download_pdf(arxiv_client, test_paper=None):
    """测试PDF下载功能"""
    logger.info("=== 测试PDF下载功能 ===")

    if test_paper is None:
        # 如果没有传入论文，搜索一篇
        papers = arxiv_client.search_and_save(
            query="machine learning",
            max_results=1,
            categories=["cs.LG"],
            download_pdfs=False
        )
        test_paper = papers[0]

    # 根据arXiv ID获取完整论文信息
    result = arxiv_client.search_by_id(test_paper["arxiv_id"])
    assert result is not None, "未找到论文信息"

    # 下载PDF
    pdf_path = arxiv_client.download_pdf(result)
    assert pdf_path is not None, "PDF下载失败"

    logger.info(f"PDF下载路径: {pdf_path}")
    assert os.path.exists(pdf_path), "PDF文件不存在"
    assert os.path.getsize(pdf_path) > 0, "PDF文件为空"

    logger.info(f"PDF文件大小: {os.path.getsize(pdf_path)} bytes")

    # 更新数据库中的PDF路径
    db = next(get_db())
    paper = db.query(Paper).filter(Paper.paper_id == test_paper["paper_id"]).first()
    if paper:
        paper.pdf_path = pdf_path
        paper.status = "downloaded"
        db.commit()

    return test_paper, pdf_path


def test_paper_interpretation(paper_interpreter, test_paper=None):
    """测试论文解读功能"""
    logger.info("=== 测试论文解读功能 ===")

    if test_paper is None:
        # 如果没有传入论文，先搜索并下载
        arxiv_client = ArxivClient()
        test_paper, _ = test_download_pdf(arxiv_client)

    paper_id = test_paper["paper_id"]
    logger.info(f"开始解读论文: {paper_id}")

    # 调用解读接口
    result = paper_interpreter.interpret_paper(paper_id)
    assert result is not None, "论文解读失败"

    logger.info(f"解读完成，置信度: {result.get('confidence_score', 0)}")

    # 验证解读结果完整性
    assert "core_contributions" in result
    assert "experimental_methods" in result
    assert "datasets" in result
    assert "conclusions" in result
    assert "innovations" in result
    assert "limitations" in result
    assert "confidence_score" in result

    # 验证字段类型
    assert isinstance(result["core_contributions"], list)
    assert isinstance(result["experimental_methods"], list)
    assert isinstance(result["datasets"], list)
    assert isinstance(result["conclusions"], list)
    assert isinstance(result["innovations"], list)
    assert isinstance(result["limitations"], list)
    assert isinstance(result["confidence_score"], float)

    logger.info("核心贡献:")
    for i, contrib in enumerate(result["core_contributions"][:3], 1):
        logger.info(f"  {i}. {contrib[:100]}...")

    return result


def test_database_storage(db_session, test_paper=None):
    """验证数据库存储结果"""
    logger.info("=== 验证数据库存储 ===")

    if test_paper is None:
        # 如果没有传入论文，从数据库获取最新的论文
        test_paper = db_session.query(Paper).order_by(Paper.id.desc()).first()
        assert test_paper is not None, "数据库中没有论文记录"

    paper_id = test_paper["paper_id"] if isinstance(test_paper, dict) else test_paper.paper_id

    # 查询论文记录
    paper = db_session.query(Paper).filter(Paper.paper_id == paper_id).first()
    assert paper is not None, "论文记录不存在"

    logger.info(f"论文记录存在: {paper.paper_id}")
    logger.info(f"论文状态: {paper.status}")
    logger.info(f"PDF路径: {paper.pdf_path}")

    # 验证PDF路径存在
    if paper.pdf_path:
        assert os.path.exists(paper.pdf_path), "数据库中记录的PDF路径不存在"

    # 查询解读记录
    interpretation = db_session.query(PaperInterpretation).filter(
        PaperInterpretation.paper_id == paper_id
    ).first()

    assert interpretation is not None, "论文解读记录不存在"
    logger.info(f"解读记录存在，ID: {interpretation.id}")
    logger.info(f"解读模型: {interpretation.interpretation_model}")
    logger.info(f"置信度: {interpretation.confidence_score}")
    logger.info(f"解读时间: {interpretation.interpretation_time}")

    # 验证解读内容完整性
    assert interpretation.core_contributions is not None
    assert interpretation.experimental_methods is not None
    assert interpretation.datasets is not None
    assert interpretation.conclusions is not None
    assert interpretation.innovations is not None
    assert interpretation.limitations is not None

    # 验证JSON字段正确解析
    assert isinstance(interpretation.core_contributions, list)
    assert isinstance(interpretation.experimental_methods, list)

    logger.info("数据库存储验证通过")


def test_full_workflow():
    """测试完整工作流程：搜索->下载->解读->存储"""
    logger.info("=" * 60)
    logger.info("测试完整论文处理工作流")
    logger.info("=" * 60)

    # 1. 搜索论文
    arxiv_client = ArxivClient()
    paper = test_search_paper(arxiv_client)

    # 2. 下载PDF
    paper, pdf_path = test_download_pdf(arxiv_client, paper)

    # 3. 解读论文
    interpreter = PaperInterpreter()
    interpretation = test_paper_interpretation(interpreter, paper)

    # 4. 验证数据库存储
    test_database_storage(None, paper)

    logger.info("=" * 60)
    logger.info("✅ 完整工作流测试通过！")
    logger.info(f"论文ID: {paper['paper_id']}")
    logger.info(f"PDF路径: {pdf_path}")
    logger.info(f"解读置信度: {interpretation['confidence_score']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    # 运行完整测试
    test_full_workflow()
