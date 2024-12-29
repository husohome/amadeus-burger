from typing import TypeVar, Generic, Any, _TypedDictMeta
from typing_extensions import TypedDict
from datetime import datetime
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4

# Allow for custom state types
S = TypeVar('State', bound=_TypedDictMeta)

class Snapshot(BaseModel, Generic[S]):
    """Snapshot of a LangGraph state with timestamp"""
    timestamp: datetime = Field(default_factory=datetime.now())
    state: S  # LangGraph state

class ExperimentRecord(BaseModel, Generic[S]):
    """Experiment record that can work with any LangGraph state"""
    id: UUID = Field(default_factory=uuid4)
    state: S  # Current LangGraph state
    name: str
    start_time: datetime
    end_time: datetime | None
    pipeline_type: str
    pipeline_config: dict[str, Any]
    metrics: dict[str, Any]
    snapshots: list[Snapshot[S]]  # Timestamped state snapshots typcially this should be a typed dict
    initial_input: Any


class QueryResult(BaseModel):
    """Generic container for any query results"""
    data: list[dict[str, any]]
    count: int = Field(description="Number of results returned")
    query: str = Field(description="Original query string")
    params: dict[str, any] | None = Field(default=None, description="Query parameters used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)