from dotenv import load_dotenv

load_dotenv()

import sys
import logging as standard_logging
import os
from pathlib import Path

hf_endpoint = os.getenv("HF_ENDPOINT")
if hf_endpoint:
    os.environ["HF_ENDPOINT"] = hf_endpoint

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api import router

# 初始化日志
setup_logging()


app = FastAPI(
    title="C++面试Agent",
    description="帮助校招应届生系统性掌握C++面试知识点",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS中间件
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 路由注册
app.include_router(router, prefix="/api/v1")


# 静态文件服务（如前端演示页面）
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup():
    """启动事件：初始化服务。"""
    logger.info("Starting C++ Interview Agent...")
    try:
        from app.services.retriever import get_retriever

        app.state.retriever = await get_retriever()
        logger.info("Retriever initialized")
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}")
        app.state.retriever = None

    logger.info(f"LLM Model: {settings.LLM_MODEL_NAME}")
    logger.info(f"Books dir: {settings.BOOK_DIR}")
    logger.info("Startup complete")


@app.on_event("shutdown")
async def shutdown():
    """关闭事件：清理资源。"""
    logger.info("Shutting down...")
    # 清理资源（如有）
    logger.info("Shutdown complete")


# 根路径重定向到前端演示页面（可选）
@app.get("/", include_in_schema=False)
async def root():
    from fastapi.responses import FileResponse

    demo = Path("static/demo.html")
    if demo.exists():
        return FileResponse(demo)
    return RedirectResponse(url="/docs")
