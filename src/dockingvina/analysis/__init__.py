"""
Analysis Module for DockingVina Project

This module provides binding mode analysis capabilities using BINANA toolkit.

Architecture:
    - binana_analyzer: Main analyzer class for BINANA integration
    - report_generator: Report generation for analysis results
    - utils/: Utility modules for parsing and processing

Usage:
    from dockingvina.analysis import (
        DockingVinaBindingAnalyzer,
        analyze_binding_quick,
        ReportGenerator,
        BINANA_AVAILABLE
    )
"""

import warnings

# BINANA availability flag
BINANA_AVAILABLE = False

# Import BINANA related modules (optional dependency)
try:
    from dockingvina.analysis.binana_analyzer import (
        DockingVinaBindingAnalyzer,
        BindingAnalyzer,  # Backward compatibility alias
        analyze_binding_quick,
        get_interaction_summary,
        find_key_residues,
        batch_analyze_docking_results,
        BINANA_AVAILABLE as _binana_available
    )
    BINANA_AVAILABLE = _binana_available
except ImportError as e:
    warnings.warn(f"BINANA analysis not available: {e}")
    DockingVinaBindingAnalyzer = None
    BindingAnalyzer = None
    analyze_binding_quick = None
    get_interaction_summary = None
    find_key_residues = None
    batch_analyze_docking_results = None

# Import other modules
try:
    from dockingvina.analysis.report_generator import ReportGenerator
except ImportError:
    ReportGenerator = None

try:
    from dockingvina.analysis.utils.interaction_parser import InteractionParser
except ImportError:
    InteractionParser = None

__version__ = "2.0.0"

__all__ = [
    "BINANA_AVAILABLE",
    "DockingVinaBindingAnalyzer",
    "BindingAnalyzer",
    "analyze_binding_quick",
    "get_interaction_summary",
    "find_key_residues",
    "batch_analyze_docking_results",
    "ReportGenerator",
    "InteractionParser",
]
