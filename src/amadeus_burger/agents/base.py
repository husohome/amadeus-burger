from typing import Any, Sequence
from datetime import datetime
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from amadeus_burger.constants.settings import Settings

class AgentPipeline:
    def __init__(self, llm: str | None = None):
        self.llm = llm or Settings.llm
        
    def get_current_state(self) -> dict[str, Any]:
        """Get current state of the pipeline"""
        raise NotImplementedError
        
    def run(self, initial_input: Any) -> Any:
        raise NotImplementedError
        
    def get_config(self) -> dict[str, Any]:
        raise NotImplementedError

