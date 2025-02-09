"""
Database clients for easy CRUD operations.

Basic usage:
    from amadeus_burger.db import SQLiteClient, QueryResult
    
    db = SQLiteClient("my_db.sqlite")
    result = db.query("status = :status", {"status": "active"})
    print(f"Found {result.count} records")
"""

# Re-export main interfaces
from .schemas import QueryResult
from .base import DBClient

# Re-export all clients
from .clients import SQLiteClient


__all__ = [
    # Core interfaces
    "DBClient",
    "QueryResult",
    
    # Available clients
    "SQLiteClient",
]

# Optional: version info
__version__ = "0.1.0"