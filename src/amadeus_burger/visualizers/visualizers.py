"""
Visualizer implementations for different visualization types.
"""
from typing import Any, Dict, List, Tuple
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from networkx.drawing.layout import spring_layout

from amadeus_burger.db.schemas import S
from amadeus_burger.constants.enums import VisualizerTypes
from .base import Visualizer, VisualizerConfig

# Type aliases for processed data
KnowledgeGraphData = Tuple[nx.Graph, Dict[str, Dict[str, Any]]]
LearningProgressData = List[Dict[str, Any]]
ConfidenceData = Dict[str, float]
TopicNetworkData = nx.Graph

class KnowledgeGraphVisualizer(Visualizer[KnowledgeGraphData]):
    """Visualizes knowledge as an interactive graph"""
    
    def process_data(self, state: S) -> KnowledgeGraphData:
        """Convert knowledge base to graph structure"""
        G = nx.Graph()
        node_attrs = {}
        
        # Process knowledge base into graph
        knowledge = state.get("knowledge_base", {})
        for topic, info in knowledge.items():
            G.add_node(topic)
            node_attrs[topic] = {
                "confidence": state.get("confidence_scores", {}).get(topic, 0),
                "status": "learned" if topic not in state.get("understanding_gaps", []) else "gap"
            }
            
            # Add relationships
            for related in info.get("related_topics", []):
                G.add_edge(topic, related)
                
        return G, node_attrs
    
    def render(self, data: KnowledgeGraphData) -> go.Figure:
        """Render interactive knowledge graph"""
        G, node_attrs = data
        pos = spring_layout(G)
        
        # Create figure
        fig = go.Figure()
        
        # Add edges
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        ))
        
        # Add nodes
        node_x, node_y = [], []
        node_colors = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_colors.append(node_attrs[node]["confidence"])
        
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hovertext=list(G.nodes()),
            marker=dict(
                size=10,
                color=node_colors,
                colorscale='Viridis',
                showscale=True
            )
        ))
        
        # Update layout
        fig.update_layout(
            title='Knowledge Graph',
            showlegend=False,
            width=self.config["width"],
            height=self.config["height"],
            template=self.config["theme"]
        )
        
        return fig
    
    def export(self, data: KnowledgeGraphData, path: str) -> None:
        """Export visualization to file"""
        fig = self.render(data)
        fig.write_html(path) if self.config["export_format"] == "html" else fig.write_image(path)

class LearningProgressVisualizer(Visualizer[LearningProgressData]):
    """Visualizes learning progress over time"""
    
    def process_data(self, state: S) -> LearningProgressData:
        """Extract learning progress metrics"""
        quiz_results = state.get("quiz_results", [])
        return [
            {
                "timestamp": result["timestamp"],
                "score": result["score"],
                "topic": result["topic"]
            }
            for result in quiz_results
        ]
    
    def render(self, data: LearningProgressData) -> go.Figure:
        """Render learning progress chart"""
        fig = px.line(
            data,
            x="timestamp",
            y="score",
            color="topic",
            title="Learning Progress Over Time"
        )
        
        fig.update_layout(
            width=self.config["width"],
            height=self.config["height"],
            template=self.config["theme"]
        )
        
        return fig
    
    def export(self, data: LearningProgressData, path: str) -> None:
        """Export visualization to file"""
        fig = self.render(data)
        fig.write_html(path) if self.config["export_format"] == "html" else fig.write_image(path)

def get_visualizer(
    visualizer_type: VisualizerTypes | None = None,
    config: VisualizerConfig | None = None
) -> Visualizer:
    """Factory method for getting visualizers
    
    Args:
        visualizer_type: Type of visualizer to create
            - "knowledge_graph": Interactive knowledge graph visualization
            - "learning_progress": Learning progress over time
            - "confidence_heatmap": Confidence scores heatmap
            - "topic_network": Topic relationship network
        config: Optional configuration for the visualizer
        
    Returns:
        Visualizer: The constructed visualizer instance
        
    Raises:
        ValueError: If visualizer_type is not recognized
    """
    visualizer_type = visualizer_type or "knowledge_graph"  # Default visualizer
    
    visualizers: dict[VisualizerTypes, type[Visualizer]] = {
        "knowledge_graph": KnowledgeGraphVisualizer,
        "learning_progress": LearningProgressVisualizer,
        # Add other visualizers as implemented
    }
    
    if visualizer_type not in visualizers:
        raise ValueError(
            f"Unknown visualizer type: {visualizer_type}. "
            f"Available types: {', '.join(visualizers.keys())}"
        )
        
    return visualizers[visualizer_type](config) 