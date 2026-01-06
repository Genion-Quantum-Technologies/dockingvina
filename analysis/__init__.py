"""
Analysis module for DockingVina project

This module provides binding mode analysis capabilities using BINANA toolkit.

Architecture:
    - binana_toolkit/: Base BINANA wrapper (generic, reusable)
    - dockingvina_integration: DockingVina-specific enhancements
    - binana_analyzer: Compatibility layer (deprecated, use dockingvina_integration)
    - utils/: Utility modules for parsing and processing
    - report_generator: Report generation for analysis results

Recommended usage for new code:
    from analysis.dockingvina_integration import DockingVinaBindingAnalyzer
    from analysis.report_generator import ReportGenerator
    from analysis.utils.interaction_parser import InteractionParser
"""

import warnings

# BINANA 可用性标志
BINANA_AVAILABLE = False

# 尝试导入 BINANA 相关模块（可选依赖）
try:
    from .dockingvina_integration import (
        DockingVinaBindingAnalyzer,
        analyze_binding_quick,
        get_interaction_summary,
        find_key_residues,
        batch_analyze_docking_results,
        BINANA_AVAILABLE as _binana_available
    )
    BINANA_AVAILABLE = _binana_available
except ImportError as e:
    warnings.warn(f"BINANA analysis not available: {e}")
    # 提供空的占位符，避免导入错误
    DockingVinaBindingAnalyzer = None
    analyze_binding_quick = None
    get_interaction_summary = None
    find_key_residues = None
    batch_analyze_docking_results = None

# Backward compatibility imports
try:
    from .binana_analyzer import BindingAnalyzer  # Deprecated alias
except ImportError:
    BindingAnalyzer = None

from .interaction_parser import InteractionParser
from .report_generator import ReportGenerator

__version__ = "2.0.0"  # Updated for new architecture

# Primary exports (new architecture)
__all__ = [
    # Availability flag
    "BINANA_AVAILABLE",
    
    # New integration layer (recommended)
    "DockingVinaBindingAnalyzer",
    "analyze_binding_quick",
    "get_interaction_summary",
    "find_key_residues",
    "batch_analyze_docking_results",
    
    # Utilities
    "ReportGenerator",
    "InteractionParser",
    
    # Backward compatibility (deprecated)
    "BindingAnalyzer",
]