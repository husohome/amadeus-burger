from typing import Any, List, Dict, Optional, TypedDict
from datetime import datetime

from amadeus_burger.agents.base import AgentPipeline
from amadeus_burger.constants.settings import Settings

# LangGraph 相關
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.errors import GraphRecursionError

# 原本的節點、工具、條件函數
from amadeus_burger.agents.tools import knowledge_base_fetcher_tool
from amadeus_burger.agents.nodes import (
    knowledge_base_node,
    final_answer_node,
    curiosity_node,
    novelty_evaluator_node, 
    web_search_node,
    knowledge_ingestion_node,
    route_knowledge_ingestion
)


class AppState(TypedDict):
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
    - thread_id (str)                  : 用於區分不同執行緒的唯一標識
    - novelty_test (bool)              : 新奇性測試有沒有過
    - loop_counter (int)                : 新增循環計數器
    """
    thread_id: str
    messages: List[AIMessage]
    question: str
    knowledge_chunks: List[str]
    query_needed: bool
    subquestions: List[str]
    answer_text: str
    db_sql_logs: List[str]
    need_more_kb: bool
    need_regenerate_subq: bool
    external_data: Optional[List[str]]
    novelty_test: bool
    loop_counter: int


# 
def should_continue_search(state) -> str:
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

def is_subquestion_novel(state) -> str:
    """添加循環終止條件"""
    if state.get("loop_counter", 0) >= 5:  # 最大循環5次
        return "end"
    if not state.get("novelty_test", False):
        return "regenerate_subq"
    return "end"

def route_knowledge_base_node(state) -> str:
    """
    根據 state["query_needed"] 判斷：
      - 如果為 True，則返回工具節點名稱 (例如 "knowledge_query_tool")，
        讓後續流程執行資料庫查詢工具。
      - 如果為 False，則返回下一個節點名稱 (例如 "final_answer_node")。

    Returns:
        str: 下一個節點的識別字串
    """
    if state.get("query_needed", False):
        return "knowledge_query_tool"
    return "final_answer_node"



class CuriousityAgentPipeline(AgentPipeline):
    """
    好奇心驅動的 Agent Pipeline
    """

    def __init__(self, llm: str | None = None):
        super().__init__(llm)

        # 初始化狀態時加入 thread_id
        self.state = AppState(
            thread_id="main_thread",
            messages=[
                HumanMessage(
                    content="I need to learn about DevOps practices and tools. Can you help me understand the basics of CI/CD, containerization, and infrastructure as code?",
                    name="user",
                ) for _ in range(1)
            ],
            question="",
            knowledge_chunks=[],
            query_needed=True,
            subquestions=[],
            answer_text="",
            db_sql_logs=[],
            need_more_kb=True,
            need_regenerate_subq=False,
            external_data=[],
            novelty_test=False,
            loop_counter=0,
        )
        
        # 建立 LangGraph 流程時加入 checkpointer
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
            should_continue_search,
            {"continue": "action", "end": "final_answer_node"},
        )
        graph_builder.add_edge("final_answer_node", "curiosity_node")
        graph_builder.add_edge("curiosity_node", "novelty_evaluator_node")
        graph_builder.add_conditional_edges(
            "novelty_evaluator_node",
            is_subquestion_novel,
            {
                "regenerate_subq": "curiosity_node", 
                "end": "web_search_node"
            },
        )
        graph_builder.add_edge("web_search_node", "knowledge_ingestion_node")
        graph_builder.add_conditional_edges(
            "knowledge_ingestion_node", route_knowledge_ingestion, {END: END}
        )

        # 正確的編譯方式
        self.graph = graph_builder.compile(
            checkpointer=self.memory_saver,
        )

    def get_current_state(self) -> AppState:
        """取得目前的 pipeline state。"""
        return self.state

    def run(self, initial_input: AppState) -> dict:
        """執行 pipeline 並返回完整狀態歷史"""
        try:
            result = self.graph.invoke(
                self.state,
                config={
                    "recursion_limit": 10,
                    "configurable": {"thread_id": initial_input["thread_id"]}
                }
            )
            return {
                "final_state": result,
                "checkpoints": self._get_checkpoints(initial_input["thread_id"])
            }
        except GraphRecursionError:
            return {
                "error": "Recursion limit reached",
                "checkpoints": self._get_checkpoints(initial_input["thread_id"])
            }

    def _get_checkpoints(self, thread_id: str) -> list:
        """獲取所有檢查點"""
        return self.memory_saver.list(
            config={"configurable": {"thread_id": thread_id}}
        )

    def get_config(self) -> dict[str, Any]:
        """回傳管線設定資訊，可根據需要增加字段。"""
        return {
            "llm": self.llm,
            "memory_saver": "MemorySaver",
            "tools": ["knowledge_base_fetcher_tool"],
        }


# 編譯流程圖
graph = CuriousityAgentPipeline().graph

if __name__ == "__main__":
    import random
    from faker import Faker
    
    fake = Faker()
    
    def generate_random_appstate() -> AppState:
        """Generate a simple random AppState with Faker-enhanced data"""
        return AppState(
            thread_id=f"thread_{fake.uuid4()}",
            messages=[
                HumanMessage(
                    content=fake.sentence(),
                    name=fake.user_name(),
                ) for _ in range(random.randint(1, 2))
            ],
            question=fake.catch_phrase(),
            knowledge_chunks=[
                fake.paragraph(nb_sentences=5) 
                for _ in range(random.randint(1, 3))
            ],
            query_needed=random.choice([True, False]),
            subquestions=[
                f"{fake.random_element(('How','Why','What'))} {fake.word()} works?"
                for _ in range(random.randint(0, 2))
            ],
            answer_text=fake.paragraph(nb_sentences=3) if random.random() > 0.5 else "",
            db_sql_logs=[
                f"SELECT * FROM {fake.bothify(text='table_????')} "
                f"WHERE created_at > '{fake.date_this_decade()}'"
                for _ in range(random.randint(0, 2))
            ],
            need_more_kb=random.choice([True, False]),
            need_regenerate_subq=random.choice([True, False]),
            external_data=[
                f"{fake.uri()}?query={fake.word()}"
                for _ in range(random.randint(0, 2))
            ],
            novelty_test=random.choice([True, False]),
            loop_counter=0,
        )
    
    # Test the pipeline with random state
    pipeline = CuriousityAgentPipeline()
    random_state = generate_random_appstate()
    print("Generated AppState:", random_state)
    result = pipeline.run(random_state)
    print("\nPipeline Result:", result)
    checkpoints = list(result["checkpoints"]) # 把這個物件拿來玩
    
    def track_state_changes(checkpoints):
        """Track changes between states, focusing on messages and node execution"""
        from difflib import Differ
        differ = Differ()

        if not checkpoints:
            print("No checkpoints to analyze")
            return
        
        prev_state = None
        for idx, cp in enumerate(checkpoints):
            current_state = cp.checkpoint['channel_values']
            
            # Initial state
            if prev_state is None:
                print(f"\n=== Initial State (Step {idx}) ===")
                if current_state.get('messages'):
                    print(f"Initial Message: {current_state['messages'][0].content}")
                active_nodes = [k for k in current_state.keys() if ':' not in k and '_node' in k]
                if active_nodes:
                    print(f"Active Node: {active_nodes[0]}")
                print("-" * 80)
                prev_state = current_state
                continue
            
            # Compare states
            print(f"\n=== Step {idx} Changes ===")
            
            # 1. Message Changes with difflib
            curr_msgs = [msg.content for msg in current_state.get('messages', [])]
            prev_msgs = [msg.content for msg in prev_state.get('messages', [])]
            
            if curr_msgs != prev_msgs:
                print("\nMessage Changes:")
                diff = list(differ.compare(prev_msgs, curr_msgs))
                for line in diff:
                    if line.startswith(('+ ', '- ')):
                        # Truncate long messages
                        message = line[:100] + '...' if len(line) > 100 else line
                        # Color code: green for additions, red for removals
                        if line.startswith('+'):
                            print(f"\033[92m{message}\033[0m")  # Green
                        else:
                            print(f"\033[91m{message}\033[0m")  # Red
            
            # 2. Node Execution
            curr_nodes = {k: v for k, v in current_state.items() 
                         if ':' not in k and '_node' in k}
            prev_nodes = {k: v for k, v in prev_state.items() 
                         if ':' not in k and '_node' in k}
            
            new_nodes = set(curr_nodes.keys()) - set(prev_nodes.keys())
            removed_nodes = set(prev_nodes.keys()) - set(curr_nodes.keys())
            
            if new_nodes or removed_nodes:
                print("\nNode Changes:")
                for node in new_nodes:
                    print(f"\033[92m+ {node}\033[0m")  # Green for new nodes
                for node in removed_nodes:
                    print(f"\033[91m- {node}\033[0m")  # Red for removed nodes
            
            # 3. Branch Decisions
            branches = {k: v for k, v in current_state.items() 
                       if k.startswith('branch:')}
            if branches:
                print("\nBranch Decisions:")
                for branch, target in branches.items():
                    print(f"• {branch.split(':')[-2]} → {target}")
            
            print("-" * 80)
            prev_state = current_state
    
    track_state_changes(checkpoints)
    