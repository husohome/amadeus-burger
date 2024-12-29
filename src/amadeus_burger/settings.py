from typing import Optional
from pydantic import BaseModel, Field
from functools import lru_cache

class _Settings(BaseModel):
    """Global settings for amadeus-burger"""
    # LLM settings
    llm: str = Field(default="gpt-4", description="Default LLM model to use")
    temperature: float = Field(default=0.7, description="Default temperature for LLM calls")
    
    # Database settings
    db_connection: str = Field(default="experiments.db", description="Default database connection string")
    
    # Memory settings
    memory_backend: str = Field(default="sqlite", description="Memory storage backend")
    
    # Other global settings...
    max_tokens: Optional[int] = Field(default=None, description="Max tokens for LLM responses")
    debug: bool = Field(default=False, description="Enable debug mode")

    class Config:
        validate_assignment = True  # Validate when settings are changed

# Global singleton instance
Settings = _Settings()

# Optional: provide a way to reset to defaults
def reset_settings():
    global Settings
    Settings = _Settings()

# Optional: provide a way to get settings with caching
@lru_cache()
def get_settings():
    return Settings 