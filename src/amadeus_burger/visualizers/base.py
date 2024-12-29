"""
Base interface for visualization components.
"""
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic
from typing_extensions import TypedDict

from amadeus_burger.agents.base import AgentState

# Type for visualization configuration
class VisualizerConfig(TypedDict):
    """Configuration options for visualizers"""
    width: int  # Width of the visualization
    height: int  # Height of the visualization
    theme: str  # Visual theme (e.g., "light", "dark")
    interactive: bool  # Whether visualization is interactive
    export_format: str  # Format for export (e.g., "png", "html")

# Type variable for visualization data
V = TypeVar('V')

class Visualizer(ABC, Generic[V]):
    """Base interface for all visualizers"""
    
    def __init__(self, config: VisualizerConfig | None = None):
        self.config = config or VisualizerConfig(
            width=800,
            height=600,
            theme="light",
            interactive=True,
            export_format="html"
        )
    
    @abstractmethod
    def process_data(self, state: AgentState) -> V:
        """Process agent state into visualization-ready data
        
        Args:
            state: Current agent state to visualize
            
        Returns:
            Processed data ready for visualization
        """
        pass
    
    @abstractmethod
    def render(self, data: V) -> Any:
        """Render the visualization
        
        Args:
            data: Processed data to visualize
            
        Returns:
            The rendered visualization (format depends on implementation)
        """
        pass
    
    @abstractmethod
    def export(self, data: V, path: str) -> None:
        """Export visualization to file
        
        Args:
            data: Processed data to visualize
            path: Path to save the visualization
        """
        pass
    
    def visualize(self, state: AgentState) -> Any:
        """Process and render visualization in one step
        
        Args:
            state: Agent state to visualize
            
        Returns:
            The rendered visualization
        """
        data = self.process_data(state)
        return self.render(data) 