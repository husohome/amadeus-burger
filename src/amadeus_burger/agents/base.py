from typing import Any, Sequence
from datetime import datetime
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict
from abc import ABC, abstractmethod
from amadeus_burger.constants.settings import Settings

class AgentPipeline(ABC):
    def __init__(self, llm: str | None = None):
        self.llm = llm or Settings.llm
        
    @abstractmethod
    def get_current_state(self) -> dict[str, Any]:
        """Get current state of the pipeline"""
        pass
        
    @abstractmethod
    def run(self, initial_input: Any) -> Any:
        pass
        
    @abstractmethod
    def get_config(self) -> dict[str, Any]:
        pass

