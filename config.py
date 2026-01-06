"""
DockingVinaApp 配置文件
"""

import os
from pathlib import Path

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 未安装时跳过

# 数据库配置 (从环境变量读取)
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "vina_user"), 
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "dockingvina"),
}

# 任务配置
TASK_CONFIG = {
    "query_interval": int(os.getenv("TASK_QUERY_INTERVAL", "180")),  # 查询任务间隔（秒）
    "task_type": "docking",  # 任务类型
    "max_concurrent_tasks": int(os.getenv("MAX_CONCURRENT_TASKS", "3")),  # 最大并发任务数
}

# Docking 默认参数
DEFAULT_DOCKING_PARAMS = {
    "num_poses": 10,
    "energy_range": 3,
    "exhaustiveness": 8,
    "num_cpu": int(os.getenv("DOCKING_NUM_CPU", "8")),
    "seed": 0,
    "min_ph": 6.0,
    "max_ph": 8.0
}

# 文件路径配置 (从环境变量读取)
PATHS = {
    "resource_dir": os.getenv("RESOURCE_DIR", "/tmp/docking_vina_app/resource"),
    "temp_dir": os.getenv("TEMP_DIR", "/tmp/docking_vina_app"),
    "log_dir": os.getenv("LOG_DIR", "/tmp/docking_vina_app/logs")
}

# BINANA 分析配置
BINANA_CONFIG = {
    "enabled": os.getenv("BINANA_ENABLED", "true").lower() == "true",  # 是否启用 BINANA 分析
    "auto_analyze": os.getenv("BINANA_AUTO_ANALYZE", "true").lower() == "true",  # 对接完成后自动进行分析
    "timeout": int(os.getenv("BINANA_TIMEOUT", "300")),  # 分析超时时间（秒）
    "binana_path": os.getenv("BINANA_PATH", None),  # BINANA 路径，None 为自动检测
    "save_intermediate_files": os.getenv("BINANA_SAVE_INTERMEDIATE", "false").lower() == "true",  # 是否保存中间文件
    "analysis_output_dir": "binding_analysis"  # 分析结果输出目录名
}
