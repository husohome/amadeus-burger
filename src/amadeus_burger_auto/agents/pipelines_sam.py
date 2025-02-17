import json
import logging
import os
from functools import lru_cache
from typing import TypedDict, Annotated, Sequence, Literal, Any, Dict, List

from neo4j import GraphDatabase
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END, add_messages
from langchain_openai import ChatOpenAI
from openai import OpenAI

# 設定日誌輸出
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入 .env 檔案
load_dotenv()

# 環境變數設定
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 初始化 Neo4j driver
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 常數提示語
SYSTEM_PROMPT = (
    "你是一個跨領域且充滿創新思維的智能助手。你可以使用以下工具：\n"
    "你有著無盡的好奇心，想要在回答問題時，可以盡可能的考慮所有面向。"
    "當你接到問題時，請先仔細拆解主問題，列出所有需要進一步查詢的子問題，"
    "請先嘗試呼叫 query_neo4j 來查詢當前資料庫，若沒有資料再嘗試使用 query_web。"
    "再呼叫query_web後，我會進行新奇性評估，如果評估失敗，會要求你重新生成子問題。"
    "如果你覺得目前的知識已經可以回答問題，就拋出END。"
)

WEB_ASSISTANT_PROMPT = (
    "You are an artificial intelligence assistant and you need to engage in a helpful, detailed, "
    "and polite conversation with a user."
)

NOVELTY_PROMPT_TEMPLATE = (
    "你是一位專業的新奇性評估專家，請從跨領域和創新角度評估以下查詢問題的新奇性：\n"
    "問題：\"{question}\"\n"
    "請僅回覆 'pass' 表示這個問題具有足夠的新奇性，或回覆 'fail' 表示不夠新奇。"
)

NOVELTY_FAIL_PROMPT_TEMPLATE = (
    "你先前生成的子問題如下：\n{original_subproblems}\n"
    "這些子問題未通過新奇性評估，原因可能是：{reasons}。\n"
    "請根據以上反饋，重新生成一組更具新奇性且跨領域的子問題，以解決主要問題。"
)

# =============================================================================
# 工具與查詢函式
# =============================================================================

@tool
def query_neo4j(query: str) -> str:
    """
    查詢 Neo4j 資料庫的工具。

    參數:
        query (str): Cypher 查詢語句。

    返回:
        str: 查詢結果的 JSON 字串，若發生錯誤則回傳錯誤訊息。
    """
    return f"Neo4J 查詢結果：資料庫無資料 查詢query: {query}"
    try:
        with neo4j_driver.session() as session:
            result = session.run(query)
            records = [record.data() for record in result]
        logger.info("Neo4j 查詢成功")
        return json.dumps(records, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Neo4j 查詢失敗: {e}")
        return json.dumps({"error": f"Neo4J 查詢失敗: {str(e)}"}, ensure_ascii=False)


@tool
def query_web(question: str) -> str:
    """
    查詢網路資料，並將結果存入 Neo4J。

    流程：
      1. 進行新奇性評估，若評估不通過則回傳錯誤。
      2. 若新奇性通過，則使用 Perplexity API 進行查詢。
      3. 解析返回的內容，提取有用的知識節點。
      4. 將知識節點存入 Neo4J。

    參數:
        question (str): 用戶查詢的問題。

    返回:
        str: JSON 格式的結果，包含成功或錯誤訊息。
    """
    # return json.dumps({"message": "知識已存入 Neo4J (mock)"}, ensure_ascii=False)
    return json.dumps({"fail": "Novelty Check fail.", "reason": "新奇性評估不通過，請重新生成，再嘗試一次query_web"}, ensure_ascii=False)
    # 進行新奇性評估
    novelty_result = evaluate_novelty(question)
    novelty_data = json.loads(novelty_result)
    if novelty_data.get("decision") == "fail":
        logger.info("新奇性評估不通過")
        return json.dumps({"fail": "Novelty Check fail.", "reason": novelty_data.get("reason", "未知原因")}, ensure_ascii=False)

    client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
    messages = [
        {"role": "system", "content": WEB_ASSISTANT_PROMPT},
        {"role": "user", "content": question},
    ]

    try:
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=messages,
        )
        result_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        extracted_knowledge = extract_knowledge(result_content)
        store_knowledge_in_neo4j(extracted_knowledge)
        logger.info("知識已成功存入 Neo4j")
        return json.dumps({"message": "知識已存入 Neo4J"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"網路查詢失敗: {e}")
        return json.dumps({"error": f"網路查詢失敗: {str(e)}"}, ensure_ascii=False)


def extract_knowledge(text: str) -> Dict[str, Any]:
    """
    從查詢結果中提取知識節點，轉換為可存入 Neo4J 的格式。

    參數:
        text (str): 查詢返回的原始文本內容。

    返回:
        dict: 包含 'nodes' 與 'relationships' 的字典。
    """
    messages = [
        {"role": "system", "content": "你是一個知識提取助手，請將輸入的文本拆解成結構化的知識。"},
        {"role": "user", "content": f"請從以下內容中提取知識節點，並以 JSON 格式輸出：\n{text}"}
    ]
    client = OpenAI(api_key=OPENAI_API_KEY)

    class Neo4J(BaseModel):
        nodes: List[Dict[str, Any]]
        relationships: List[Dict[str, Any]]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        extracted_data = response.choices[0].message.content
        # 使用 json.loads 替代 eval 來解析 JSON 格式的字串
        knowledge_graph = json.loads(extracted_data)
        logger.info("知識提取成功")
        return knowledge_graph
    except Exception as e:
        logger.error(f"提取知識時發生錯誤：{e}")
        return {"nodes": [], "relationships": []}


def store_knowledge_in_neo4j(knowledge_graph: Dict[str, Any]):
    """
    將解析出的知識節點和關係存入 Neo4j。

    參數:
        knowledge_graph (dict): 包含 'nodes' 與 'relationships' 的字典。
    """
    nodes = knowledge_graph.get("nodes", [])
    relationships = knowledge_graph.get("relationships", [])

    with neo4j_driver.session() as session:
        # 插入節點
        for node in nodes:
            node_label = node.get("label", "Knowledge")
            node_id = node.get("id", "")
            properties = node.get("properties", {})

            query = f"""
            MERGE (n:{node_label} {{id: $id}})
            SET n += $properties
            """
            try:
                session.run(query, id=node_id, properties=properties)
            except Exception as e:
                logger.error(f"插入節點失敗: {e}")

        # 插入關係
        for rel in relationships:
            start_id = rel.get("start_id", "")
            end_id = rel.get("end_id", "")
            rel_type = rel.get("type", "RELATED_TO")
            properties = rel.get("properties", {})

            query = f"""
            MATCH (a {{id: $start_id}}), (b {{id: $end_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $properties
            """
            try:
                session.run(query, start_id=start_id, end_id=end_id, properties=properties)
            except Exception as e:
                logger.error(f"插入關係失敗: {e}")


def evaluate_novelty(question: str) -> str:
    """
    進行新奇性評估，確保查詢的問題具有足夠的新奇性。

    參數:
        question (str): 需要評估的新奇性問題。

    返回:
        str: 包含 "decision": "pass" 或 "decision": "fail" 的 JSON 字串。
    """
    prompt = f'請評估以下問題的新奇性: "{question}"。 回覆格式: {{"decision": "pass"}} 或 {{"decision": "fail", "reason": "原因"}}'
    try:
        client = ChatOpenAI(api_key=OPENAI_API_KEY, model_name="gpt-4o-mini")
        response = client.invoke([{"role": "system", "content": prompt}])
        # 假設 response.content 為 JSON 格式字串
        result = json.loads(response.content)
        logger.info("新奇性評估成功")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"新奇性評估失敗: {e}")
        return json.dumps({"decision": "fail", "reason": "新奇性評估失敗"}, ensure_ascii=False)
    

