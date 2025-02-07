from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage



@lru_cache(maxsize=1)
def get_knowledge_ingestion_model() -> ChatOpenAI:
    """
    KnowledgeIngestion Node 專用 LLM。
    可在這裡綁定若有需要的工具 (ex. knowledge_base_fetcher_tool 用於更新 KB)。
    """
    model = ChatOpenAI(temperature=0, model_name="gpt-4")
    return model


def knowledge_ingestion_node(state) -> dict:
    """
    這個 Node 負責將外部搜尋來的資料進一步處理並存入 KnowledgeBase。

    功能：
    - 接收外部查詢資料 (例如 state["external_data"])，
      或直接使用 state["knowledge_chunks"] 中暫存資料，
      進行整理、標記，最後更新回 KnowledgeBase。

    Parameters
    ----------
    state : AppState
        - external_data (list[str]): 外部查回來的原始資訊
        - knowledge_chunks (list[str]): 也可用來存放最終整合後的知識

    Returns
    -------
    dict
        - "messages": [AIMessage(...)] 告知已完成知識整合的結果
    """
    # 假設外部資料存在 state["external_data"] 裡
    external_data = state.get("external_data", [])
    if not external_data:
        return {"messages": [AIMessage(content="[KnowledgeIngestionNode] 無外部資料可存入。")]}

    # 呼叫 LLM 來分析外部資料
    model = get_knowledge_ingestion_model()
    combined_text = "\n".join(external_data)
    messages_for_llm = [
        {"role": "system", "content": "你是KnowledgeIngestion Node，幫我將以下外部資料整合成知識圖譜的知識。"},
        {"role": "user", "content": f"外部資料:\n{combined_text}\n請協助擴充或格式化後更新 KnowledgeBase。"}
    ]
    llm_response = model.invoke(messages_for_llm)

    # 在這裡可以把 LLM 的回應寫進 knowledge_chunks
    state["knowledge_chunks"].append(f"[Ingested Info]\n{llm_response.content}")

    msg = AIMessage(content=f"[KnowledgeIngestionNode] 已將外部資料整合並更新知識庫:\n{llm_response.content}")
    return {"messages": [msg]}


def route_knowledge_ingestion(state) -> str:
    """
    KnowledgeIngestion Node 路由
    - 資料整合完後，一般就結束流程
    """
    return "END"
