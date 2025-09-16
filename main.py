#!/usr/bin/env python3
"""
FastAPI wrapper for Docking Pipeline
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

# 添加当前目录到Python路径
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

from config.logging_config import setup_logging, get_log_file_path
from async_task_processor import AsyncTaskProcessor
from docking_task_processor import background_task_runner

# 设置日志系统
log_file = get_log_file_path()
setup_logging(level="INFO", log_file=log_file)
logger = logging.getLogger(__name__)

# 全局异步任务处理器
async_processor = None
# 后台任务
background_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # —— 应用启动时执行 —— 
    global async_processor, background_task
    
    logger.info("Starting Docking Vina API...")
    
    # 初始化异步任务处理器
    logger.info("Initializing async task processor...")
    async_processor = AsyncTaskProcessor()
    
    # 启动后台定时任务
    logger.info("Starting background task runner...")
    background_task = asyncio.create_task(background_task_runner())
    
    logger.info("Docking Vina API startup complete")
    yield
    
    # —— 应用关闭时执行 ——
    logger.info("Shutting down Docking Vina API...")
    
    # 取消后台任务
    if background_task:
        logger.info("Cancelling background task...")
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            logger.info("Background task cancelled successfully")
    
    # 关闭异步任务处理器
    if async_processor:
        await async_processor.shutdown()
    
    logger.info("Docking Vina API shutdown complete")

app = FastAPI(
    lifespan=lifespan,
    title="Docking Vina API", 
    description="Molecular docking service using AutoDock Vina with database task management.",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# 基本路由
@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "Docking Vina API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "active_tasks": async_processor.get_task_count() if async_processor else 0
    }

@app.get("/status")
async def status():
    """获取服务状态"""
    if not async_processor:
        return {"status": "initializing"}
    
    return {
        "status": "running",
        "active_tasks": async_processor.get_task_count(),
        "active_task_ids": async_processor.get_active_tasks()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=False)
