
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

# 系統提示：告知 LLM 它可用的工具清單，並要求在回答前拆解主問題、產生跨領域子問題
SYSTEM_PROMPT = (
    "你是一個跨領域且充滿創新思維的智能助手。你可以使用以下工具：\n"
    "你產出的思考與子問題，都必須要充滿新奇性，我會檢查你的新奇性，若不夠，你會需要重新產生。"
    "1. query_neo4j ： 用於查詢 neo4J 資料庫；\n"
    "2. query_web ： 用於查詢網路上的資料；\n"
    "當你接到問題時，請先仔細拆解主問題，列出所有需要進一步查詢的子問題，"
    "請先嘗試呼叫 query_neo4j 來查詢當前資料庫，若沒有資料再嘗試使用 query_web"
    "如果你覺得已經可以回答了，就拋出END"
)

# Web 查詢助手提示，供 OpenAI API 使用
WEB_ASSISTANT_PROMPT = (
    "You are an artificial intelligence assistant and you need to engage in a helpful, detailed, "
    "and polite conversation with a user."
)

# 新奇性評估提示模板，要求 LLM 僅根據跨領域和創新角度判斷查詢問題的新奇性，
# 並僅返回 "pass" 或 "fail"
NOVELTY_PROMPT_TEMPLATE = (
    "你是一位專業的新奇性評估專家，請從跨領域和創新角度評估以下查詢問題的新奇性：\n"
    "問題：\"{question}\"\n"
    "請僅回覆 'pass' 表示這個問題具有足夠的新奇性，或回覆 'fail' 表示不夠新奇。"
)

# 當新奇性評估不通過時的提示模板，要求 LLM 根據原先產生的子問題及原因重新生成
NOVELTY_FAIL_PROMPT_TEMPLATE = (
    "你先前生成的子問題如下：\n{original_subproblems}\n"
    "這些子問題未通過新奇性評估，原因可能是：{reasons}。\n"
    "請根據以上反饋，重新生成一組更具新奇性且跨領域的子問題，以解決主要問題。"
)

# =============================================================================
# 工具定義區
# =============================================================================

# 1. 查詢 neo4j 工具：連線並執行傳入的 Cypher 查詢
from neo4j import GraphDatabase

# 根據實際環境修改 neo4j 連線參數
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password_here"

# 建立全域 neo4j 驅動連線（應根據需要在應用關閉前關閉 driver）
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

@tool
def query_neo4j(query: str) -> str:
    """
    查詢 neo4J 資料庫

    Args:
        query (str): 傳入的 Cypher 查詢語法

    Returns:
        str: 返回查詢結果的描述（模擬格式），或錯誤提示
    """
    try:
        with neo4j_driver.session() as session:
            result = session.run(query)
            records = [record.data() for record in result]
        return f"Neo4J 查詢結果：{records}"
    except Exception as e:
        return f"執行 neo4J 查詢時發生錯誤：{str(e)}"

# 2. 查詢網路工具：利用 OpenAI API（以 perplexity.ai 為基礎）執行網路查詢
@tool
def query_web(question: str) -> str:
    """
    查詢網路

    Args:
        question (str): 用戶輸入的查詢問題

    Returns:
        str: 返回網路查詢結果的描述（模擬格式），或錯誤提示
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

# 3. 新奇性評估工具：利用 LLM 判官評估查詢問題的新奇性，返回 JSON 格式結果
@tool
def evaluate_novelty(question: str) -> str:
    """
    利用 LLM 判官評估查詢問題的新奇性，並返回決策與失敗原因的 JSON 字串。

    請根據跨領域與創新角度檢視下列查詢問題的新奇性，
    並請以 JSON 格式回覆，格式如下：
      - {"decision": "pass"} 表示新奇性達標；
      - {"decision": "fail", "reason": "<失敗原因>"} 表示新奇性不足。
    提示：僅回覆單一 JSON 字串，不要包含額外文字。

    Args:
        question (str): 待評估的新奇性查詢問題

    Returns:
        str: JSON 字串，包含 "decision" 與（在失敗時） "reason"。
             若無法解析，則返回 {"decision": "fail", "reason": "解析失敗"}。
    """
    prompt = NOVELTY_PROMPT_TEMPLATE.format(question=question) + \
             "\n請以 JSON 格式回覆，例如：{\"decision\": \"pass\"} 或 {\"decision\": \"fail\", \"reason\": \"問題過於平凡\"}"
    judge = ChatOpenAI(temperature=0, model_name="gpt-4o")
    response = judge.invoke([{"role": "system", "content": prompt}])
    output = response.content.strip()
    try:
        result = json.loads(output)
        if "decision" not in result or result["decision"] not in ["pass", "fail"]:
            return json.dumps({"decision": "fail", "reason": "無法解析決策"})
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"decision": "fail", "reason": f"解析 JSON 失敗：{str(e)}"})

# 4. 重新生成子問題工具：當新奇性評估不通過時，根據原先的子問題與失敗原因重新生成更具新奇性的子問題
@tool
def regenerate_subproblems(original_subproblems: str, reason: str) -> str:
    """
    利用 LLM 重新生成更具新奇性且跨領域的子問題。

    此函數根據原先產生的子問題和失敗原因，
    組成一個提示，要求 LLM 根據反饋重新生成子問題，
    並僅返回新的子問題列表（文本格式）。

    Args:
        original_subproblems (str): 原先生成的子問題內容
        reason (str): 新奇性評估失敗的原因

    Returns:
        str: 重新生成的新奇性子問題列表
    """
    prompt = NOVELTY_FAIL_PROMPT_TEMPLATE.format(
        original_subproblems=original_subproblems,
        reasons=reason
    )
    judge = ChatOpenAI(temperature=0, model_name="gpt-4o")
    response = judge.invoke([{"role": "system", "content": prompt}])
    return response.content.strip()

# =============================================================================
# 建立工具節點
# =============================================================================
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
    根據模型名稱初始化對應的 LLM 模型

    Args:
        model_name (str): 模型名稱，目前僅支持 "openai"

    Returns:
        ChatOpenAI: 綁定工具後的模型實例
    """
    if model_name == "openai":
        model = ChatOpenAI(temperature=0, model_name="gpt-4o")
    else:
        raise ValueError(f"Unsupported model type: {model_name}")
    model = model.bind_tools([query_neo4j, query_web, evaluate_novelty])
    return model

