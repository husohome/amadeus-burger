from typing import Literal

# Literal types for function parameters
DBClientTypes = Literal["sqlite", "json", "mongo", "neo4j"]
CompressorTypes = Literal["json", "binary"]
PipelineTypes = Literal["structured_learning", "adaptive_learning"]
VisualizerTypes = Literal[
    "knowledge_graph",  # For visualizing knowledge relationships
    "learning_progress",  # For tracking learning metrics over time
    "confidence_heatmap",  # For showing confidence across topics
    "topic_network"  # For showing topic relationships
]
MetricTypes = Literal[
    "知識節點數量",  # Number of knowledge nodes
    "知識連結數量",  # Number of knowledge edges
    "節點相關度",  # Node relevance to query
    "平均困惑度"  # Average perplexity
]
