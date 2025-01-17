"""
Metric functions for analyzing agent states.
Each function takes a state and returns a value.
"""
from typing import Any, Callable
from datetime import datetime
from amadeus_burger.db.schemas import S, Metric
from amadeus_burger.constants.enums import MetricType

class NumKnowledgeNodes(Metric):
    """Number of nodes in knowledge graph"""
    # override fields
    name: str = "知識節點數量"
    description: str = "知識圖譜中的節點數量"
    
    def calculate(self, state: S) -> int:
        """Count number of nodes in knowledge graph"""
        if not hasattr(state, "knowledge_graph"):
            self.value = 0
            return self.value
        self.value = len(state.knowledge_graph.get("nodes", []))
        return self.value


class NumKnowledgeEdges(Metric):
    """Number of edges in knowledge graph"""
    # override fields
    name: str = "知識連結數量"
    description: str = "知識圖譜中的連結數量"
    def calculate(self, state: S) -> int:
        """Count number of edges in knowledge graph"""
        if not hasattr(state, "knowledge_graph"):
            self.value = 0
            return self.value
        self.value = len(state.knowledge_graph.get("edges", []))
        return self.value

class AveragePerplexity(Metric):
    """Average perplexity of the agent"""
    # override fields
    name: str = "平均困惑度"
    description: str = "平均困惑度"
    def calculate(self, state: S) -> float:
        self.value = state.perplexity
        return self.value

metric_classes = {
    MetricType.NUM_KNOWLEDGE_NODES: NumKnowledgeNodes,
    MetricType.NUM_KNOWLEDGE_EDGES: NumKnowledgeEdges,
    MetricType.AVERAGE_PERPLEXITY: AveragePerplexity
}

def get_metric(metric: MetricType) -> Metric:
    """Get a metric instance from a metric type"""
    return metric_classes[metric]()


a = get_metric(MetricType.NUM_KNOWLEDGE_NODES)