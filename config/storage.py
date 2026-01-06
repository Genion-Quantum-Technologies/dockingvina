"""
SeaweedFS 存储配置
"""
import os
from pathlib import Path

# SeaweedFS API 类型: filer 或 s3
api_type = os.getenv("SEAWEED_API_TYPE", "filer")

# SeaweedFS Filer API 端点
filer_endpoint = os.getenv("SEAWEED_FILER_ENDPOINT", "http://localhost:8888")

# SeaweedFS S3 API 端点（备用）
s3_endpoint = os.getenv("SEAWEED_S3_ENDPOINT", "http://localhost:8333")

# S3 访问密钥
access_key = os.getenv("SEAWEED_ACCESS_KEY", "")
secret_key = os.getenv("SEAWEED_SECRET_KEY", "")

# Bucket 名称
bucket = os.getenv("SEAWEED_BUCKET", "astramolecula")

# 临时文件目录
temp_dir = Path(os.getenv("TEMP_DIR", "/tmp/dockingvina"))

# 预签名 URL 过期时间（秒）
presigned_url_expires = int(os.getenv("PRESIGNED_URL_EXPIRES", 3600))


def get_filer_base_url() -> str:
    """获取 Filer 的 bucket 基础 URL"""
    return f"{filer_endpoint}/buckets/{bucket}"


def ensure_temp_dir() -> Path:
    """确保临时目录存在"""
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir
