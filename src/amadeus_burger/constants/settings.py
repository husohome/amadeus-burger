from typing import Optional, Any
from pydantic import BaseModel, Field

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
    experiment_name: str = Field(
        default="default",
        description="Current experiment name"
    )
    experiment_tags: list[str] = Field(
        default_factory=list,
        description="Tags for the current experiment"
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

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True

Settings = _Settings() 