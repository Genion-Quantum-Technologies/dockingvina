"""
Tests for the FastAPI application endpoints.
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint returns correct response."""
        from dockingvina.app import root
        
        response = await root()
        
        assert response["message"] == "Docking Vina API"
        assert response["version"] == "1.0.0"
        assert response["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_health_check_no_processor(self):
        """Test health check when processor is not initialized."""
        from dockingvina import app as app_module
        
        # Temporarily set processor to None
        original = app_module.async_processor
        app_module.async_processor = None
        
        try:
            response = await app_module.health_check()
            assert response["status"] == "healthy"
            assert response["active_tasks"] == 0
        finally:
            app_module.async_processor = original


class TestStatusEndpoint:
    """Test status endpoint."""
    
    @pytest.mark.asyncio
    async def test_status_initializing(self):
        """Test status when processor is initializing."""
        from dockingvina import app as app_module
        
        original = app_module.async_processor
        app_module.async_processor = None
        
        try:
            response = await app_module.get_status()
            assert response["status"] == "initializing"
        finally:
            app_module.async_processor = original
