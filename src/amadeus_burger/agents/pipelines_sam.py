from typing import Any, List, Dict, Optional
from datetime import datetime

from amadeus_burger.agents.base import AgentPipeline
from amadeus_burger.constants.settings import Settings

# LangGraph 相關
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

# 原本的節點、工具、條件函數
from amadeus_burger.agents.tools.knowledge_base_fetcher_tool import knowledge_base_fetcher_tool
from amadeus_burger.agents.nodes.knowledge_base_node import knowledge_base_node
from amadeus_burger.agents.nodes.final_answer_node import final_answer_node
from amadeus_burger.agents.nodes.curiosity_node import curiosity_node
from amadeus_burger.agents.nodes.novelty_evaluator_node import novelty_evaluator_node, route_novelty_evaluator
from amadeus_burger.agents.nodes.web_search_node import web_search_node
from amadeus_burger.agents.nodes.knowledge_ingestion_node import knowledge_ingestion_node, route_knowledge_ingestion


class AppState(Dict[str, Any]):
    """
    應用狀態 (AppState)，作為 StateGraph 在各個 Node 中流轉的共享狀態。

    欄位說明：
    ----------
    - messages (List[AIMessage])       : 用於存放所有過程中的對話記錄
    - question (str)                   : 主問題，由使用者或系統初始化輸入
    - knowledge_chunks (List[str])     : 從 KnowledgeBase 收集到的知識片段
    - subquestions (List[str])         : 透過 CuriosityNode 產生的子問題，後續用於外部查詢
    - answer_text (str)                : 最終產生的回答，將寫入資料庫或返回用戶
    - db_sql_logs (List[str])          : 模擬 SQL 操作記錄，保存執行的插入或查詢語句
    - need_more_kb (bool)              : 是否需要繼續從 KnowledgeBase 抓取資料
    - need_regenerate_subq (bool)      : 是否需要重新生成子問題 (CuriosityNode)
    - external_data (Optional[List[str]]): 外部查詢的原始結果，可能尚未格式化
    """
    messages: List[AIMessage]
    question: str
    knowledge_chunks: List[str]
    subquestions: List[str]
    answer_text: str
    db_sql_logs: List[str]
    need_more_kb: bool
    need_regenerate_subq: bool
    external_data: Optional[List[str]]


def should_continue(state: AppState) -> str:
    """
    判斷是否繼續程序執行

    Args:
        state (AppState): 當前的狀態。

    Returns:
        str: "continue" 表示繼續執行，"end" 表示結束執行。
    """
    if not state["messages"]:
        return "end"
    
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return "end"
    return "continue"


class CuriousityAgentPipeline(AgentPipeline):
    """
    好奇心驅動的 Agent Pipeline
    """

    def __init__(self, llm: str | None = None):
        super().__init__(llm)

        # 初始化狀態
        self.state: AppState = AppState(
            messages=[],
            question="",
            knowledge_chunks=[],
            subquestions=[],
            answer_text="",
            db_sql_logs=[],
            need_more_kb=True,
            need_regenerate_subq=False,
            external_data=[],
        )
        
        # 建立 LangGraph 流程
        self._setup_graph()

    def _setup_graph(self) -> None:
        """建立並編譯 StateGraph，包含節點與邏輯邊。"""
        self.memory_saver = MemorySaver()
        graph_builder = StateGraph(AppState)

        # 1) 加入節點
        graph_builder.add_node("knowledge_base_node", knowledge_base_node)
        graph_builder.add_node("final_answer_node", final_answer_node)
        graph_builder.add_node("curiosity_node", curiosity_node)
        graph_builder.add_node("novelty_evaluator_node", novelty_evaluator_node)
        graph_builder.add_node("web_search_node", web_search_node)
        graph_builder.add_node("knowledge_ingestion_node", knowledge_ingestion_node)

        # 建立工具節點（ToolNode）
        tools = [knowledge_base_fetcher_tool]
        tool_node = ToolNode(tools)
        graph_builder.add_node("action", tool_node)

        # 2) 建立節點連結與條件
        graph_builder.add_edge(START, "knowledge_base_node")
        graph_builder.add_conditional_edges(
            "knowledge_base_node",
            should_continue,
            {"continue": "action", "end": "final_answer_node"},
        )
        graph_builder.add_edge("final_answer_node", "curiosity_node")
        graph_builder.add_edge("curiosity_node", "novelty_evaluator_node")
        graph_builder.add_conditional_edges(
            "novelty_evaluator_node",
            route_novelty_evaluator,
            {"curiosity_node": "curiosity_node", "web_search_node": "web_search_node"},
        )
        graph_builder.add_edge("web_search_node", "knowledge_ingestion_node")
        graph_builder.add_conditional_edges(
            "knowledge_ingestion_node", route_knowledge_ingestion, {END: END}
        )

        # 編譯圖並設定 checkpoint
        self.graph = graph_builder.compile(checkpointer=self.memory_saver)

    def get_current_state(self) -> AppState:
        """取得目前的 pipeline state。"""
        return self.state

    def run(self, initial_input: Any) -> AppState:
        """
        執行 pipeline 流程。

        Args:
            initial_input (Any): 進入管線的第一個訊息或資料。

        Returns:
            AppState: 執行完成後的狀態。
        """
        self.state["messages"].append(initial_input)
        result_state = self.graph.invoke(self.state)
        return result_state

    def get_config(self) -> dict[str, Any]:
        """回傳管線設定資訊，可根據需要增加字段。"""
        return {
            "llm": self.llm,
            "memory_saver": "MemorySaver",
            "tools": ["knowledge_base_fetcher_tool"],
        }


# 編譯流程圖
graph = CuriousityAgentPipeline().graph