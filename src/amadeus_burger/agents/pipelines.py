"""
LangGraph-based agent pipeline implementations for knowledge learning.
"""
from typing import Any, Literal, TypedDict, NotRequired, Sequence
from datetime import datetime, UTC
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langgraph.graph import END, StateGraph
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults

from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_community.tools import WikipediaQueryRun
from amadeus_burger.constants.enums import PipelineType
from amadeus_burger.constants.settings import Settings
from langchain.tools import BaseTool
import requests
import os

class PerplexitySearchTool(BaseTool):
    """Tool that queries Perplexity AI API"""
    name: str = "perplexity_search"
    description: str = "Search for information using Perplexity AI"

    def _run(self, query: str) -> str:
        headers = {
            "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": "Be precise and concise."},
                {"role": "user", "content": query}
            ],
            "temperature": 0.2,
            "top_p": 0.9
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        return response.json()["choices"][0]["message"]["content"]

    def _arun(self, query: str) -> str:
        raise NotImplementedError("Async not implemented")

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



class ExampleAgentState(TypedDict):
    """Example agent state with common fields and proper typing"""
    # Required fields
    messages: list[BaseMessage]  # Chat history
    current_step: str  # Current step in the graph
    timestamp: datetime  # Last update time
    
    # Optional fields with specific types
    status: NotRequired[Literal["running", "completed", "failed"]]
    error: NotRequired[str]  # Error message if any
    iterations: NotRequired[int]  # Number of iterations
    tool_outputs: NotRequired[list[dict[str, Any]]]  # Tool execution results
    
    # Knowledge learning specific fields
    knowledge_base: NotRequired[dict[str, Any]]  # Accumulated knowledge
    learning_objectives: NotRequired[list[str]]  # Learning goals
    understanding_gaps: NotRequired[list[str]]  # Identified knowledge gaps
    confidence_scores: NotRequired[dict[str, float]]  # Confidence in different topics
    sources: NotRequired[list[dict[str, str]]]  # Reference sources
    quiz_results: NotRequired[list[dict[str, Any]]]  # Self-assessment results
    
    # Metadata can store any additional info
    metadata: NotRequired[dict[str, Any]]

class StructuredLearningPipeline(AgentPipeline):
    """Plan-and-execute style agent for structured knowledge acquisition"""
    
    def __init__(self, llm: str | None = None):
        super().__init__(llm)
        self.planner = ChatOpenAI(model="gpt-4-turbo-preview")
        self.learner = ChatAnthropic(model="claude-3-haiku")
        self.tools = [
            PerplexitySearchTool(),
            WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
        ]
        self.state = ExampleAgentState(
            messages=[],
            current_step="plan",
            timestamp=datetime.now(UTC),
            status="running",
            iterations=0,
            tool_outputs=[],
            knowledge_base={},
            learning_objectives=[],
            understanding_gaps=[],
            confidence_scores={},
            sources=[],
            quiz_results=[],
            metadata={}
        )
        self._setup_graph()
        
    def _setup_graph(self):
        """Setup the learning computation graph"""
        workflow = StateGraph(ExampleAgentState)
        
        # Add nodes for learning pipeline
        workflow.add_node("analyze", self._analyze_topic)
        workflow.add_node("plan", self._create_learning_plan)
        workflow.add_node("research", self._gather_information) 
        workflow.add_node("synthesize", self._synthesize_knowledge)
        workflow.add_node("validate", self._validate_understanding)
        
        # Build learning flow
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "plan")
        workflow.add_edge("plan", "research")
        workflow.add_edge("research", "synthesize")
        workflow.add_conditional_edges(
            "synthesize",
            self._should_continue_learning,
            {
                "research": "research",  # Need more information
                "validate": "validate",  # Ready to validate
                "plan": "plan"  # Need to revise plan
            }
        )
        workflow.add_edge("validate", END)
        
        self.graph = workflow.compile()
    
    def _analyze_topic(self, state: ExampleAgentState) -> ExampleAgentState:
        """Analyze the learning topic and identify key areas"""
        # Implementation here
        return state
        
    def _create_learning_plan(self, state: ExampleAgentState) -> ExampleAgentState:
        """Create structured learning plan with objectives"""
        # Implementation here
        return state
        
    def _gather_information(self, state: ExampleAgentState) -> ExampleAgentState:
        """Research and gather information from various sources"""
        # Implementation here
        return state
        
    def _synthesize_knowledge(self, state: ExampleAgentState) -> ExampleAgentState:
        """Synthesize gathered information into coherent knowledge"""
        # Implementation here
        return state
        
    def _validate_understanding(self, state: ExampleAgentState) -> ExampleAgentState:
        """Validate understanding through self-assessment"""
        # Implementation here
        return state
        
    def _should_continue_learning(self, state: ExampleAgentState) -> str:
        """Determine next learning step based on current understanding"""
        if len(state["understanding_gaps"]) > 0:
            return "research"
        if all(score > 0.8 for score in state["confidence_scores"].values()):
            return "validate"
        return "plan"
    
    def get_current_state(self) -> ExampleAgentState:
        return self.state
        
    def run(self, initial_input: Any) -> Any:
        self.state["messages"].append(initial_input)
        return self.graph.invoke(self.state)
        
    def get_config(self) -> dict[str, Any]:
        return {
            "llm": self.llm,
            "planner": "gpt-4-turbo-preview",
            "learner": "claude-3-haiku",
            "tools": ["perplexity_search", "wikipedia"]
        }

