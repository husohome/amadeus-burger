from typing import TypeVar, Generic, Any, _TypedDictMeta
from typing_extensions import TypedDict
from datetime import datetime
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4
from abc import ABC, abstractmethod
# Allow for custom state types
S = TypeVar('State', bound=_TypedDictMeta)

class Metric(BaseModel, ABC):
    """A metric with its metadata and value"""
    name: str  # e.g. "知識節點數量"
    description: str  # e.g. "Number of nodes in knowledge graph"
    value: Any | None = None  # The actual metric value
    timestamp: datetime = datetime.utcnow()  # When the metric was recorded
    
    @abstractmethod
    def calculate(self, state: S) -> Any:
        """Calculate the metric value"""
        pass
    

class Snapshot(BaseModel, Generic[S]):
    """Snapshot of agent state at a point in time"""
    state: S | None = None
    timestamp: datetime
    compressed_data: bytes | None = None
    compression_type: str | None = None
    metrics: list[Metric] = []  # List of metrics at this snapshot

class ExperimentRecord(BaseModel, Generic[S]):
    """Experiment record that can work with any LangGraph state"""
    id: UUID = Field(default_factory=uuid4)
    state: S  # Current LangGraph state
    name: str
    start_time: datetime
    end_time: datetime | None
    pipeline_type: str
    pipeline_config: dict[str, Any]
    metrics: list[Metric] = []  # All metrics recorded during the experiment
    snapshots: list[Snapshot[S]] = []
    status: str
    initial_input: Any
class QueryResult(BaseModel):
    """Generic container for any query results"""
    data: list[dict[str, any]]
    count: int = Field(description="Number of results returned")
    query: str = Field(description="Original query string")
    params: dict[str, any] | None = Field(default=None, description="Query parameters used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

