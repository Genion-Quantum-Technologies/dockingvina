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

# Main integration layer (recommended for new code)
from .dockingvina_integration import (
    DockingVinaBindingAnalyzer,
    analyze_binding_quick,
    get_interaction_summary,
    find_key_residues,
    batch_analyze_docking_results
)

# Backward compatibility imports
from .binana_analyzer import BindingAnalyzer  # Deprecated alias
from .interaction_parser import InteractionParser  # Deprecated location
from .report_generator import ReportGenerator

__version__ = "2.0.0"  # Updated for new architecture

# Primary exports (new architecture)
__all__ = [
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