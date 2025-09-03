"""
异步数据库连接和操作模块
"""
import aiomysql
import logging
from .config import DB_CONFIG

logger = logging.getLogger(__name__)

async def get_db_connection():
    """获取异步数据库连接"""
    try:
        connection = await aiomysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return None

class DatabaseManager:
    """数据库管理器"""
    
    @staticmethod
    async def get_pending_docking_tasks():
        """获取待处理的docking任务"""
        connection = await get_db_connection()
        if not connection:
            return []
        
        try:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, user_id, task_type, job_dir, status FROM tasks WHERE status = %s AND task_type = %s",
                    ('pending', 'docking')
                )
                tasks = await cursor.fetchall()
                return tasks
        except Exception as e:
            logger.error(f"查询docking任务失败: {e}")
            return []
        finally:
            connection.close()
    
    @staticmethod
    async def update_task_status(connection, task_id: str, status: str):
        """更新任务状态"""
        try:
            async with connection.cursor() as cursor:
                if status == 'running':
                    await cursor.execute(
                        "UPDATE tasks SET status = %s, started_at = NOW() WHERE id = %s",
                        (status, task_id)
                    )
                elif status in ['finished', 'failed']:
                    await cursor.execute(
                        "UPDATE tasks SET status = %s, finished_at = NOW() WHERE id = %s",
                        (status, task_id)
                    )
                else:
                    await cursor.execute(
                        "UPDATE tasks SET status = %s WHERE id = %s",
                        (status, task_id)
                    )
                logger.info(f"任务 {task_id} 状态更新为: {status}")
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
