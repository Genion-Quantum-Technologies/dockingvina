#!/usr/bin/env python3
"""
BINANA Binding Mode Analyzer for DockingVina Integration
Enhanced wrapper for BINANA analysis with dockingvina-specific adaptations.

NOTE: This module is now a compatibility layer. For new code, use:
    from analysis.dockingvina_integration import DockingVinaBindingAnalyzer
    
This file maintains backward compatibility for existing code that imports:
    from analysis.binana_analyzer import BindingAnalyzer
"""

from typing import Dict, List, Optional

# Import the new integration layer
from .dockingvina_integration import (
    DockingVinaBindingAnalyzer,
    analyze_binding_quick,
    get_interaction_summary,
    find_key_residues,
    batch_analyze_docking_results,
    BINANA_AVAILABLE
)


# Backward compatibility: BindingAnalyzer is now an alias to DockingVinaBindingAnalyzer
class BindingAnalyzer(DockingVinaBindingAnalyzer):
    """
    Enhanced wrapper for BINANA analysis integrated with DockingVina workflow.
    
    This is now a compatibility wrapper. All functionality has been moved to
    DockingVinaBindingAnalyzer in dockingvina_integration.py.
    
    For new code, please use:
        from analysis.dockingvina_integration import DockingVinaBindingAnalyzer
    """
    pass


# Re-export convenience functions for backward compatibility
__all__ = [
    'BindingAnalyzer',
    'analyze_binding_quick',
    'get_interaction_summary',
    'find_key_residues',
    'batch_analyze_docking_results',
    'BINANA_AVAILABLE'
]
