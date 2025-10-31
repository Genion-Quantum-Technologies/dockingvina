"""
Interaction parser utilities for BINANA analysis results.

NOTE: This module has been moved to analysis.utils.interaction_parser
This file maintains backward compatibility.

For new code, please use:
    from analysis.utils.interaction_parser import InteractionParser
"""

import warnings

# Import from the new location
from .utils.interaction_parser import InteractionParser

# Issue a deprecation warning when this module is imported
warnings.warn(
    "Importing from 'analysis.interaction_parser' is deprecated. "
    "Please use 'from analysis.utils.interaction_parser import InteractionParser' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['InteractionParser']
