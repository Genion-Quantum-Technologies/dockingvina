"""
Storage Service Module

Provides a unified object storage interface using SeaweedFS as backend.

Usage:
    from dockingvina.services.storage import get_storage
    
    storage = get_storage()
    
    # Upload file
    await storage.upload_file(local_path, "uploads/user_id/file.pdb")
    
    # Upload bytes
    await storage.upload_bytes(content, "uploads/user_id/file.pdb")
    
    # Download file
    await storage.download_file("uploads/user_id/file.pdb", local_path)
    
    # Generate presigned URL
    url = await storage.get_presigned_url("uploads/user_id/file.pdb")
    
    # Check if file exists
    exists = await storage.file_exists("uploads/user_id/file.pdb")
    
    # List files
    files = await storage.list_files("uploads/user_id/")
    
    # Delete file
    await storage.delete_file("uploads/user_id/file.pdb")
"""

import logging
from typing import Optional

from dockingvina.services.storage.seaweed_storage import SeaweedStorage

logger = logging.getLogger(__name__)

_storage_instance: Optional[SeaweedStorage] = None


def get_storage() -> SeaweedStorage:
    """
    Get SeaweedFS storage instance (singleton).
    
    Returns:
        SeaweedStorage instance
    """
    global _storage_instance
    
    if _storage_instance is None:
        _storage_instance = SeaweedStorage()
        logger.info("SeaweedFS storage instance created")
    
    return _storage_instance


__all__ = ['get_storage', 'SeaweedStorage']
