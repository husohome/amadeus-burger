from typing import Any, TypeVar, Generic
from typing_extensions import TypedDict
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from abc import ABC, abstractmethod

S = TypeVar("S")

class Metric(BaseModel, ABC):
    """A metric with its metadata and value"""
    name: str  # e.g. "知識節點數量"
    description: str  # e.g. "Number of nodes in knowledge graph"
    value: Any | None = None  # The actual metric value
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))  # When the metric was recorded

    class Config:
        arbitrary_types_allowed = True
    
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
    
    class Config:
        arbitrary_types_allowed = True


class ExperimentRecord(BaseModel, Generic[S]):
    """Experiment record that can work with any LangGraph state"""
    id: UUID = Field(default_factory=uuid4)
    state: S
    name: str
    start_time: datetime
    end_time: datetime | None
    pipeline_type: str
    pipeline_config: dict[str, Any]
    metrics: list[Metric] = []  # All metrics recorded during the experiment
    snapshots: list[Snapshot] = []
    status: str
    initial_input: Any
    
    class Config:
        arbitrary_types_allowed = True


class QueryResult(BaseModel):
    """Generic container for any query results"""
    data: list[dict[str, Any]]
    count: int = Field(description="Number of results returned")
    query: str = Field(description="Original query string")
    params: dict[str, any] | None = Field(default=None, description="Query parameters used")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        arbitrary_types_allowed = True
