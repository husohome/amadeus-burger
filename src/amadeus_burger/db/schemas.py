from pydantic import BaseModel, Field
from datetime import datetime

class QueryResult(BaseModel):
    """Generic container for any query results"""
    data: list[dict[str, any]]
    count: int = Field(description="Number of results returned")
    query: str = Field(description="Original query string")
    params: dict[str, any] | None = Field(default=None, description="Query parameters used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

