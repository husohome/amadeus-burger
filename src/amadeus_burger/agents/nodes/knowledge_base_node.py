# graph_knowledge_node.py

from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
# from langchain_core.tools import ToolMessage


from amadeus_burger.agents.tools.knowledge_base_fetcher_tool import knowledge_base_fetcher_tool

@lru_cache(maxsize=1)
def get_knowledge_base_model() -> ChatOpenAI:
    """
    綁定 "knowledge_base_fetcher_tool" 給 LLM，
    讓 LLM 可以直接輸出 function calls 來執行 Cypher 查詢。
    """
    model = ChatOpenAI(temperature=0, model_name="gpt-4")
    model = model.bind_tools([knowledge_base_fetcher_tool])
    return model


def knowledge_base_node(state) -> dict:
    """
    Graph Knowledge Node

    讓 LLM 根據 user question + 已有 knowledge_chunks，決定是否要生成 Cypher Query。
    呼叫 "knowledge_base_fetcher_tool" 來取得資料再整合。

    Parameters
    ----------
    state : AppState
        - question (str): 使用者問題
        - knowledge_chunks (list[str]): 目前存放的知識 (可累計)
        - messages (list[AIMessage]): 流程中已有的對話

    Returns
    -------
    dict
        - "messages": [AIMessage(...)] 為 Node 執行後輸出的消息
    """

    user_q = state["question"]
    existing_knowledge = "\n".join(state["knowledge_chunks"]) if state["knowledge_chunks"] else "(無)"

    system_prompt = f"""
        你是一個Graph RAG Node，可以通過呼叫 "knowledge_base_fetcher_tool" 來執行Cypher查詢。
        依據問題: {user_q}
        目前已知知識:
        {existing_knowledge}
        如果你需要查Neo4J中的任何資料，請輸出json格式 function call:
        name="knowledge_base_fetcher_tool"
        args={{"cypher_query":"..."}}

        如果不需要查詢，請直接回答。
    """

    # 準備要給 LLM 的對話
    messages_for_llm = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_q}
    ]

    model = get_knowledge_base_model()
    response = model.invoke(messages_for_llm)

    # 如果 LLM 有呼叫 tool，執行完會產生 ToolMessage 回到 response
    # 我們可在這裡檢查 response 是否含 tool_calls 執行成果
    # 例如:
    # if response.tool_calls:
    #     # do something with the tool call results?

    # 產生一個 AIMessage 做回饋
    final_msg_content = "[GraphKnowledgeNode] " + response.content
    # 如果 LLM 用 function call 形式 ToolMessage 產生了中繼訊息，也會在 response 的 tool_calls / tool_messages

    return {
        "messages": [AIMessage(content=final_msg_content)]
    }
