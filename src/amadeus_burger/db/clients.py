import sqlite3
import json
import uuid
from typing import Optional
from base import DBClient
from schemas import QueryResult
from amadeus_burger import Settings

class SQLiteClient(DBClient):
    def __init__(self, connection_string: str | None = None):
        """Initialize SQLite client with optional connection override
        Args:
            connection_string: Override the default/settings connection string
        """
        # Class-level override or settings default
        self.connection_string = connection_string or Settings.sqlite.connection_string
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(
            self.connection_string,
            timeout=Settings.sqlite.timeout
        ) as conn:
            # Apply SQLite optimizations from settings
            conn.execute(f"PRAGMA journal_mode={Settings.sqlite.journal_mode}")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data (
                    id TEXT PRIMARY KEY,
                    content JSON
                )
            """)
    
    def save(self, data: dict[str, any]) -> str:
        id = str(uuid.uuid4())
        with sqlite3.connect(self.connection_string) as conn:
            conn.execute(
                "INSERT INTO data (id, content) VALUES (?, ?)",
                (id, json.dumps(data))
            )
        return id
    
    def query(self, query_str: str, params: Optional[dict[str, any]] = None, 
             connection_string: str | None = None) -> QueryResult:
        """Query with optional function-level connection override"""
        # Priority: function param > instance var > settings
        conn_str = connection_string or self.connection_string or Settings.sqlite.connection_string
        
        with sqlite3.connect(
            conn_str,
            timeout=Settings.sqlite.timeout
        ) as conn:
            where_clause = query_str.replace(".", "->")
            sql = f"SELECT id, content FROM data WHERE {where_clause}"
            
            cursor = conn.execute(sql, params or {})
            rows = cursor.fetchall()
            
            data = [
                {**json.loads(content), "id": id}
                for id, content in rows
            ]
            
            return QueryResult(
                data=data,
                count=len(data),
                query=query_str,
                params=params
            )
    
    def update(self, update_str: str, params: Optional[dict[str, any]] = None) -> int:
        with sqlite3.connect(self.connection_string) as conn:
            cursor = conn.execute(
                f"UPDATE data SET {update_str}",
                params or {}
            )
            return cursor.rowcount
    
    def delete(self, delete_str: str, params: Optional[dict[str, any]] = None) -> int:
        with sqlite3.connect(self.connection_string) as conn:
            cursor = conn.execute(
                f"DELETE FROM data WHERE {delete_str}",
                params or {}
            )
            return cursor.rowcount

# Can add other clients in the same file
class JSONFileClient(DBClient):
    # Implementation here
    pass

class MongoClient(DBClient):
    # Implementation here
    pass
