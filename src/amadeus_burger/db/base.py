from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .schemas import QueryResult

class DBClient(ABC):
    @abstractmethod
    def save(self, data: dict[str, any]) -> str:
        """Save operation
        Returns:
            str: ID of the saved record
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
    def update(self, update_str: str, params: dict[str, any] | None = None) -> int:
        """Update records matching the update string
        Returns:
            int: Number of records updated
        Examples:
            >>> count = client.update("status = 'failed' WHERE id = :id", {"id": "123"})
            >>> print(f"Updated {count} records")
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