"""
Async Task Processor

Handles concurrent processing of docking tasks with progress tracking.
"""

import asyncio
import json
import logging
import os
import shutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Optional

from dockingvina.database.db import get_db_connection
from dockingvina.core.vina_workflow import vina_docking_from_list
from dockingvina.services.storage import get_storage
from dockingvina.config import storage as storage_config

logger = logging.getLogger(__name__)


class TaskProgressCallback:
    """Task progress callback handler."""
    
    def __init__(self, task_id: str, connection):
        self.task_id = task_id
        self.connection = connection
        self._is_completed = False
        
    async def update_progress(self, progress: float, info: Optional[str] = None) -> None:
        """Update task progress in database."""
        if self._is_completed:
            logger.debug("Task %s already completed, skipping progress update", self.task_id)
            return
            
        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(
                    "UPDATE tasks SET status = %s, progress = %s, info = %s WHERE id = %s",
                    ("processing", progress, info or "", self.task_id)
                )
                await self.connection.commit()
                
            logger.debug(
                "Task %s progress updated: %.1f%% - %s",
                self.task_id, progress, info or ""
            )
        except Exception as e:
            logger.error("Failed to update progress for task %s: %s", self.task_id, e)
    
    def mark_completed(self) -> None:
        """Mark task as completed."""
        self._is_completed = True


class AsyncTaskProcessor:
    """Async task processor with concurrent execution support."""
    
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.thread_executor = ThreadPoolExecutor(max_workers=max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=max_workers)
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = True
        self.current_dir = Path(__file__).parent.absolute()
        
        logger.info("AsyncTaskProcessor initialized with %d workers", max_workers)
    
    async def process_docking_task(self, task_id: str, job_dir: str) -> None:
        """
        Process a docking task with SeaweedFS storage.
        
        Args:
            task_id: Task identifier
            job_dir: Job directory path prefix
        """
        connection = None
        temp_job_dir = None
        
        try:
            connection = await get_db_connection()
            if not connection:
                raise Exception("Failed to connect to database")
            
            progress_callback = TaskProgressCallback(task_id, connection)
            await progress_callback.update_progress(0, "Starting docking process")
            
            original_cwd = os.getcwd()
            storage = get_storage()
            
            # Create temporary directory
            storage_config.ensure_temp_dir()
            temp_job_dir = storage_config.temp_dir / task_id
            temp_job_dir.mkdir(parents=True, exist_ok=True)
            temp_input_dir = temp_job_dir / "input"
            temp_input_dir.mkdir(exist_ok=True)
            
            try:
                os.chdir(self.current_dir)
                
                # Download input files from SeaweedFS
                await progress_callback.update_progress(5, "Downloading input files from storage")
                
                remote_config_key = f"jobs/docking/{task_id}/input/input.json"
                local_config_file = temp_input_dir / "input.json"
                
                await storage.download_file(remote_config_key, local_config_file)
                
                await progress_callback.update_progress(10, "Validating input files")
                
                with open(local_config_file, 'r') as f:
                    config = json.load(f)
                
                logger.info(f"Task configuration: {config}")
                
                # Validate required configuration
                required_keys = ['receptor_path', 'ligand_smiles_list', 'output_dir']
                for key in required_keys:
                    if key not in config:
                        raise ValueError(f"Missing required configuration: {key}")
                
                # Download receptor file
                receptor_storage_key = config.get('receptor_storage_key')
                receptor_local = temp_input_dir / "receptor.pdbqt"
                
                if receptor_storage_key:
                    await storage.download_file(receptor_storage_key, receptor_local)
                    logger.info(f"Downloaded receptor from: {receptor_storage_key}")
                else:
                    receptor_key = f"jobs/docking/{task_id}/input/receptor.pdbqt"
                    await storage.download_file(receptor_key, receptor_local)
                    logger.info(f"Downloaded receptor from: {receptor_key}")
                
                config['receptor_path'] = str(receptor_local)
                
                # Setup output directory
                output_dir = temp_job_dir / "output"
                output_dir.mkdir(exist_ok=True)
                config['output_dir'] = str(output_dir)
                
                # Execute docking task
                await progress_callback.update_progress(30, "Running molecular docking")
                
                result = await asyncio.get_event_loop().run_in_executor(
                    self.thread_executor,
                    self._run_docking_sync,
                    config,
                    progress_callback
                )
                
                await progress_callback.update_progress(80, "Uploading results to storage")
                
                # Upload results to SeaweedFS
                for result_file in output_dir.rglob("*"):
                    if result_file.is_file():
                        relative_path = result_file.relative_to(output_dir)
                        remote_key = f"jobs/docking/{task_id}/output/{relative_path}"
                        await storage.upload_file(result_file, remote_key)
                        logger.info(f"Uploaded result: {remote_key}")
                
                await progress_callback.update_progress(90, "Finalizing results")
                
                # Update database status
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
            
            if temp_job_dir and temp_job_dir.exists():
                try:
                    shutil.rmtree(temp_job_dir, ignore_errors=True)
                    logger.info(f"Cleaned up temp directory: {temp_job_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory: {e}")
            
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def _run_docking_sync(self, config: dict, progress_callback: TaskProgressCallback):
        """Execute docking task synchronously."""
        try:
            logger.info("Starting vina docking process...")
            
            receptor_path = config['receptor_path']
            ligand_smiles_list = config['ligand_smiles_list']
            output_dir = config['output_dir']
            
            # Optional parameters
            center = config.get('center', None)
            size = config.get('size', None)
            exhaustiveness = config.get('exhaustiveness', 8)
            num_modes = config.get('num_modes', 9)
            
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
        """Submit a new task for processing."""
        if not self.is_running:
            logger.warning("TaskProcessor is not running, cannot submit task %s", task_id)
            return False
        
        if task_id in self.active_tasks:
            logger.warning("Task %s is already running", task_id)
            return False
        
        try:
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
        """Cancel a running task."""
        if task_id not in self.active_tasks:
            logger.warning("Task %s not found in active tasks", task_id)
            return False
        
        try:
            task = self.active_tasks[task_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
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
        """Get list of active task IDs."""
        return list(self.active_tasks.keys())
    
    def get_task_count(self) -> int:
        """Get count of active tasks."""
        return len(self.active_tasks)
    
    async def shutdown(self) -> None:
        """Shutdown the task processor gracefully."""
        logger.info("Shutting down AsyncTaskProcessor...")
        self.is_running = False
        
        for task_id, task in self.active_tasks.items():
            logger.info("Cancelling task: %s", task_id)
            task.cancel()
        
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        
        logger.info("AsyncTaskProcessor shutdown complete")
