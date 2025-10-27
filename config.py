"""
DockingVinaApp 配置文件
"""

# 数据库配置
DATABASE_CONFIG = {
    "host": "127.0.0.1",
    "user": "vina_user", 
    "password": "Aa7758258123",
    "database": "project1",
    "charset": "utf8mb4"
}

# 任务配置
TASK_CONFIG = {
    "query_interval": 180,  # 查询任务间隔（秒）
    "task_type": "docking",  # 任务类型
    "max_concurrent_tasks": 3,  # 最大并发任务数
}

# Docking 默认参数
DEFAULT_DOCKING_PARAMS = {
    "num_poses": 10,
    "energy_range": 3,
    "exhaustiveness": 8,
    "num_cpu": 8,
    "seed": 0,
    "min_ph": 6.0,
    "max_ph": 8.0
}

# 文件路径配置
PATHS = {
    "resource_dir": "/home/davis/projects/genion_quantum/dockingvina/resource",
    "temp_dir": "/tmp/docking_vina_app",
    "log_dir": "/home/davis/projects/serverlogs"
}

# BINANA 分析配置
BINANA_CONFIG = {
    "enabled": True,  # 是否启用 BINANA 分析
    "auto_analyze": True,  # 对接完成后自动进行分析
    "timeout": 300,  # 分析超时时间（秒）
    "binana_path": None,  # BINANA 路径，None 为自动检测
    "save_intermediate_files": False,  # 是否保存中间文件
    "analysis_output_dir": "binding_analysis"  # 分析结果输出目录名
}
