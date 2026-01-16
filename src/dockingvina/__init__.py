"""
DockingVina - Molecular docking service using AutoDock Vina

A FastAPI-based molecular docking service with database task management
and BINANA binding interaction analysis.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from dockingvina.core.task_processor import DockingTaskProcessor
from dockingvina.core.async_processor import AsyncTaskProcessor

__all__ = [
    "__version__",
    "DockingTaskProcessor",
    "AsyncTaskProcessor",
]
