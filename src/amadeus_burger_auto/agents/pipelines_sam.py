import json
from typing import TypedDict, Annotated, Sequence, Literal
from functools import lru_cache

from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END, add_messages
from langchain_openai import ChatOpenAI
from openai import OpenAI

# =============================================================================
# Prompt 定義區（集中管理所有提示信息）
# =============================================================================

# 系統提示，告知 LLM 可用工具並要求生成拆解主問題與跨領域子問題的回答
SYSTEM_PROMPT = (
    "你是一個跨領域且充滿創新思維的智能助手。你可以使用以下工具：\n"
    "你產出的思考與子問題，都必須要充滿新奇性，我會檢查你的新奇性，若不夠，你會需要重新產生。"
    "1. query_neo4j ： 用於查詢 neo4J 資料庫；\n"
    "2. query_web ： 用於查詢網路上的資料；\n"
    "當你接到問題時，請先仔細拆解主問題，列出所有需要進一步查詢的子問題，"
    "請先嘗試呼叫 query_neo4j 來查詢當前資料庫，若沒有資料再嘗試使用 query_web"
    "如果你覺得已經可以回答了，就拋出END"
)

# 網路查詢輔助系統提示
WEB_ASSISTANT_PROMPT = (
    "You are an artificial intelligence assistant and you need to engage in a helpful, detailed, "
    "and polite conversation with a user."
)

# 新奇性評估提示模板，要求回覆 pass 或 fail
NOVELTY_PROMPT_TEMPLATE = (
    "你是一位專業的新奇性評估專家，請從跨領域和創新角度評估以下查詢問題的新奇性：\n"
    "問題：\"{question}\"\n"
    "請僅回覆 'pass' 表示這個問題具有足夠的新奇性，或回覆 'fail' 表示不夠新奇。"
)

# 當新奇性評估不通過時，重新生成子問題的提示模板
NOVELTY_FAIL_PROMPT_TEMPLATE = (
    "你先前生成的子問題如下：\n{original_subproblems}\n"
    "這些子問題未通過新奇性評估，原因可能是：{reasons}。\n"
    "請根據以上反饋，重新生成一組更具新奇性且跨領域的子問題，以解決主要問題。"
)

# =============================================================================
# 工具定義區
# =============================================================================

# 1. 查詢 neo4j 工具
from neo4j import GraphDatabase

# 設定 neo4j 連線參數（根據實際環境修改）
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password_here"

# 建立全域 neo4j 驅動連線
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

@tool
def query_neo4j(query: str) -> str:
    """
    查詢 neo4j 資料庫工具。

    此函數接收一段 Cypher 查詢語法，並連線至 neo4j 資料庫執行查詢，
    將結果以描述性字串返回。如果查詢發生錯誤，則返回錯誤提示。

    Args:
        query (str): 傳入的 Cypher 查詢語法。

    Returns:
        str: 查詢結果描述或錯誤提示。
    """
    try:
        return f"Neo4J 查詢結果：資料庫無資料 查詢query: {query}"
        with neo4j_driver.session() as session:
            result = session.run(query)
            records = [record.data() for record in result]
        return f"Neo4J 查詢結果：{records}"
    except Exception as e:
        return f"執行 neo4J 查詢時發生錯誤：{str(e)}"

# 2. 查詢網路工具
@tool
def query_web(question: str) -> str:
    """
    查詢網路工具。

    利用 OpenAI API（基於 perplexity.ai）進行網路查詢，
    傳入查詢問題並返回網路搜尋結果的描述字串。

    Args:
        question (str): 用戶輸入的查詢問題。

    Returns:
        str: 網路查詢結果描述或錯誤提示。
    """
    YOUR_API_KEY = "INSERT_API_KEY_HERE"  # 請替換為你自己的 API 金鑰
    client = OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")
    messages = [
        {"role": "system", "content": WEB_ASSISTANT_PROMPT},
        {"role": "user", "content": question},
    ]
    try:
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=messages,
        )
        result = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return f"網路搜尋結果：{result}"
    except Exception as e:
        return f"執行網路查詢時發生錯誤：{str(e)}"

