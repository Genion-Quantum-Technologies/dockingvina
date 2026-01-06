"""
PostgreSQL 数据库配置
"""
import os
from pathlib import Path

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    # 查找项目根目录的 .env 文件
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 未安装时跳过

# PostgreSQL 数据库配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "secret"),
    "database": os.getenv("DB_NAME", "mydatabase"),
}

# 连接池配置
POOL_CONFIG = {
    "min_size": int(os.getenv("DB_POOL_MIN", 1)),
    "max_size": int(os.getenv("DB_POOL_MAX", 10)),
}
