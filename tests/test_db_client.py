"""
Tests for the database client implementations.
"""

import pytest
from amadeus_burger import Settings
from amadeus_burger.db import SQLiteClient
from amadeus_burger.db.schemas import QueryResult

@pytest.fixture
def db_client():
    """Create a test database client."""
    Settings.sqlite.connection_string = ":memory:"  # Use in-memory SQLite for tests
    return SQLiteClient()

def test_save_and_query(db_client):
    """Test basic save and query operations."""
    # Save test data
    id = db_client.save({"test": "data"})
    assert id is not None
    
    # Query it back
    result = db_client.query("test = :value", {"value": "data"})
    assert isinstance(result, QueryResult)
    assert result.count == 1
    assert result.data[0]["test"] == "data"

def test_settings_override(db_client):
    """Test the settings override mechanism."""
    # Save with default connection
    id1 = db_client.save({"test": "settings"})
    
    # Query with connection override
    result = db_client.query(
        "test = :value", 
        {"value": "settings"},
        connection_string=":memory:"  # Should work as it's the same in-memory DB
    )
    assert result.count == 1 