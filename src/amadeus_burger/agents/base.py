from typing import Any, TypeVar
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

def get_pipeline(pipeline_type: str, **kwargs) -> AgentPipeline:
    """Factory method for getting agent pipelines"""
    if pipeline_type == "chat":
        from .chat import ChatPipeline
        return ChatPipeline(**kwargs)
    elif pipeline_type == "researcher":
        from .researcher import ResearcherPipeline
        return ResearcherPipeline(**kwargs)
    # etc...
    raise ValueError(f"Unknown pipeline type: {pipeline_type}") 