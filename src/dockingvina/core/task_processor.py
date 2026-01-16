"""
Docking Task Processor

Processes docking tasks from the database with SeaweedFS storage support.
"""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from dockingvina.database.db import DatabaseManager, get_db_connection
from dockingvina.core.vina_workflow import vina_docking_from_list
from dockingvina.services.storage import get_storage
from dockingvina.config import storage as storage_config

logger = logging.getLogger(__name__)


class DockingTaskProcessor:
    """Docking task processor with SeaweedFS storage support."""
    
    def __init__(self):
        self.current_dir = Path(__file__).parent.absolute()
        self.storage = get_storage()
        
    async def process_docking_task(self, task_id: str, job_dir: str, connection) -> None:
        """
        Process a single docking task.
        
        Args:
            task_id: Task identifier
            job_dir: Job directory path (SeaweedFS path prefix)
            connection: Database connection
        """
        original_cwd = os.getcwd()
        temp_job_dir = None
        
        try:
            logger.info(f"Starting docking task: {task_id}")
            
            storage_prefix = job_dir
            job_id = Path(job_dir).name
            logger.info(f"Processing task, storage prefix: {storage_prefix}, job_id: {job_id}")
            
            # Create temporary directory
            storage_config.ensure_temp_dir()
            temp_job_dir = storage_config.temp_dir / task_id
            temp_job_dir.mkdir(parents=True, exist_ok=True)
            temp_input_dir = temp_job_dir / "input"
            temp_input_dir.mkdir(exist_ok=True)
            
            # Download input configuration from SeaweedFS
            remote_config_key = f"{storage_prefix}/input/input.json"
            config_file = temp_input_dir / "input.json"
            
            await self.storage.download_file(remote_config_key, config_file)
            logger.info(f"Downloaded config from SeaweedFS: {remote_config_key}")
            
            # Parse configuration
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            logger.info(f"Task configuration: {config}")
            
            # Validate required configuration
            if 'ligands' not in config or not config['ligands']:
                raise ValueError("Missing ligands in configuration")
            
            if 'receptor_pdbqt' not in config:
                raise ValueError("Missing receptor_pdbqt in configuration")
            
            # Download receptor file from SeaweedFS
            receptor_storage_key = config.get('receptor_storage_key')
            receptor_path = temp_input_dir / "receptor.pdbqt"
            
            if receptor_storage_key:
                await self.storage.download_file(receptor_storage_key, receptor_path)
                logger.info(f"Downloaded receptor from SeaweedFS: {receptor_storage_key}")
            else:
                receptor_key = f"{storage_prefix}/input/receptor.pdbqt"
                await self.storage.download_file(receptor_key, receptor_path)
                logger.info(f"Downloaded receptor from SeaweedFS: {receptor_key}")
            
            # Setup output directory
            output_dir = temp_job_dir / "output"
            output_dir.mkdir(exist_ok=True)
            
            # Generate temporary SMILES file
            smiles_file = temp_input_dir / "ligands.csv"
            await self._create_smiles_file(config['ligands'], smiles_file)
            
            # Generate vina box configuration file
            vina_box_file = temp_input_dir / "vina_box.json"
            await self._create_vina_box_file(config, vina_box_file)
            
            # Update task status to running
            await DatabaseManager.update_task_status(connection, task_id, 'running')
            
            logger.info(f"Task {task_id} starting docking process")
            
            # Prepare docking parameters
            docking_params = {
                'smiles_file': str(smiles_file),
                'protein_file': str(receptor_path),
                'vina_box_file': str(vina_box_file),
                'output_dir': str(output_dir),
                'n_poses': config.get('n_poses', 10),
                'energy_range': config.get('energy_range', 3),
                'exhaustiveness': config.get('exhaustiveness', 8),
                'num_cpu': config.get('n_jobs', 1),
                'seed': config.get('seed', 0),
                'min_ph': config.get('min_ph', 6.0),
                'max_ph': config.get('max_ph', 8.0)
            }
            
            # Run docking calculation
            await self._run_docking_calculation(docking_params, task_id)
            
            # Upload results to SeaweedFS
            logger.info("Uploading task results to SeaweedFS...")
            for result_file in output_dir.rglob("*"):
                if result_file.is_file():
                    relative_path = result_file.relative_to(output_dir)
                    remote_key = f"{storage_prefix}/output/{relative_path}"
                    await self.storage.upload_file(result_file, remote_key)
                    logger.info(f"Uploaded: {remote_key}")
            
            # Update task status to finished
            await DatabaseManager.update_task_status(connection, task_id, 'finished')
            
            logger.info(f"Task {task_id} completed")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            try:
                await DatabaseManager.update_task_status(connection, task_id, 'failed')
            except Exception as db_error:
                logger.error(f"Failed to update task status: {db_error}")
            raise
        finally:
            os.chdir(original_cwd)
            
            if temp_job_dir and temp_job_dir.exists():
                try:
                    shutil.rmtree(temp_job_dir, ignore_errors=True)
                    logger.info(f"Cleaned up temporary directory: {temp_job_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory: {e}")
    
    async def _create_smiles_file(self, ligands: List[Dict], output_file: Path) -> None:
        """Create SMILES CSV file from ligands list."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("SMILES,Title\n")
                for ligand in ligands:
                    smiles = ligand.get('smiles', '')
                    title = ligand.get('title', '')
                    f.write(f"{smiles},{title}\n")
            logger.info(f"SMILES file created: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create SMILES file: {e}")
            raise
    
    async def _create_vina_box_file(self, config: Dict, output_file: Path) -> None:
        """Create vina box JSON file from configuration."""
        try:
            vina_box = {
                "center": [
                    config.get('center_x', 0.0),
                    config.get('center_y', 0.0),
                    config.get('center_z', 0.0)
                ],
                "box_size": [
                    config.get('box_size_x', 20.0),
                    config.get('box_size_y', 20.0),
                    config.get('box_size_z', 20.0)
                ],
                "exhaustiveness": config.get('exhaustiveness', 8),
                "n_poses": config.get('n_poses', 10)
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(vina_box, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Vina box file created: {output_file}")
        except Exception as e:
            logger.error(f"Failed to create vina box file: {e}")
            raise
    
    async def _run_docking_calculation(self, params: Dict[str, Any], task_id: str) -> str:
        """Run docking calculation."""
        try:
            # Read SMILES file
            smiles_list = []
            with open(params['smiles_file'], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[1:]:  # Skip header
                    line = line.strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            smiles_list.append({
                                'smiles': parts[0].strip(),
                                'title': parts[1].strip()
                            })
            
            if not smiles_list:
                raise ValueError("No valid molecules in SMILES file")
            
            logger.info(f"Starting docking calculation for {len(smiles_list)} molecules")
            
            # Read vina box configuration
            with open(params['vina_box_file'], 'r', encoding='utf-8') as f:
                vina_box_config = json.load(f)
            
            # Run docking in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_vina_docking_sync,
                smiles_list,
                params['protein_file'],
                vina_box_config,
                params['output_dir'],
                params
            )
            
            logger.info(f"Docking calculation complete, results saved to: {params['output_dir']}")
            return result
            
        except Exception as e:
            logger.error(f"Docking calculation failed: {e}")
            raise
    
    def _run_vina_docking_sync(
        self,
        smiles_list: List[Dict],
        protein_file: str,
        vina_box_config: Dict,
        output_dir: str,
        params: Dict
    ) -> str:
        """Synchronous wrapper for vina docking."""
        try:
            result_dir = vina_docking_from_list(
                ligands=smiles_list,
                receptor_pdbqt=protein_file,
                vina_box_config=vina_box_config,
                min_ph=params.get('min_ph', 6.0),
                max_ph=params.get('max_ph', 8.0),
                n_jobs=params.get('num_cpu', 8),
                exhaustiveness=params.get('exhaustiveness', 8),
                n_poses=params.get('n_poses', 10)
            )
            
            # Copy results to specified output directory
            if output_dir != result_dir:
                result_path = Path(result_dir)
                output_path = Path(output_dir)
                
                if (result_path / "dockRes.json").exists():
                    shutil.copy2(result_path / "dockRes.json", output_path / "dockRes.json")
                
                docked_src = result_path / "docked"
                docked_dst = output_path / "docked"
                if docked_src.exists():
                    if docked_dst.exists():
                        shutil.rmtree(docked_dst)
                    shutil.copytree(docked_src, docked_dst)
                
                logger.info(f"Results copied to output directory: {output_dir}")
            
            return result_dir
                
        except Exception as e:
            logger.error(f"Synchronous docking calculation failed: {e}")
            raise
    
    async def query_and_process_tasks(self) -> None:
        """Query and process pending docking tasks."""
        try:
            tasks = await DatabaseManager.get_pending_docking_tasks()
            
            if tasks:
                logger.info(f"Found {len(tasks)} pending docking tasks")
                
                connection = await get_db_connection()
                if not connection:
                    logger.error("Failed to get database connection")
                    return
                
                try:
                    for task in tasks:
                        task_id, user_id, task_type, job_dir, status = task
                        logger.info(f"Processing task: ID={task_id}, user={user_id}, type={task_type}")
                        
                        try:
                            await self.process_docking_task(task_id, job_dir, connection)
                        except Exception as e:
                            logger.error(f"Error processing task {task_id}: {e}")
                            continue
                finally:
                    connection.close()
            else:
                logger.debug("No pending docking tasks found")
                
        except Exception as e:
            logger.error(f"Error querying tasks: {e}")


async def background_task_runner() -> None:
    """Background task runner - polls database every 3 minutes."""
    processor = DockingTaskProcessor()
    logger.info("Docking background task started, polling every 3 minutes")
    
    while True:
        try:
            await processor.query_and_process_tasks()
            await asyncio.sleep(180)  # Wait 3 minutes
        except asyncio.CancelledError:
            logger.info("Background task runner cancelled")
            break
        except Exception as e:
            logger.error(f"Background task error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error


if __name__ == "__main__":
    asyncio.run(background_task_runner())
