"""
DockingVina Settings

Central configuration settings loaded from environment variables.
Supports both legacy dict-based config and modern pydantic-style Settings class.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

# Load .env file if available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


# =============================================================================
# Modern Settings Class (Pydantic-style)
# =============================================================================

class Settings:
    """
    Application settings loaded from environment variables.
    
    Usage:
        settings = get_settings()
        print(settings.APP_NAME)
        print(settings.DB_HOST)
    """
    
    def __init__(self):
        # Application
        self.APP_NAME: str = os.getenv("APP_NAME", "DockingVina")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        
        # Database
        self.DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
        self.DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
        self.DB_USER: str = os.getenv("DB_USER", "vina_user")
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
        self.DB_NAME: str = os.getenv("DB_NAME", "dockingvina")
        
        # Task Processing
        self.TASK_QUERY_INTERVAL: int = int(os.getenv("TASK_QUERY_INTERVAL", "180"))
        self.MAX_CONCURRENT_TASKS: int = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))
        
        # Docking Parameters
        self.DOCKING_NUM_CPU: int = int(os.getenv("DOCKING_NUM_CPU", "8"))
        self.DOCKING_EXHAUSTIVENESS: int = int(os.getenv("DOCKING_EXHAUSTIVENESS", "8"))
        self.DOCKING_NUM_POSES: int = int(os.getenv("DOCKING_NUM_POSES", "10"))
        
        # Paths
        self.RESOURCE_DIR: str = os.getenv("RESOURCE_DIR", "/tmp/docking_vina_app/resource")
        self.TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp/docking_vina_app")
        self.LOG_DIR: str = os.getenv("LOG_DIR", "/tmp/docking_vina_app/logs")
        
        # BINANA
        self.BINANA_ENABLED: bool = os.getenv("BINANA_ENABLED", "true").lower() == "true"
        self.BINANA_AUTO_ANALYZE: bool = os.getenv("BINANA_AUTO_ANALYZE", "true").lower() == "true"
        self.BINANA_PATH: Optional[str] = os.getenv("BINANA_PATH", None)
        
        # SeaweedFS Storage
        self.SEAWEEDFS_MASTER_URL: str = os.getenv("SEAWEEDFS_MASTER_URL", "http://localhost:9333")
        self.SEAWEEDFS_FILER_URL: str = os.getenv("SEAWEEDFS_FILER_URL", "http://localhost:8888")
        self.SEAWEEDFS_S3_URL: str = os.getenv("SEAWEEDFS_S3_URL", "http://localhost:8333")
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL database URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings instance (cached)
    """
    return Settings()


# =============================================================================
# Legacy Dictionary Configuration (for backward compatibility)
# =============================================================================

DATABASE_CONFIG: Dict[str, Any] = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "vina_user"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "dockingvina"),
}


# =============================================================================
# Task Processing Configuration
# =============================================================================

TASK_CONFIG: Dict[str, Any] = {
    "query_interval": int(os.getenv("TASK_QUERY_INTERVAL", "180")),
    "task_type": "docking",
    "max_concurrent_tasks": int(os.getenv("MAX_CONCURRENT_TASKS", "3")),
}


# =============================================================================
# Default Docking Parameters
# =============================================================================

DEFAULT_DOCKING_PARAMS: Dict[str, Any] = {
    "num_poses": 10,
    "energy_range": 3,
    "exhaustiveness": 8,
    "num_cpu": int(os.getenv("DOCKING_NUM_CPU", "8")),
    "seed": 0,
    "min_ph": 6.0,
    "max_ph": 8.0,
}


# =============================================================================
# File Paths Configuration
# =============================================================================

PATHS: Dict[str, str] = {
    "resource_dir": os.getenv("RESOURCE_DIR", "/tmp/docking_vina_app/resource"),
    "temp_dir": os.getenv("TEMP_DIR", "/tmp/docking_vina_app"),
    "log_dir": os.getenv("LOG_DIR", "/tmp/docking_vina_app/logs"),
}


# =============================================================================
# BINANA Analysis Configuration
# =============================================================================

BINANA_CONFIG: Dict[str, Any] = {
    "enabled": os.getenv("BINANA_ENABLED", "true").lower() == "true",
    "auto_analyze": os.getenv("BINANA_AUTO_ANALYZE", "true").lower() == "true",
    "timeout": int(os.getenv("BINANA_TIMEOUT", "300")),
    "binana_path": os.getenv("BINANA_PATH", None),
    "save_intermediate_files": os.getenv("BINANA_SAVE_INTERMEDIATE", "false").lower() == "true",
    "analysis_output_dir": "binding_analysis",
}
