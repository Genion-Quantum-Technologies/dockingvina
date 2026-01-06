"""
PostgreSQL 数据库连接模块
使用同步 psycopg2 + asyncio.run_in_executor 实现异步操作
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import asyncio
import logging
from functools import partial
from .config import DB_CONFIG, POOL_CONFIG

logger = logging.getLogger(__name__)

# 延迟初始化的连接池
_pool = None


def _get_pool():
    """获取或创建连接池"""
    global _pool
    if _pool is None:
        logger.info("Creating PostgreSQL connection pool...")
        _pool = pool.ThreadedConnectionPool(
            minconn=POOL_CONFIG.get("min_size", 1),
            maxconn=POOL_CONFIG.get("max_size", 10),
            **DB_CONFIG
        )
    return _pool


class PostgresConnection:
    """PostgreSQL 连接包装器，兼容原有的异步接口"""
    
    def __init__(self, conn):
        self._conn = conn
        self._conn.autocommit = True
    
    def cursor(self, dictionary=False):
        if dictionary:
            return self._conn.cursor(cursor_factory=RealDictCursor)
        return self._conn.cursor()
    
    def commit(self):
        self._conn.commit()
    
    def close(self):
        """归还连接到连接池"""
        try:
            pool_obj = _get_pool()
            pool_obj.putconn(self._conn)
        except Exception as e:
            logger.error(f"归还连接失败: {e}")


class AsyncCursorWrapper:
    """异步游标包装器，兼容原有的 async with cursor 语法"""
    
    def __init__(self, cursor):
        self._cursor = cursor
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._cursor.close()
        return False
    
    async def execute(self, query, params=None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._cursor.execute(query, params)
        )
    
    async def fetchall(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._cursor.fetchall)
    
    async def fetchone(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._cursor.fetchone)


class AsyncConnectionWrapper:
    """异步连接包装器，保持与原有代码兼容"""
    
    def __init__(self, pg_conn: PostgresConnection):
        self._pg_conn = pg_conn
    
    def cursor(self, dictionary=False):
        """返回异步游标包装器"""
        cursor = self._pg_conn.cursor(dictionary=dictionary)
        return AsyncCursorWrapper(cursor)
    
    async def commit(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._pg_conn.commit)
    
    def close(self):
        self._pg_conn.close()


def get_db_connection_sync():
    """同步获取数据库连接"""
    try:
        pool_obj = _get_pool()
        conn = pool_obj.getconn()
        return PostgresConnection(conn)
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return None


async def get_db_connection():
    """异步获取数据库连接（兼容现有代码）"""
    loop = asyncio.get_event_loop()
    pg_conn = await loop.run_in_executor(None, get_db_connection_sync)
    if pg_conn is None:
        return None
    return AsyncConnectionWrapper(pg_conn)


class DatabaseManager:
    """数据库管理器"""
    
    @staticmethod
    async def get_pending_docking_tasks():
        """获取待处理的docking任务"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            DatabaseManager._get_pending_docking_tasks_sync
        )
    
    @staticmethod
    def _get_pending_docking_tasks_sync():
        """同步获取待处理任务"""
        conn = get_db_connection_sync()
        if not conn:
            return []
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, user_id, task_type, job_dir, status "
                    "FROM tasks WHERE status = %s AND task_type = %s",
                    ('pending', 'docking')
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"查询docking任务失败: {e}")
            return []
        finally:
            conn.close()
    
    @staticmethod
    async def update_task_status(connection, task_id: str, status: str):
        """更新任务状态"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(DatabaseManager._update_task_status_sync, task_id, status)
        )
    
    @staticmethod
    def _update_task_status_sync(task_id: str, status: str):
        """同步更新任务状态"""
        conn = get_db_connection_sync()
        if not conn:
            logger.error("无法获取数据库连接")
            return
        try:
            with conn.cursor() as cursor:
                if status == 'running':
                    cursor.execute(
                        "UPDATE tasks SET status = %s, started_at = NOW() WHERE id = %s",
                        (status, task_id)
                    )
                elif status in ['finished', 'failed']:
                    cursor.execute(
                        "UPDATE tasks SET status = %s, finished_at = NOW() WHERE id = %s",
                        (status, task_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE tasks SET status = %s WHERE id = %s",
                        (status, task_id)
                    )
            conn.commit()
            logger.info(f"任务 {task_id} 状态更新为: {status}")
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
        finally:
            conn.close()


def close_pool():
    """关闭连接池"""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("PostgreSQL connection pool closed")
