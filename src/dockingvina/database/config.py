"""
PostgreSQL Database Configuration
"""

import os
from pathlib import Path
from typing import Any, Dict

# Load .env file if available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


class DatabaseConfig:
    """
    Database configuration class.
    
    Provides both class-level access and instance-level access to database settings.
    """
    
    # Class-level defaults
    host: str = os.getenv("DB_HOST", "127.0.0.1")
    port: int = int(os.getenv("DB_PORT", "5432"))
    user: str = os.getenv("DB_USER", "admin")
    password: str = os.getenv("DB_PASSWORD", "secret")
    database: str = os.getenv("DB_NAME", "mydatabase")
    
    # Pool settings
    pool_min_size: int = int(os.getenv("DB_POOL_MIN", "1"))
    pool_max_size: int = int(os.getenv("DB_POOL_MAX", "10"))
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        """Initialize with optional override values."""
        self.host = host or DatabaseConfig.host
        self.port = port or DatabaseConfig.port
        self.user = user or DatabaseConfig.user
        self.password = password or DatabaseConfig.password
        self.database = database or DatabaseConfig.database
    
    @property
    def dsn(self) -> str:
        """Get PostgreSQL DSN connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
        }


# PostgreSQL configuration (legacy dict format)
DB_CONFIG: Dict[str, Any] = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "secret"),
    "database": os.getenv("DB_NAME", "mydatabase"),
}

# Connection pool configuration
POOL_CONFIG: Dict[str, int] = {
    "min_size": int(os.getenv("DB_POOL_MIN", "1")),
    "max_size": int(os.getenv("DB_POOL_MAX", "10")),
}
