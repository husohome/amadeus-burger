"""
Metric functions for analyzing agent states.
Each function takes a state and returns a value.
"""
from typing import Any, Callable
from datetime import datetime
from amadeus_burger.db.schemas import S, Metric
from amadeus_burger.constants.literals import MetricTypes

class NumKnowledgeNodes(Metric):
    """Number of nodes in knowledge graph"""
    # override fields
    name = "知識節點數量"
    description = "知識圖譜中的節點數量"
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
    name = "知識連結數量"
    description = "知識圖譜中的連結數量"
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
    name = "平均困惑度"
    description = "平均困惑度"
    def calculate(self, state: S) -> float:
        self.value = state.perplexity
        return self.value

metric_classes = {
    MetricTypes.NUM_KNOWLEDGE_NODES: NumKnowledgeNodes,
    MetricTypes.NUM_KNOWLEDGE_EDGES: NumKnowledgeEdges,
    MetricTypes.AVERAGE_PERPLEXITY: AveragePerplexity
}

def get_metric(metric: MetricTypes) -> list[Metric]:
    """Get a list of metrics from a list of metric types"""
    return metric_classes[metric]()