# 3. 新奇性評估工具
@tool
def evaluate_novelty(question: str) -> str:
    """
    新奇性評估工具。

    根據傳入的查詢問題，利用 LLM 模型（gpt-4o-mini）對問題進行新奇性評估，
    並要求模型僅返回 JSON 格式的結果，如 {"decision": "pass"} 或 {"decision": "fail", "reason": "原因"}。
    如果解析失敗，則返回失敗的 JSON 格式。

    Args:
        question (str): 待評估的新奇性查詢問題。

    Returns:
        str: JSON 格式字串，包含 "decision" 與（在失敗時） "reason"。
    """
    prompt = NOVELTY_PROMPT_TEMPLATE.format(question=question) + \
             "\n請以 JSON 格式回覆，例如：{\"decision\": \"pass\"} 或 {\"decision\": \"fail\", \"reason\": \"問題過於平凡\"}"
    judge = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")
    response = judge.invoke([{"role": "system", "content": prompt}])
    output = response.content.strip()
    try:
        result = json.loads(output)
        if "decision" not in result or result["decision"] not in ["pass", "fail"]:
            return json.dumps({"decision": "fail", "reason": "無法解析決策"})
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"decision": "fail", "reason": f"解析 JSON 失敗：{str(e)}"})

# 4. 重新生成子問題工具
@tool
def regenerate_subproblems(original_subproblems: str, reason: str) -> str:
    """
    重新生成子問題工具。

    當新奇性評估不通過時，此工具根據原先生成的子問題及失敗原因，
    呼叫 LLM 模型生成一組更具新奇性且跨領域的子問題，
    並返回新的子問題列表（純文本格式）。

    Args:
        original_subproblems (str): 原先生成的子問題內容。
        reason (str): 新奇性評估失敗的原因。

    Returns:
        str: 重新生成的新奇性子問題列表（文本格式）。
    """
    prompt = NOVELTY_FAIL_PROMPT_TEMPLATE.format(
        original_subproblems=original_subproblems,
        reasons=reason
    )
    judge = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")
    response = judge.invoke([{"role": "system", "content": prompt}])
    return response.content.strip()

# 建立工具節點，將各工具包裝成 ToolNode
neo4j_tool_node = ToolNode([query_neo4j])
web_tool_node = ToolNode([query_web])
novelty_tool_node = ToolNode([evaluate_novelty])
regenerate_tool_node = ToolNode([regenerate_subproblems])

# =============================================================================
# 模型與狀態相關設置
# =============================================================================

@lru_cache(maxsize=4)
def _get_model(model_name: str):
    """
    根據模型名稱初始化對應的 LLM 模型，並綁定可用工具。

    Args:
        model_name (str): 模型名稱，目前僅支持 "openai"。

    Returns:
        ChatOpenAI: 綁定工具後的 LLM 模型實例。

    Raises:
        ValueError: 如果模型名稱不被支持。
    """
    if model_name == "openai":
        model = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")
    else:
        raise ValueError(f"Unsupported model type: {model_name}")
    model = model.bind_tools([query_neo4j, query_web, evaluate_novelty])
    return model

