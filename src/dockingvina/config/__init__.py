"""
DockingVina Configuration Package

This package contains all configuration modules for the docking service.
"""

from dockingvina.config.settings import (
    # Modern Settings class
    Settings,
    get_settings,
    # Legacy dict configs
    DATABASE_CONFIG,
    TASK_CONFIG,
    DEFAULT_DOCKING_PARAMS,
    PATHS,
    BINANA_CONFIG,
)
from dockingvina.config import storage
from dockingvina.config.logging_config import setup_logging, get_log_file_path

__all__ = [
    # Modern settings
    "Settings",
    "get_settings",
    # Legacy dict configs
    "DATABASE_CONFIG",
    "TASK_CONFIG",
    "DEFAULT_DOCKING_PARAMS",
    "PATHS",
    "BINANA_CONFIG",
    # Other modules
    "storage",
    "setup_logging",
    "get_log_file_path",
]
