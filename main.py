#!/usr/bin/env python3
"""
FastAPI wrapper for Docking Pipeline
仿照peptide_opt的设计，从数据库获取任务参数并执行docking计算
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

# 添加当前目录到Python路径
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

from docking_task_processor import DockingTaskProcessor, background_task_runner

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量用于控制定时任务
background_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global background_task
    
    # 启动时执行
    logger.info("启动DockingVinaApp FastAPI应用...")
    background_task = asyncio.create_task(background_task_runner())
    
    yield
    
    # 关闭时执行
    logger.info("关闭DockingVinaApp FastAPI应用...")
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            logger.info("Docking定时任务已停止")

app = FastAPI(
    title="Docking Vina API",
    description="API for molecular docking using AutoDock Vina, with database task management",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Docking Vina API", 
        "status": "running",
        "description": "Molecular docking service with database task management"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "docking-vina-app"}

@app.post("/trigger-task-check")
async def trigger_task_check():
    """手动触发任务检查（用于测试）"""
    try:
        processor = DockingTaskProcessor()
        await processor.query_and_process_tasks()
        return {"message": "任务检查已触发", "status": "success"}
    except Exception as e:
        logger.error(f"手动触发任务检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"任务检查失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=False)
