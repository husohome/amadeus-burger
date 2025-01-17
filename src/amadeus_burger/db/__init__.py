"""
Database clients for easy CRUD operations.

Basic usage:
    from amadeus_burger.db import SQLiteClient, QueryResult
    
    db = SQLiteClient("my_db.sqlite")
    result = db.query("status = :status", {"status": "active"})
    print(f"Found {result.count} records")
"""

from amadeus_burger.db.schemas import *
from amadeus_burger.db.clients import *