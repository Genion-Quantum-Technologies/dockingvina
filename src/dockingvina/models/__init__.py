"""
Models Package

Data models and schemas for the docking service.
"""

# Re-export from legacy location for backward compatibility
import sys
from pathlib import Path

_models_legacy_path = Path(__file__).parent.parent.parent.parent / "models"
if _models_legacy_path.exists() and str(_models_legacy_path) not in sys.path:
    sys.path.insert(0, str(_models_legacy_path))

try:
    from dataset import *
except ImportError:
    pass
