import sqlite3
import json
import uuid
from typing import Optional
from schemas import QueryResult
from amadeus_burger import Settings
from amadeus_burger.constants.literals import DBClientTypes
from abc import ABC, abstractmethod

class DBClient(ABC):
    @abstractmethod
    def upsert(self, data: dict[str, any], query_str: str | None = None, params: dict[str, any] | None = None) -> str:
        """Upsert operation - insert if not exists, update if exists
        Args:
            data: The data to upsert
            query_str: Optional query string to identify existing record
            params: Optional parameters for the query string
        Returns:
            str: ID of the upserted record
        Examples:
            >>> # Insert new record
            >>> id = client.upsert({"name": "test", "value": 123})
            >>> # Update existing record
            >>> id = client.upsert({"value": 456}, "id = :id", {"id": "123"})
        """
        pass

    @abstractmethod
    def query(self, query_str: str, params: dict[str, any] | None = None) -> QueryResult:
        """Query database with simple query string
        Examples:
            >>> result = client.query("status = :status", {"status": "completed"})
            >>> print(f"Found {result.count} records")
        """
        pass
    
    @abstractmethod
    def delete(self, delete_str: str, params: dict[str, any] | None = None) -> int:
        """Delete records matching the delete string
        Returns:
            int: Number of records deleted
        Examples:
            >>> count = client.delete("status = :status", {"status": "failed"})
            >>> print(f"Deleted {count} failed records")
        """
        pass


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
    
    def upsert(self, data: dict[str, any], query_str: str | None = None, params: dict[str, any] | None = None) -> str:
        """Upsert operation - insert if not exists, update if exists"""
        with sqlite3.connect(self.connection_string) as conn:
            if query_str is None:
                # Insert new record
                id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO data (id, content) VALUES (?, ?)",
                    (id, json.dumps(data))
                )
                return id
            else:
                # Try to update existing record
                where_clause = query_str.replace(".", "->")
                content_updates = []
                for key, value in data.items():
                    content_updates.append(f"json_set(content, '$.{key}', json(?))")
                
                update_values = [json.dumps(v) for v in data.values()]
                update_sql = f"""
                    UPDATE data 
                    SET content = {' , '.join(content_updates)}
                    WHERE {where_clause}
                """
                
                cursor = conn.execute(update_sql, update_values + list(params.values()))
                
                if cursor.rowcount == 0:
                    # No existing record found, insert new one
                    id = params.get("id", str(uuid.uuid4()))
                    full_data = {"id": id, **data}
                    conn.execute(
                        "INSERT INTO data (id, content) VALUES (?, ?)",
                        (id, json.dumps(full_data))
                    )
                    return id
                else:
                    # Return the ID of the updated record
                    cursor = conn.execute(f"SELECT id FROM data WHERE {where_clause}", params)
                    return cursor.fetchone()[0]
    
    def query(self, query_str: str, params: Optional[dict[str, any]] = None) -> QueryResult:
        """Query with optional function-level connection override"""
        with sqlite3.connect(
            self.connection_string,
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

class Neo4jClient(DBClient):
    """Neo4j client implementation"""
    
    def __init__(self, connection_string: str | None = None):
        """Initialize Neo4j client with optional connection override
        Args:
            connection_string: Override the default/settings connection string
        """
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError("neo4j-driver package is required for Neo4jClient")
            
        # Class-level override or settings default
        self.connection_string = connection_string or Settings.neo4j.connection_string
        self._driver = GraphDatabase.driver(
            self.connection_string,
            auth=(Settings.neo4j.username, Settings.neo4j.password)
        )
        self._init_db()
    
    def _init_db(self):
        """Initialize database constraints and indexes"""
        with self._driver.session() as session:
            # Create constraints for unique IDs
            session.run("""
                CREATE CONSTRAINT IF NOT EXISTS FOR (n:Record)
                REQUIRE n.id IS UNIQUE
            """)
    
    def upsert(self, data: dict[str, any], query_str: str | None = None, params: dict[str, any] | None = None) -> str:
        """Upsert operation - insert if not exists, update if exists"""
        with self._driver.session() as session:
            if query_str is None:
                # Insert new record
                result = session.run("""
                    CREATE (n:Record)
                    SET n = $data, n.id = randomUUID()
                    RETURN n.id as id
                """, {"data": data})
                return result.single()["id"]
            else:
                # Try to update existing record
                # Convert simple query string to Cypher
                where_clause = self._convert_to_cypher_where(query_str)
                
                result = session.run("""
                    MATCH (n:Record)
                    WHERE """ + where_clause + """
                    SET n += $data
                    RETURN n.id as id
                """, {**params, "data": data})
                
                record = result.single()
                if record:
                    return record["id"]
                
                # No existing record found, insert new one
                result = session.run("""
                    CREATE (n:Record)
                    SET n = $data, n.id = $id
                    RETURN n.id as id
                """, {
                    "data": data,
                    "id": params.get("id", str(uuid.uuid4()))
                })
                return result.single()["id"]
    
    def query(self, query_str: str, params: dict[str, any] | None = None) -> QueryResult:
        """Query database with simple query string"""
        with self._driver.session() as session:
            # Convert simple query string to Cypher
            where_clause = self._convert_to_cypher_where(query_str)
            
            result = session.run("""
                MATCH (n:Record)
                WHERE """ + where_clause + """
                RETURN n
            """, params or {})
            
            data = [dict(record["n"]) for record in result]
            
            return QueryResult(
                data=data,
                count=len(data),
                query=query_str,
                params=params
            )
    
    def delete(self, delete_str: str, params: dict[str, any] | None = None) -> int:
        """Delete records matching the delete string"""
        with self._driver.session() as session:
            # Convert simple query string to Cypher
            where_clause = self._convert_to_cypher_where(delete_str)
            
            result = session.run("""
                MATCH (n:Record)
                WHERE """ + where_clause + """
                WITH n, n.id as id
                DETACH DELETE n
                RETURN count(id) as count
            """, params or {})
            
            return result.single()["count"]
    
    def _convert_to_cypher_where(self, query_str: str) -> str:
        """Convert simple query string to Cypher WHERE clause
        
        Examples:
            "status = :status" -> "n.status = $status"
            "age > :min_age" -> "n.age > $min_age"
        """
        # Replace : with $ for Neo4j parameters
        clause = query_str.replace(":", "$")
        # Add n. prefix to properties
        for word in query_str.split():
            if "." not in word and word not in ["AND", "OR", "NOT", "IN"]:
                clause = clause.replace(word, f"n.{word}")
        return clause
    
    def close(self):
        """Close the database connection"""
        self._driver.close()

# write a function to get client 
def get_client(db_client: DBClientTypes | None = None, **kwargs) -> DBClient:
    db_client = db_client or Settings.experiment_runner.db_client
    if db_client == "sqlite":
        return SQLiteClient(**kwargs)
    elif db_client == "json":
        return JSONFileClient(**kwargs)
    elif db_client == "mongo":
        return MongoClient(**kwargs)
    elif db_client == "neo4j":
        return Neo4jClient(**kwargs)
    else:
        raise ValueError(f"Invalid database client: {db_client}")
