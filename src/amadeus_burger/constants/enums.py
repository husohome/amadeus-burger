from enum import Enum, auto
from typing import Union

class CompressorType(Enum):
    JSON = "json"
    BINARY = "binary"

class DBClientType(Enum):
    SQLITE = "sqlite"
    JSON = "json"
    MONGO = "mongo"
    NEO4J = "neo4j"

class PipelineType(Enum):
    STRUCTURED_LEARNING = "structured_learning"
    ADAPTIVE_LEARNING = "adaptive_learning"

class VisualizerType(Enum):
    KNOWLEDGE_GRAPH = "knowledge_graph"
    LEARNING_PROGRESS = "learning_progress"
    CONFIDENCE_HEATMAP = "confidence_heatmap"
    TOPIC_NETWORK = "topic_network"

class MetricType(Enum):
    NUM_KNOWLEDGE_NODES = "num_knowledge_nodes"
    NUM_KNOWLEDGE_EDGES = "num_knowledge_edges"
    NODE_RELEVANCE = "node_relevance"
    AVERAGE_PERPLEXITY = "average_perplexity"