class AgentState(TypedDict):
    """
    Agent 狀態類型。

    Attributes:
        messages: 輸入與輸出的 BaseMessage 列表，並使用 add_messages 管理。
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]

# =============================================================================
# 節點函式定義
# =============================================================================

def call_model(state: AgentState, config: dict) -> AgentState:
    """
    呼叫 LLM 模型生成初步查詢問題。

    此函數會將系統提示與先前訊息結合後呼叫 LLM 模型生成回答，
    該回答必須包含主問題的拆解與跨領域子問題。

    Args:
        state (AgentState): 當前狀態，包括訊息列表。
        config (dict): 模型配置，包含模型名稱等資訊。

    Returns:
        AgentState: 更新後的狀態，僅包含模型生成的回應訊息。
    """
    messages = state["messages"]
    new_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    model_name = config.get('configurable', {}).get("model_name", "openai")
    model = _get_model(model_name)
    response = model.invoke(new_messages)
    return {"messages": [response]}


def regenerate(state: AgentState, config: dict) -> AgentState:
    """
    當新奇性評估不通過時，根據原先子問題及失敗原因重新生成更具新奇性的子問題，
    並將結果追加至狀態訊息中。

    從狀態中取出倒數第二則訊息作為原先子問題，最後一則訊息為新奇性評估結果，
    調用重新生成子問題工具並將結果包裝成新的 BaseMessage。

    Args:
        state (AgentState): 當前狀態。
        config (dict): 節點配置（此處未使用）。

    Returns:
        AgentState: 更新後的狀態，包含原有訊息及新追加的重新生成子問題訊息。
    """
    original_subproblems = state["messages"][-2].content
    try:
        novelty_result = json.loads(state["messages"][-1].content.strip())
        reason = novelty_result.get("reason", "未知原因")
    except Exception:
        reason = "未知原因"
    result = regenerate_tool_node.invoke(original_subproblems, reason)
    new_msg = BaseMessage(role="system", content=result)
    return {"messages": state["messages"] + [new_msg]}

# =============================================================================
# 決策函式定義
# =============================================================================

def choose_tool(state: AgentState) -> Literal["neo4j", "web"]:
    """
    根據訊息中 tool_calls 判斷使用哪個工具：
      - 若在最近的訊息中有對 query_neo4j 的工具呼叫，則返回 "neo4j"
      - 否則返回 "web"
    """
    # 逆向遍歷所有訊息，找出最近一次帶有 tool_calls 的訊息
    for msg in reversed(state["messages"]):
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            # 檢查是否有對 query_neo4j 的呼叫
            for call in tool_calls:
                if call.get("name", "").lower() == "query_neo4j":
                    return "neo4j"
            # 若有 tool_calls 但不包含 query_neo4j，則預設 web
            return "web"
    # 若完全沒有 tool_calls 記錄，則預設 web
    return "web"


def should_continue(state: AgentState) -> str:
    """
    判斷是否應繼續流程執行。

    若狀態中已出現任一工具調用記錄，則返回 "end" 表示可以結束流程；
    否則返回 "continue" 表示流程需要繼續。

    Args:
        state (AgentState): 當前狀態。

    Returns:
        str: "continue" 或 "end"。
    """
    if any(getattr(msg, "tool_calls", None) for msg in state["messages"]):
        return "end"
    return "continue"

# =============================================================================
# 模型配置類型定義
# =============================================================================

class GraphConfig(TypedDict):
    """
    流程圖配置類型。

    Attributes:
        model_name (Literal): 模型名稱，目前支援 "anthropic" 或 "openai"（此範例僅支持 "openai"）。
    """
    model_name: Literal["anthropic", "openai"]

# =============================================================================
# 建立工作流流程
# =============================================================================

# 建立 StateGraph 實例，傳入 AgentState 類型與配置 schema
workflow = StateGraph(AgentState, config_schema=GraphConfig)

# 節點 "agent": 呼叫模型生成初步查詢問題（拆解主問題並生成子問題）
workflow.add_node("agent", call_model)

# 節點 "neo4j_action": 呼叫 neo4j 工具進行查詢
workflow.add_node("neo4j_action", neo4j_tool_node)

# 節點 "web_action": 呼叫網路查詢工具進行查詢
workflow.add_node("web_action", web_tool_node)

# 節點 "novelty_check": 呼叫新奇性評估工具進行查詢問題評估
workflow.add_node("novelty_check", novelty_tool_node)

# 節點 "regenerate": 當新奇性評估未通過時，重新生成子問題
workflow.add_node("regenerate", regenerate)

# 設定流程起點為 "agent"
workflow.set_entry_point("agent")

# 從 "agent" 節點開始，根據 choose_tool 函式的決策選擇工具路徑
workflow.add_conditional_edges(
    "agent",
    choose_tool,
    {
        "neo4j": "neo4j_action",
        "web": "novelty_check",
    },
)

# 根據新奇性評估結果決定後續動作：
# 若評估結果為 "pass" 則進入 "web_action"；若為 "fail" 則進入 "regenerate"
workflow.add_conditional_edges(
    "novelty_check",
    novelty_tool_node,
    {
        "pass": "web_action",
        "fail": "regenerate",
    },
)

# 工具節點執行後，結果回傳至 "agent" 節點，讓模型根據更新訊息進一步生成回答
workflow.add_edge("neo4j_action", "agent")
workflow.add_edge("web_action", "agent")
workflow.add_edge("regenerate", "agent")

# 最後，在 "agent" 節點加入通用條件邊：若狀態中已有工具調用記錄則流程結束，
# 否則返回 "agent" 以繼續執行
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "agent",
        "end": END,
    },
)

# 編譯工作流，得到可執行的工作流物件
graph = workflow.compile()

"""
工作流說明：
1. 節點 "agent" 呼叫模型生成初步查詢問題（拆解主問題並生成子問題），產生的訊息會作為後續工具查詢的依據。
2. 從 "agent" 節點根據 choose_tool 函式的決策：
   - 若訊息中包含 neo4j 關鍵字則進入 "neo4j_action" 節點呼叫 neo4j 工具；
   - 否則先進入 "novelty_check" 節點進行新奇性評估。
3. 在 "novelty_check" 節點：
   - 若評估結果為 {"decision": "pass"}，則進入 "web_action" 節點呼叫網路查詢工具；
   - 若評估結果為 {"decision": "fail", "reason": "<原因>"}，則進入 "regenerate" 節點，根據原先子問題及失敗原因重新生成更具新奇性的子問題。
4. 工具查詢後，結果會回傳至 "agent" 節點，模型根據更新後的資訊繼續生成回答，
   直到 should_continue 函式判定流程可以結束（已存在工具調用記錄）。
"""

# 現在 graph 即為組裝好的工作流，可供後續執行使用
