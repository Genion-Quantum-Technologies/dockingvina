"""
Pytest Configuration and Fixtures

Shared fixtures for all tests.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_storage():
    """Mock storage service for testing."""
    storage = AsyncMock()
    storage.upload_file = AsyncMock(return_value="test/path/file.pdbqt")
    storage.download_file = AsyncMock()
    storage.download_bytes = AsyncMock(return_value=b"test content")
    storage.file_exists = AsyncMock(return_value=True)
    storage.delete_file = AsyncMock(return_value=True)
    storage.list_files = AsyncMock(return_value=[])
    return storage


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing."""
    connection = AsyncMock()
    cursor = AsyncMock()
    cursor.execute = AsyncMock()
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.fetchone = AsyncMock(return_value=None)
    connection.cursor = MagicMock(return_value=cursor)
    connection.commit = AsyncMock()
    connection.close = MagicMock()
    
    # Support async context manager
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=None)
    
    return connection


@pytest.fixture
def sample_ligand_data():
    """Sample ligand data for testing."""
    return [
        {"smiles": "CC(=O)OC1=CC=CC=C1C(=O)O", "title": "aspirin"},
        {"smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", "title": "ibuprofen"},
    ]


@pytest.fixture
def sample_config():
    """Sample docking configuration for testing."""
    return {
        "ligands": [
            {"smiles": "CC(=O)OC1=CC=CC=C1C(=O)O", "title": "aspirin"},
        ],
        "receptor_pdbqt": "receptor.pdbqt",
        "center_x": 0.0,
        "center_y": 0.0,
        "center_z": 0.0,
        "box_size_x": 20.0,
        "box_size_y": 20.0,
        "box_size_z": 20.0,
        "exhaustiveness": 8,
        "n_poses": 10,
    }


@pytest.fixture
def temp_directory(tmp_path):
    """Temporary directory for test files."""
    test_dir = tmp_path / "dockingvina_test"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir
