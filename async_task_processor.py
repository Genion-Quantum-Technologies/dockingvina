"""
分子对接异步任务处理器
支持并发处理和进度更新
"""

import asyncio
import logging
import json
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from database.db import get_db_connection
from Vina.vina_workflow import vina_docking_from_list

logger = logging.getLogger("async_task_processor")


class TaskProgressCallback:
    """任务进度回调类"""
    
    def __init__(self, task_id: str, connection):
        self.task_id = task_id
        self.connection = connection
        self._is_completed = False
        
    async def update_progress(self, progress: float, info: str = None):
        """更新任务进度"""
        if self._is_completed:
            logger.debug("Task %s already completed, skipping progress update", self.task_id)
            return
            
        try:
            # 更新数据库中的任务状态
            async with self.connection.cursor() as cursor:
                await cursor.execute(
                    "UPDATE tasks SET status = %s, progress = %s, info = %s WHERE id = %s",
                    ("processing", progress, info or "", self.task_id)
                )
                await self.connection.commit()
                
            logger.debug("Task %s progress updated: %.1f%% - %s", 
                        self.task_id, progress, info or "")
        except Exception as e:
            logger.error("Failed to update progress for task %s: %s", self.task_id, e)
    
    def mark_completed(self):
        """标记任务为已完成"""
        self._is_completed = True


class AsyncTaskProcessor:
    """异步任务处理器"""
    
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.thread_executor = ThreadPoolExecutor(max_workers=max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=max_workers)
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = True
        self.current_dir = Path(__file__).parent.absolute()
        
        logger.info("AsyncTaskProcessor initialized with %d workers", max_workers)
    
    async def process_docking_task(self, task_id: str, job_dir: str):
        """处理分子对接任务"""
        connection = None
        try:
            # 获取数据库连接
            connection = await get_db_connection()
            if not connection:
                raise Exception("Failed to connect to database")
            
            # 创建进度回调
            progress_callback = TaskProgressCallback(task_id, connection)
            
            # 更新任务状态为处理中
            await progress_callback.update_progress(0, "Starting docking process")
            
            # 保存当前工作目录
            original_cwd = os.getcwd()
            
            try:
                # 切换到dockingvina目录
                os.chdir(self.current_dir)
                
                # 读取任务配置文件
                job_path = Path(job_dir)
                input_dir = job_path / "input"
                config_file = input_dir / "input.json"
                
                if not config_file.exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_file}")
                
                # 验证输入文件
                await progress_callback.update_progress(10, "Validating input files")
                
                # 解析配置文件
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                logger.info(f"Task configuration: {config}")
                
                # 检查必要的配置项
                required_keys = ['receptor_path', 'ligand_smiles_list', 'output_dir']
                for key in required_keys:
                    if key not in config:
                        raise ValueError(f"Missing required configuration: {key}")
                
                # 设置输出目录
                output_dir = job_path / "output"
                output_dir.mkdir(exist_ok=True)
                config['output_dir'] = str(output_dir)
                
                # 执行对接任务
                await progress_callback.update_progress(30, "Running molecular docking")
                
                # 在线程池中执行对接任务
                result = await asyncio.get_event_loop().run_in_executor(
                    self.thread_executor,
                    self._run_docking_sync,
                    config,
                    progress_callback
                )
                
                await progress_callback.update_progress(90, "Finalizing results")
                
                # 更新数据库为完成状态 - 使用NOW()确保时区一致
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        """UPDATE tasks 
                           SET status = %s, progress = %s, info = %s, result = %s, finished_at = NOW()
                           WHERE id = %s""",
                        ("finished", 100, "Docking completed successfully", 
                         json.dumps(result) if result else None, task_id)
                    )
                    await connection.commit()
                
                progress_callback.mark_completed()
                logger.info("Task %s completed successfully", task_id)
                
            finally:
                # 恢复原始工作目录
                os.chdir(original_cwd)
                
        except Exception as e:
            logger.error("Task %s failed: %s", task_id, str(e))
            
            if connection:
                try:
                    async with connection.cursor() as cursor:
                        await cursor.execute(
                            "UPDATE tasks SET status = %s, info = %s, finished_at = NOW() WHERE id = %s",
                            ("failed", str(e), task_id)
                        )
                        await connection.commit()
                except Exception as db_error:
                    logger.error("Failed to update task status in database: %s", db_error)
        
        finally:
            if connection:
                connection.close()
            
            # 从活动任务中移除
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def _run_docking_sync(self, config: dict, progress_callback: TaskProgressCallback):
        """同步执行对接任务"""
        try:
            logger.info("Starting vina docking process...")
            
            # 准备对接参数
            receptor_path = config['receptor_path']
            ligand_smiles_list = config['ligand_smiles_list']
            output_dir = config['output_dir']
            
            # 可选参数
            center = config.get('center', None)
            size = config.get('size', None)
            exhaustiveness = config.get('exhaustiveness', 8)
            num_modes = config.get('num_modes', 9)
            
            # 执行对接
            result = vina_docking_from_list(
                receptor_path=receptor_path,
                ligand_smiles_list=ligand_smiles_list,
                output_dir=output_dir,
                center=center,
                size=size,
                exhaustiveness=exhaustiveness,
                num_modes=num_modes
            )
            
            logger.info("Docking process completed")
            return result
            
        except Exception as e:
            logger.error("Docking process failed: %s", str(e))
            raise
    
    async def submit_task(self, task_id: str, job_dir: str) -> bool:
        """提交新任务"""
        if not self.is_running:
            logger.warning("TaskProcessor is not running, cannot submit task %s", task_id)
            return False
        
        if task_id in self.active_tasks:
            logger.warning("Task %s is already running", task_id)
            return False
        
        try:
            # 创建并启动任务
            task = asyncio.create_task(
                self.process_docking_task(task_id, job_dir)
            )
            self.active_tasks[task_id] = task
            
            logger.info("Task %s submitted successfully", task_id)
            return True
            
        except Exception as e:
            logger.error("Failed to submit task %s: %s", task_id, e)
            return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.active_tasks:
            logger.warning("Task %s not found in active tasks", task_id)
            return False
        
        try:
            task = self.active_tasks[task_id]
            task.cancel()
            
            # 等待任务真正取消
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # 更新数据库状态
            connection = await get_db_connection()
            if connection:
                try:
                    async with connection.cursor() as cursor:
                        await cursor.execute(
                            "UPDATE tasks SET status = %s, info = %s, finished_at = NOW() WHERE id = %s",
                            ("cancelled", "Task cancelled by user", task_id)
                        )
                        await connection.commit()
                finally:
                    connection.close()
            
            del self.active_tasks[task_id]
            logger.info("Task %s cancelled successfully", task_id)
            return True
            
        except Exception as e:
            logger.error("Failed to cancel task %s: %s", task_id, e)
            return False
    
    def get_active_tasks(self) -> list:
        """获取活动任务列表"""
        return list(self.active_tasks.keys())
    
    def get_task_count(self) -> int:
        """获取活动任务数量"""
        return len(self.active_tasks)
    
    async def shutdown(self):
        """关闭任务处理器"""
        logger.info("Shutting down AsyncTaskProcessor...")
        self.is_running = False
        
        # 取消所有活动任务
        for task_id, task in self.active_tasks.items():
            logger.info("Cancelling task: %s", task_id)
            task.cancel()
        
        # 等待所有任务完成或被取消
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        
        # 关闭执行器
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        
        logger.info("AsyncTaskProcessor shutdown complete")