class AdaptiveLearningPipeline(AgentPipeline):
    """Self-correcting knowledge refinement pipeline"""
    
    def __init__(self, llm: str | None = None):
        super().__init__(llm)
        self.model = ChatOpenAI(model="gpt-4-turbo-preview")
        self.state = ExampleAgentState(
            messages=[],
            current_step="explore",
            timestamp=datetime.now(UTC),
            status="running",
            iterations=0,
            tool_outputs=[],
            knowledge_base={},
            learning_objectives=[],
            understanding_gaps=[],
            confidence_scores={},
            sources=[],
            quiz_results=[],
            metadata={
                "learning_path": []
            }
        )
        self._setup_graph()
        
    def _setup_graph(self):
        """Setup the adaptive learning graph"""
        workflow = StateGraph(ExampleAgentState)
        
        # Add nodes for adaptive learning
        workflow.add_node("explore", self._explore_knowledge)
        workflow.add_node("assess", self._assess_understanding)
        workflow.add_node("refine", self._refine_knowledge)
        
        # Build adaptive learning flow
        workflow.set_entry_point("explore")
        workflow.add_edge("explore", "assess")
        workflow.add_conditional_edges(
            "assess",
            self._decide_next_step,
            {
                "end": END,
                "refine": "refine",
                "explore": "explore"
            }
        )
        workflow.add_edge("refine", "explore")
        
        self.graph = workflow.compile()
    
    def _explore_knowledge(self, state: ExampleAgentState) -> ExampleAgentState:
        """Explore and expand current knowledge"""
        # Implementation here
        return state
        
    def _assess_understanding(self, state: ExampleAgentState) -> ExampleAgentState:
        """Assess current understanding and identify gaps"""
        # Implementation here
        return state
        
    def _refine_knowledge(self, state: ExampleAgentState) -> ExampleAgentState:
        """Refine and correct knowledge based on assessment"""
        # Implementation here
        return state
        
    def _decide_next_step(self, state: ExampleAgentState) -> str:
        """Decide next step based on learning progress"""
        if state["iterations"] >= 5:
            return "end"
        if len(state["understanding_gaps"]) > 0:
            return "refine"
        if min(state["confidence_scores"].values(), default=0) < 0.9:
            return "explore"
        return "end"
    
    def get_current_state(self) -> ExampleAgentState:
        return self.state
        
    def run(self, initial_input: Any) -> Any:
        self.state["messages"].append(initial_input)
        return self.graph.invoke(self.state)
        
    def get_config(self) -> dict[str, Any]:
        return {
            "llm": self.llm,
            "model": "gpt-4-turbo-preview",
            "max_iterations": 5
        }


def get_pipeline(pipeline_type: PipelineType | None = None, **kwargs) -> AgentPipeline:
    """Factory method for getting agent pipelines
    
    Args:
        pipeline_type: Type of pipeline to create
            - "structured_learning": Plan-based structured learning pipeline
            - "adaptive_learning": Self-correcting adaptive learning pipeline
        **kwargs: Additional arguments to pass to the pipeline constructor
        
    Returns:
        AgentPipeline: The constructed pipeline instance
        
    Raises:
        ValueError: If pipeline_type is not recognized
    """
    pipeline_type = pipeline_type or "structured_learning"  # Default pipeline
    
    pipelines: dict[PipelineType, type[AgentPipeline]] = {
        PipelineType.STRUCTURED_LEARNING: StructuredLearningPipeline,
        PipelineType.ADAPTIVE_LEARNING: AdaptiveLearningPipeline
    }
    
    if pipeline_type not in pipelines:
        raise ValueError(
            f"Unknown pipeline type: {pipeline_type}. "
            f"Available types: {', '.join(pipelines.keys())}"
        )
        
    return pipelines[pipeline_type](**kwargs) 