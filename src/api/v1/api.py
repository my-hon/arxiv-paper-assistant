"""
API路由总入口
"""
from fastapi import APIRouter

from src.api.v1.endpoints import crawler
from src.api.v1.endpoints import interpretation
from src.api.v1.endpoints import reproduction
from src.api.v1.endpoints import knowledge
from src.api.v1.endpoints import papers

api_router = APIRouter()

api_router.include_router(crawler.router, prefix="/crawler", tags=["爬虫模块"])
api_router.include_router(interpretation.router, prefix="/interpretation", tags=["论文解读模块"])
api_router.include_router(reproduction.router, prefix="/reproduction", tags=["复现验证模块"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库模块"])
api_router.include_router(papers.router, prefix="/papers", tags=["论文管理"])
