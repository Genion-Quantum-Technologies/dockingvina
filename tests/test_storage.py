"""
Tests for the storage service.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock


class TestSeaweedStorage:
    """Tests for SeaweedStorage class."""
    
    def test_initialization(self):
        """Test storage initialization."""
        with patch('dockingvina.services.storage.seaweed_storage.storage_config') as mock_config:
            mock_config.filer_endpoint = "http://localhost:8888"
            mock_config.bucket = "test-bucket"
            mock_config.get_filer_base_url.return_value = "http://localhost:8888/buckets/test-bucket"
            
            from dockingvina.services.storage.seaweed_storage import SeaweedStorage
            
            storage = SeaweedStorage()
            
            assert storage.filer_endpoint == "http://localhost:8888"
            assert storage.bucket == "test-bucket"
    
    def test_get_url(self):
        """Test URL construction."""
        with patch('dockingvina.services.storage.seaweed_storage.storage_config') as mock_config:
            mock_config.filer_endpoint = "http://localhost:8888"
            mock_config.bucket = "test-bucket"
            mock_config.get_filer_base_url.return_value = "http://localhost:8888/buckets/test-bucket"
            
            from dockingvina.services.storage.seaweed_storage import SeaweedStorage
            
            storage = SeaweedStorage()
            
            url = storage._get_url("path/to/file.pdbqt")
            assert url == "http://localhost:8888/buckets/test-bucket/path/to/file.pdbqt"
            
            # Test with leading slash
            url = storage._get_url("/path/to/file.pdbqt")
            assert url == "http://localhost:8888/buckets/test-bucket/path/to/file.pdbqt"


class TestGetStorage:
    """Tests for get_storage function."""
    
    def test_singleton_pattern(self):
        """Test that get_storage returns singleton instance."""
        from dockingvina.services.storage import get_storage, _storage_instance
        import dockingvina.services.storage as storage_module
        
        # Reset singleton
        storage_module._storage_instance = None
        
        storage1 = get_storage()
        storage2 = get_storage()
        
        assert storage1 is storage2
