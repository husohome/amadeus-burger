from typing import Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field
from amadeus_burger.constants.literals import DBClientTypes, CompressorTypes, MetricTypes

class SQLiteSettings(BaseModel):
    """SQLite-specific settings"""
    connection_string: str = Field(
        default="experiments.db",
        description="Default SQLite database file path"
    )
    journal_mode: str = Field(
        default="WAL",
        description="SQLite journal mode (WAL recommended for concurrent access)"
    )
    timeout: float = Field(
        default=30.0,
        description="Connection timeout in seconds"
    )

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True

class ExperimentRunnerSettings(BaseModel):
    """Settings for experiment runner behavior"""
    snapshot_interval: float | None = Field(default=5.0, description="How often to auto-snapshot (in seconds), None for manual only")
    max_snapshots: int = Field(default=1000, description="Max snapshots to keep per experiment")
    snapshot_on_metrics: bool = Field(default=True, description="Whether to snapshot on every metric record")
    collection_name: str = Field(default="experiments", description="Default collection name for experiments")
    compressor_type: CompressorTypes | None = Field(default=None, description="Type of snapshot compressor to use (json/binary/None)")
    db_client: DBClientTypes = Field(default="sqlite", description="Database client")
    db_client_params: dict[str, Any] = Field(default={}, description="Database client parameters")
    metrics: list[MetricTypes] = Field(
        default=["知識節點數量", "知識連結數量"],
        description="Default metrics to track in experiments"
    )

class _Settings(BaseModel):
    """Global settings for amadeus-burger"""
    # LLM settings
    llm: str = Field(
        default="gpt-4",
        description="Default LLM model to use"
    )
    temperature: float = Field(
        default=0.7,
        description="Default temperature for LLM calls"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Max tokens for LLM responses"
    )
    
    # Memory settings
    memory_backend: str = Field(
        default="sqlite",
        description="Memory storage backend (sqlite, json, mongo)"
    )
    memory_size: int = Field(
        default=1000,
        description="Maximum number of memories to keep"
    )
    
    # Database settings
    sqlite: SQLiteSettings = Field(
        default_factory=SQLiteSettings,
        description="SQLite-specific settings"
    )
    
    # Experiment settings
    experiment_runner: ExperimentRunnerSettings = Field(
        default_factory=ExperimentRunnerSettings,
        description="Experiment runner settings"
    )
    
    # Debug settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Add experiment runner settings
    experiment_runner: ExperimentRunnerSettings = ExperimentRunnerSettings()
    
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True
    
Settings = _Settings()
