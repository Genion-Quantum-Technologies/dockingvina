"""
Services Package

External service integrations (storage, etc.)
"""

from dockingvina.services.storage import get_storage, SeaweedStorage

# Alias for backward compatibility
SeaweedStorageService = SeaweedStorage

__all__ = [
    "get_storage",
    "SeaweedStorage",
    "SeaweedStorageService",
]