class AgentState(TypedDict):
    """
    Agent 狀態類型

    Attributes:
        messages: 一個 BaseMessage 序列，通過 add_messages 裝飾器管理訊息
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]

def should_continue(state: AgentState) -> str:
    """
    判斷流程是否應繼續

    檢查整個訊息歷史中是否存在任何工具調用記錄，
    如果已存在工具調用，則表示已獲取足夠外部資訊，可終止流程；
    否則強制繼續流程，以確保最終答案基於外部查詢結果。

    Args:
        state (AgentState): 當前狀態

    Returns:
        str: "continue" 或 "end"
    """
    if any(getattr(msg, "tool_calls", None) for msg in state["messages"]):
        return "end"
    return "continue"

def choose_tool(state: AgentState) -> Literal["neo4j", "web"]:
    """
    根據狀態中最後一則訊息內容選擇使用哪個工具

    為了強迫在回答前必須先查詢外部資訊，該函數首先檢查整個訊息歷史中是否有任何工具調用記錄。
    若無工具調用記錄，則默認返回 "web" 分支以強制執行外部查詢。
    否則，再根據最後一則訊息內容判斷：
      - 如果訊息中包含 "neo4j" 或 "match" 等關鍵詞，則返回 "neo4j"
      - 否則返回 "web"

    Args:
        state (AgentState): 當前狀態

    Returns:
        Literal["neo4j", "web"]: 工具選擇結果
    """
    if not any(getattr(msg, "tool_calls", None) for msg in state["messages"]):
        return "web"
    last_content = state["messages"][-1].content.lower()
    if "neo4j" in last_content or "match" in last_content:
        return "neo4j"
    else:
        return "web"

# =============================================================================
# 基礎系統提示與模型呼叫函數
# =============================================================================
def call_model(state: AgentState, config: dict) -> AgentState:
    """
    呼叫 LLM 模型生成初步的查詢問題

    此函數會在訊息列表前加入系統提示，並使用 LLM 生成回答，
    要求回答中包含對主問題的拆解與跨領域子問題的產出，
    並且在最終回答前必定調用外部查詢工具以獲取支持資訊。

    Args:
        state (AgentState): 當前狀態，包括交互訊息
        config (dict): 模型配置

    Returns:
        AgentState: 更新後的狀態，其中 messages 為原有訊息加上新生成的訊息
    """
    messages = state["messages"]
    # 加入系統提示訊息
    new_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    model_name = config.get('configurable', {}).get("model_name", "openai")
    model = _get_model(model_name)
    response = model.invoke(new_messages)
    # 使用 langgraph 的原始方法，共用 state：將新訊息追加到原有訊息列表中
    return {"messages": messages + [response]}

class GraphConfig(TypedDict):
    """
    流程圖配置類型

    Attributes:
        model_name: 支持 "anthropic" 或 "openai"，目前僅支持 "openai"
    """
    model_name: Literal["anthropic", "openai"]

# =============================================================================
# 建立工作流流程（使用 langgraph 原始方法共用 state）
# =============================================================================
workflow = StateGraph(AgentState, config_schema=GraphConfig)

# 節點 "agent": 呼叫 LLM 生成初步查詢問題（必須先拆解主問題並產生子問題）
workflow.add_node("agent", call_model)

# 節點 "neo4j_action": 使用 neo4j 工具進行查詢，將結果追加到 state["messages"]
workflow.add_node("neo4j_action", lambda state, config: {
    "messages": state["messages"] + [BaseMessage(
        role="system",
        content=neo4j_tool_node.invoke(state["messages"][-1].content)
    )]
})

# 節點 "web_action": 使用 web 工具進行查詢，將結果追加到 state["messages"]
workflow.add_node("web_action", lambda state, config: {
    "messages": state["messages"] + [BaseMessage(
        role="system",
        content=web_tool_node.invoke(state["messages"][-1].content)
    )]
})

# 節點 "novelty_check": 使用新奇性評估工具檢查生成的查詢問題，返回 JSON 格式結果
workflow.add_node("novelty_check", lambda state, config: {
    "messages": state["messages"] + [BaseMessage(
        role="system",
        content=novelty_tool_node.invoke(state["messages"][-1].content)
    )]
})

# 節點 "regenerate": 當新奇性評估不通過時，根據原先的子問題和失敗原因重新生成子問題
workflow.add_node("regenerate", lambda state, config: {
    "messages": state["messages"] + [BaseMessage(
        role="system",
        content=regenerate_tool_node.invoke(
            # 假設倒數第二則訊息存有原先的子問題
            state["messages"][-2].content,
            json.loads(state["messages"][-1].content).get("reason", "未知原因")
        )
    )]
})

# =============================================================================
# 定義流程邊及分支條件
# =============================================================================

# 設定入口點為 "agent"
workflow.set_entry_point("agent")

# 從 "agent" 節點開始，根據 choose_tool 的決策：
# - 如果決策結果為 "neo4j"，則進入 "neo4j_action" 節點；
# - 如果決策結果為 "web"，則進入 "novelty_check" 節點以進行新奇性評估。
workflow.add_conditional_edges(
    "agent",
    choose_tool,
    {
        "neo4j": "neo4j_action",
        "web": "novelty_check",
    },
)

# 定義 novelty_decision 決策函數：解析 novelty_check 輸出的 JSON 判斷是否通過新奇性評估
def novelty_decision(state: AgentState) -> Literal["pass", "fail"]:
    """
    根據 novelty_check 節點輸出判斷查詢問題是否新奇

    Args:
        state (AgentState): 當前狀態

    Returns:
        Literal["pass", "fail"]: "pass" 表示通過新奇性評估，"fail" 表示未通過
    """
    try:
        result = json.loads(state["messages"][-1].content.strip())
        decision = result.get("decision", "fail")
    except Exception:
        decision = "fail"
    return decision

workflow.add_conditional_edges(
    "novelty_check",
    novelty_decision,
    {
        "pass": "web_action",
        "fail": "regenerate",  # 當新奇性不通過，進入 regenerate 節點重新生成子問題
    },
)

# 各工具查詢節點完成後，結果回傳至 "agent" 節點以便 LLM 進一步處理
workflow.add_edge("neo4j_action", "agent")
workflow.add_edge("web_action", "agent")
workflow.add_edge("regenerate", "agent")

# 添加通用條件邊：檢查整個狀態中是否已有工具調用記錄，
# 若有則允許流程終止；若沒有則強制繼續循環，
# 從而保證在最終回答之前，必定至少調用了外部查詢工具。
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "agent",
        "end": END,
    },
)

# 編譯工作流，graph 為可執行的工作流對象
graph = workflow.compile()

"""
工作流說明：
1. 節點 "agent" 呼叫 LLM 生成初步查詢問題，此回答必須包含對主問題的拆解與跨領域子問題的產出，
   並且不能直接作為最終答案，必須先透過外部查詢工具獲得支持資訊。
2. 從 "agent" 節點，根據 choose_tool 決策：
   - 如果訊息中包含 neo4j 關鍵字，則直接進入 "neo4j_action" 節點調用 query_neo4j 工具；
   - 否則預設使用外部網路查詢，此時先進入 "novelty_check" 節點，
     利用 evaluate_novelty 工具評估查詢問題的新奇性（返回 JSON 格式的決策及原因）。
3. 在 "novelty_check" 節點：
   - 若評估結果為 {"decision": "pass"}，則進入 "web_action" 節點調用 query_web 工具執行網路查詢；
   - 若評估結果為 {"decision": "fail", "reason": "<原因>"}，則進入 "regenerate" 節點，
     該節點會根據原先生成的子問題及失敗原因要求模型重新生成更具新奇性的子問題。
4. 查詢工具節點（neo4j_action、web_action 或 regenerate）完成後，
   結果會被追加到 state["messages"] 中，然後回傳至 "agent" 節點，
   由 LLM 根據更新後的資訊繼續生成回答，直到 state 中已有工具調用記錄（should_continue 返回 "end"），
   這樣最終答案便基於外部查詢結果生成。
"""

# graph 即為組裝好的工作流，可用於 AI 問答或深度研究等應用。