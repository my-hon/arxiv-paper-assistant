#!/usr/bin/env python3
"""
AI论文搜集解读复现系统主入口
"""

import sys
from pathlib import Path

# 确保模块路径正确
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from src.api.v1.api import api_router
from src.config.settings import settings
from src.core.init import initialize_system

# 日志配置
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
)

# 创建必要的目录
Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
Path(settings.PDF_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
Path(settings.SCRIPT_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
Path(settings.REPORT_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# 初始化FastAPI应用
app = FastAPI(
    title="AI论文搜集解读复现系统",
    description="支持论文爬取、结构化解读、实验复现、知识图谱构建的一站式学术研究平台",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/storage", StaticFiles(directory=settings.STORAGE_PATH), name="storage")

# 注册API路由
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    logger.info("系统启动中...")
    await initialize_system()
    logger.info("系统初始化完成")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "message": "系统运行正常"}


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "AI论文搜集解读复现系统",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "Documentation disabled",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1,
    )
