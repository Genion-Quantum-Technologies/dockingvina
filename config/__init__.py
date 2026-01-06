"""
DockingVina 配置模块

提供统一的配置访问接口，支持 YAML 配置文件和环境变量。

使用示例:
    from config import storage
    
    # 获取 SeaweedFS Filer 端点
    endpoint = storage.filer_endpoint
    
    # 获取临时目录
    temp = storage.temp_dir
"""
from . import storage

__all__ = ['storage']