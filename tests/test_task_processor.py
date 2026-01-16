"""
Tests for the task processor module.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


class TestDockingTaskProcessor:
    """Tests for DockingTaskProcessor class."""
    
    @pytest.mark.asyncio
    async def test_create_smiles_file(self, temp_directory, sample_ligand_data):
        """Test SMILES file creation."""
        from dockingvina.core.task_processor import DockingTaskProcessor
        
        processor = DockingTaskProcessor()
        output_file = temp_directory / "test_ligands.csv"
        
        await processor._create_smiles_file(sample_ligand_data, output_file)
        
        assert output_file.exists()
        content = output_file.read_text()
        assert "SMILES,Title" in content
        assert "aspirin" in content
        assert "ibuprofen" in content
    
    @pytest.mark.asyncio
    async def test_create_vina_box_file(self, temp_directory, sample_config):
        """Test vina box file creation."""
        import json
        from dockingvina.core.task_processor import DockingTaskProcessor
        
        processor = DockingTaskProcessor()
        output_file = temp_directory / "vina_box.json"
        
        await processor._create_vina_box_file(sample_config, output_file)
        
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        
        assert "center" in data
        assert "box_size" in data
        assert data["center"] == [0.0, 0.0, 0.0]
        assert data["box_size"] == [20.0, 20.0, 20.0]


class TestAsyncTaskProcessor:
    """Tests for AsyncTaskProcessor class."""
    
    def test_initialization(self):
        """Test processor initialization."""
        from dockingvina.core.async_processor import AsyncTaskProcessor
        
        processor = AsyncTaskProcessor(max_workers=4)
        
        assert processor.max_workers == 4
        assert processor.is_running
        assert len(processor.active_tasks) == 0
    
    def test_get_active_tasks_empty(self):
        """Test getting active tasks when empty."""
        from dockingvina.core.async_processor import AsyncTaskProcessor
        
        processor = AsyncTaskProcessor()
        
        assert processor.get_active_tasks() == []
        assert processor.get_task_count() == 0
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test processor shutdown."""
        from dockingvina.core.async_processor import AsyncTaskProcessor
        
        processor = AsyncTaskProcessor()
        
        await processor.shutdown()
        
        assert not processor.is_running
