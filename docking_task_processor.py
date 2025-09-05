"""
Docking任务处理器
基于peptide_opt的设计模式，处理从数据库获取的docking任务
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# 添加当前目录到Python路径
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))
sys.path.append(str(current_dir.parent))

from database.db import DatabaseManager, get_db_connection
from Vina.vina_workflow import vina_docking_from_list

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DockingTaskProcessor:
    """Docking任务处理器"""
    
    def __init__(self):
        self.current_dir = Path(__file__).parent.absolute()
        
    async def process_docking_task(self, task_id: str, job_dir: str, connection):
        """处理单个docking任务"""
        # 保存当前工作目录
        original_cwd = os.getcwd()
        
        try:
            logger.info(f"开始处理docking任务: {task_id}")
            
            # 切换到dockingVinaApp目录
            app_dir = self.current_dir.parent
            os.chdir(app_dir)
            logger.info(f"切换工作目录到: {app_dir}")
            
            # 读取任务配置文件 - 适配dockingVina的input.json格式
            job_path = Path(job_dir)
            input_dir = job_path / "input"
            config_file = input_dir / "input.json"
            
            if not config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_file}")
            
            # 解析配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            logger.info(f"任务配置: {config}")
            
            # 验证必要的配置项
            if 'ligands' not in config or not config['ligands']:
                raise ValueError("配置文件中缺少ligands信息")
            
            if 'receptor_pdbqt' not in config:
                raise ValueError("配置文件中缺少receptor_pdbqt路径")
            
            # 验证receptor文件存在
            receptor_path = Path(config['receptor_pdbqt'])
            if not receptor_path.exists():
                raise FileNotFoundError(f"Receptor文件不存在: {receptor_path}")
            
            # 设置输出目录
            output_dir = job_path / "output"
            output_dir.mkdir(exist_ok=True)
            
            # 生成临时SMILES文件到input目录
            smiles_file = input_dir / "ligands.csv"
            await self.create_smiles_file(config['ligands'], smiles_file)
            
            # 生成vina box配置文件到input目录
            vina_box_file = input_dir / "vina_box.json"
            await self.create_vina_box_file(config, vina_box_file)
            
            # 更新任务状态为running
            await DatabaseManager.update_task_status(connection, task_id, 'running')
            
            logger.info(f"任务 {task_id} 开始运行docking流程")
            
            # 准备docking参数
            docking_params = {
                'smiles_file': str(smiles_file),
                'protein_file': str(receptor_path),
                'vina_box_file': str(vina_box_file),
                'output_dir': str(output_dir),
                'num_poses': config.get('n_poses', 10),
                'energy_range': config.get('energy_range', 3),
                'exhaustiveness': config.get('exhaustiveness', 8),
                'num_cpu': config.get('n_jobs', 1),
                'seed': config.get('seed', 0)
            }
            
            # 运行docking计算
            await self.run_docking_calculation(docking_params, task_id)
            
            # 更新任务状态为finished
            await DatabaseManager.update_task_status(connection, task_id, 'finished')
            
            logger.info(f"任务 {task_id} 完成")
            
        except Exception as e:
            logger.error(f"任务 {task_id} 执行失败: {str(e)}")
            # 更新任务状态为failed
            try:
                await DatabaseManager.update_task_status(connection, task_id, 'failed')
            except Exception as db_error:
                logger.error(f"更新任务状态失败: {db_error}")
            raise
        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)
    
    async def create_smiles_file(self, ligands: list, output_file: Path):
        """从ligands列表创建SMILES CSV文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("SMILES,Title\n")  # 写入CSV头部
                for ligand in ligands:
                    smiles = ligand.get('smiles', '')
                    title = ligand.get('title', '')
                    f.write(f"{smiles},{title}\n")
            logger.info(f"SMILES文件已创建: {output_file}")
        except Exception as e:
            logger.error(f"创建SMILES文件失败: {e}")
            raise
    
    async def create_vina_box_file(self, config: dict, output_file: Path):
        """从配置创建vina box JSON文件"""
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
            
            logger.info(f"Vina box文件已创建: {output_file}")
        except Exception as e:
            logger.error(f"创建Vina box文件失败: {e}")
            raise
    
    async def run_docking_calculation(self, params: Dict[str, Any], task_id: str):
        """运行docking计算"""
        try:
            # 读取SMILES文件
            smiles_list = []
            with open(params['smiles_file'], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 跳过标题行
                for line in lines[1:]:
                    line = line.strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            smiles_list.append({
                                'smiles': parts[0].strip(),
                                'title': parts[1].strip()
                            })
            
            if not smiles_list:
                raise ValueError("SMILES文件中没有有效的分子数据")
            
            # 调用vina_docking_from_list函数
            # 注意：这里可能需要修改vina_workflow.py以支持异步调用
            logger.info(f"开始执行docking计算，共 {len(smiles_list)} 个分子")
            
            # 由于vina_docking_from_list可能是同步函数，我们在线程池中运行它
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_vina_docking_sync,
                smiles_list,
                params['protein_file'],
                params['vina_box_file'],
                params['output_dir'],
                params
            )
            
            logger.info(f"Docking计算完成，结果保存在: {params['output_dir']}")
            return result
            
        except Exception as e:
            logger.error(f"Docking计算失败: {e}")
            raise
    
    def _run_vina_docking_sync(self, smiles_list, protein_file, vina_box_file, output_dir, params):
        """同步运行vina docking的包装函数"""
        try:
            # 备份原始的vina_box.json文件
            import shutil
            default_box_file = self.current_dir / "resource" / "vina_box.json"
            backup_box_file = self.current_dir / "resource" / "vina_box.json.backup"
            
            # 备份原始文件
            if default_box_file.exists():
                shutil.copy2(default_box_file, backup_box_file)
            
            # 复制我们的box文件到默认位置
            shutil.copy2(vina_box_file, default_box_file)
            logger.info(f"Vina box文件已更新: {default_box_file}")
            
            try:
                # 调用vina_workflow.py中的vina_docking_from_list函数
                # 该函数接受ligands列表、receptor_pdbqt路径等参数
                result_dir = vina_docking_from_list(
                    ligands=smiles_list,  # 格式: [{"smiles":"...", "title":"..."}, ...]
                    receptor_pdbqt=protein_file,
                    min_ph=params.get('min_ph', 6.0),
                    max_ph=params.get('max_ph', 8.0),
                    n_jobs=params.get('num_cpu', 8)
                )
                
                # 将结果复制到指定的输出目录
                if output_dir != result_dir:
                    # 复制结果文件到指定的输出目录
                    result_path = Path(result_dir)
                    output_path = Path(output_dir)
                    
                    # 复制主要结果文件
                    if (result_path / "dockRes.json").exists():
                        shutil.copy2(result_path / "dockRes.json", output_path / "dockRes.json")
                    
                    # 复制docked文件夹
                    docked_src = result_path / "docked"
                    docked_dst = output_path / "docked"
                    if docked_src.exists():
                        if docked_dst.exists():
                            shutil.rmtree(docked_dst)
                        shutil.copytree(docked_src, docked_dst)
                    
                    logger.info(f"结果已复制到指定输出目录: {output_dir}")
                
                return result_dir
                
            finally:
                # 恢复原始的vina_box.json文件
                if backup_box_file.exists():
                    shutil.copy2(backup_box_file, default_box_file)
                    backup_box_file.unlink()  # 删除备份文件
                    logger.info("已恢复原始vina_box.json文件")
                
        except Exception as e:
            logger.error(f"同步docking计算失败: {e}")
            raise
    
    async def query_and_process_tasks(self):
        """查询并处理待处理的docking任务"""
        try:
            # 获取待处理的docking任务
            tasks = await DatabaseManager.get_pending_docking_tasks()
            
            if tasks:
                logger.info(f"发现 {len(tasks)} 个待处理的docking任务")
                
                # 获取数据库连接
                connection = await get_db_connection()
                if not connection:
                    logger.error("无法获取数据库连接")
                    return
                
                try:
                    for task in tasks:
                        task_id, user_id, task_type, job_dir, status = task
                        logger.info(f"处理任务: ID={task_id}, 用户={user_id}, 类型={task_type}")
                        
                        try:
                            await self.process_docking_task(task_id, job_dir, connection)
                        except Exception as e:
                            logger.error(f"处理任务 {task_id} 时发生错误: {e}")
                            continue
                finally:
                    connection.close()
            else:
                logger.info("没有发现待处理的docking任务")
                
        except Exception as e:
            logger.error(f"查询任务时发生错误: {e}")

async def background_task_runner():
    """后台定时任务运行器"""
    processor = DockingTaskProcessor()
    logger.info("Docking定时任务启动，每3分钟查询一次tasks表")
    
    while True:
        try:
            await processor.query_and_process_tasks()
            await asyncio.sleep(180)  # 等待3分钟
        except Exception as e:
            logger.error(f"定时任务执行错误: {e}")
            await asyncio.sleep(60)  # 发生错误时等待1分钟后重试

if __name__ == "__main__":
    # 可以单独运行任务处理器进行测试
    asyncio.run(background_task_runner())
