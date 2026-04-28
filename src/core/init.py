"""系统初始化模块，负责启动时初始化所有核心组件。

包含数据库、向量存储、爬虫、论文解读、复现脚本生成等组件的初始化逻辑，
确保系统启动时所有依赖组件都能正常工作。
"""
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.db.models import Base
from src.db.database import engine
from src.modules.crawler.arxiv_client import ArxivClient as ArxivCrawler
from src.modules.interpretation.paper_interpreter import PaperInterpreter
from src.modules.reproduction.script_generator import ScriptGenerator
from src.modules.knowledge.vector_store import VectorStore

async def initialize_system():
    """异步初始化系统所有核心组件。

    按顺序初始化以下组件：
    1. 关系数据库，创建所有表结构
    2. 向量存储，用于语义搜索和相似论文推荐
    3. 爬虫组件，用于从arXiv等平台获取论文数据
    4. 论文解读组件，用于基于大模型提取论文核心信息
    5. 复现脚本生成组件，用于自动生成论文实验复现代码

    向量存储初始化失败时不会终止启动，仅禁用相关功能；
    其他组件初始化失败时会抛出异常，终止启动过程。

    Raises:
        Exception: 当数据库、爬虫、解读或复现组件初始化失败时抛出。
    """
    logger.info("开始初始化系统组件")
    
    # 初始化数据库
    try:
        logger.info("初始化数据库...")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise
    
    # 初始化向量存储
    try:
        logger.info("初始化向量存储...")
        vector_store = VectorStore()
        await vector_store.initialize()
        logger.info("向量存储初始化完成")
    except Exception as e:
        logger.warning(f"向量存储初始化失败: {str(e)}，知识库功能将不可用")
    
    # 初始化爬虫组件
    try:
        logger.info("初始化爬虫组件...")
        arxiv_crawler = ArxivCrawler()
        logger.info("爬虫组件初始化完成")
    except Exception as e:
        logger.error(f"爬虫组件初始化失败: {str(e)}")
        raise
    
    # 初始化论文解读组件
    try:
        logger.info("初始化论文解读组件...")
        interpreter = PaperInterpreter()
        logger.info("论文解读组件初始化完成")
    except Exception as e:
        logger.error(f"论文解读组件初始化失败: {str(e)}")
        raise
    
    # 初始化复现组件
    try:
        logger.info("初始化复现组件...")
        script_generator = ScriptGenerator()
        logger.info("复现组件初始化完成")
    except Exception as e:
        logger.error(f"复现组件初始化失败: {str(e)}")
        raise
    
    logger.info("所有系统组件初始化完成")
