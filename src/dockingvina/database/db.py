"""
PostgreSQL Database Connection Module

Provides database connection pooling with async wrapper support.
"""

import asyncio
import logging
from functools import partial
from typing import Any, List, Optional, Tuple

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from dockingvina.database.config import DB_CONFIG, POOL_CONFIG

logger = logging.getLogger(__name__)

# Lazily initialized connection pool
_pool: Optional[pool.ThreadedConnectionPool] = None


def _get_pool() -> pool.ThreadedConnectionPool:
    """Get or create the connection pool."""
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
    """PostgreSQL connection wrapper for compatibility with async interface."""
    
    def __init__(self, conn):
        self._conn = conn
        self._conn.autocommit = True
    
    def cursor(self, dictionary: bool = False):
        """Get a cursor, optionally as dictionary cursor."""
        if dictionary:
            return self._conn.cursor(cursor_factory=RealDictCursor)
        return self._conn.cursor()
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self._conn.commit()
    
    def close(self) -> None:
        """Return connection to the pool."""
        try:
            pool_obj = _get_pool()
            pool_obj.putconn(self._conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")


class AsyncCursorWrapper:
    """Async cursor wrapper for compatibility with existing async code."""
    
    def __init__(self, cursor):
        self._cursor = cursor
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._cursor.close()
        return False
    
    async def execute(self, query: str, params: Optional[Tuple] = None):
        """Execute a query asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._cursor.execute(query, params)
        )
    
    async def fetchall(self) -> List[Any]:
        """Fetch all results asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._cursor.fetchall)
    
    async def fetchone(self) -> Optional[Any]:
        """Fetch one result asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._cursor.fetchone)


class AsyncConnectionWrapper:
    """Async connection wrapper for compatibility with existing async code."""
    
    def __init__(self, pg_conn: PostgresConnection):
        self._pg_conn = pg_conn
    
    def cursor(self, dictionary: bool = False) -> AsyncCursorWrapper:
        """Get an async cursor wrapper."""
        cursor = self._pg_conn.cursor(dictionary=dictionary)
        return AsyncCursorWrapper(cursor)
    
    async def commit(self) -> None:
        """Commit asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._pg_conn.commit)
    
    def close(self) -> None:
        """Close the connection."""
        self._pg_conn.close()


def get_db_connection_sync() -> Optional[PostgresConnection]:
    """Get a database connection synchronously."""
    try:
        pool_obj = _get_pool()
        conn = pool_obj.getconn()
        return PostgresConnection(conn)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


async def get_db_connection() -> Optional[AsyncConnectionWrapper]:
    """Get a database connection asynchronously (for compatibility)."""
    loop = asyncio.get_event_loop()
    pg_conn = await loop.run_in_executor(None, get_db_connection_sync)
    if pg_conn is None:
        return None
    return AsyncConnectionWrapper(pg_conn)


class DatabaseManager:
    """Database operations manager."""
    
    @staticmethod
    async def get_pending_docking_tasks() -> List[Tuple]:
        """Get pending docking tasks from the database."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            DatabaseManager._get_pending_docking_tasks_sync
        )
    
    @staticmethod
    def _get_pending_docking_tasks_sync() -> List[Tuple]:
        """Synchronously get pending docking tasks."""
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
            logger.error(f"Failed to query docking tasks: {e}")
            return []
        finally:
            conn.close()
    
    @staticmethod
    async def update_task_status(connection, task_id: str, status: str) -> None:
        """Update task status in the database."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(DatabaseManager._update_task_status_sync, task_id, status)
        )
    
    @staticmethod
    def _update_task_status_sync(task_id: str, status: str) -> None:
        """Synchronously update task status."""
        conn = get_db_connection_sync()
        if not conn:
            logger.error("Failed to get database connection")
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
            logger.info(f"Task {task_id} status updated to: {status}")
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
        finally:
            conn.close()


def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("PostgreSQL connection pool closed")