# =============================================================================
# 狀態機與決策流程
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
    model = model.bind_tools([query_neo4j, query_web])
    return model

class AgentState(TypedDict):
    """
    Agent 的狀態類型，包含對話訊息列表。

    Attributes:
        messages: 儲存對話歷史與工具調用資訊。
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]


def agent(state: AgentState, config: dict) -> AgentState:
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
    print("response:", response)
    return {"messages": [response]}


def choose_tool(state: AgentState) -> Literal["neo4j", "web"]:
    """
    根據對話內容選擇要使用的工具。

    參數:
        state (AgentState): 當前對話狀態。

    返回:
        Literal["neo4j", "web"]: 決定使用哪個工具。
    """
    messages = state["messages"]
    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    if tool_calls:
        for call in tool_calls:
            if call.get("name", "").lower() == "query_neo4j":
                return "neo4j"
            elif call.get("name", "").lower() == "query_web":
                return "web"
    return "web"


def regenerate(state: AgentState, config: dict) -> AgentState:
    """
    當新奇性評估不通過時，根據原先子問題及失敗原因重新生成更具新奇性的子問題，
    並將結果追加至狀態訊息中。

    參數:
        state (AgentState): 當前狀態。
        config (dict): 節點配置（此處未使用）。

    返回:
        AgentState: 更新後的狀態，包含原有訊息及新追加的重新生成子問題訊息。
    """
    return {"messages": ["這是模擬的新奇性子問題 (mock)"]}
    original_subproblems = state["messages"][-2].content
    try:
        novelty_result = json.loads(state["messages"][-1].content.strip())
        reason = novelty_result.get("reason", "未知原因")
    except Exception:
        reason = "未知原因"
    prompt = NOVELTY_FAIL_PROMPT_TEMPLATE.format(
        original_subproblems=original_subproblems,
        reasons=reason
    )
    judge = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")
    response = judge.invoke([{"role": "system", "content": prompt}])
    new_msg = BaseMessage(role="system", content=response.content.strip())
    return {"messages": state["messages"] + [new_msg]}


# =============================================================================
# 建立工作流
# =============================================================================

workflow = StateGraph(AgentState)

workflow.add_node("agent", agent)
workflow.add_node("neo4j_action", ToolNode([query_neo4j]))
workflow.add_node("web_action", ToolNode([query_web]))
# workflow.add_node("regenerate", regenerate)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    choose_tool,
    {
        "neo4j": "neo4j_action",
        "web": "web_action",
    },
)

workflow.add_edge("neo4j_action", "agent")


workflow.add_conditional_edges(
    "agent",
    lambda state: "end" if any(getattr(msg, "tool_calls", None) for msg in state["messages"]) else "continue",
    {
        "continue": "agent",
        "end": END,
    },
)

workflow.add_conditional_edges(
    "web_action",
    lambda state: "regenerate" if "fail" in state["messages"][-1].content else "end",
    {
        "regenerate": "agent",
        "end": END,
    },
)

print("what?")
graph = workflow.compile()
