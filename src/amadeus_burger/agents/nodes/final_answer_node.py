from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage



@lru_cache(maxsize=1)
def get_final_answer_model() -> ChatOpenAI:
    """
    給 FinalAnswer Node 用的 LLM。
    """
    model = ChatOpenAI(temperature=0, model_name="gpt-4")
    return model


def final_answer_node(state) -> dict:
    """
    (2) FinalAnswer Node

    彙整先前收集的 KnowledgeBase 內容，產出最終答案並寫入資料庫。

    Parameters
    ----------
    state : AppState
        - question (str): 主問題
        - knowledge_chunks (list[str]): 從KB收集到的資訊

    Returns
    -------
    dict
        - "messages": [AIMessage(...)]: 包含最終回答
        - "answer_text": str
        - "db_sql_logs": list[str]: 模擬 SQL 寫入指令
    """
    knowledge_text = "\n".join(state["knowledge_chunks"]) or "目前知識庫中無相關知識"
    
    # (A) 呼叫 LLM，做最後的回答整合
    model = get_final_answer_model()
    messages_for_llm = [
        {"role": "system", "content": "你是FinalAnswer Node， KnowledgeChunks 是目前你的知識庫中相關的知識，請根據這些知識來回答問題。"},
        {"role": "user", "content": f"Question: {state['question']}\nKnowledgeChunks:\n{knowledge_text}"}
    ]
    llm_response = model.invoke(messages_for_llm)
    
    final_ans = llm_response.content  # LLM的回答當作最終回答
    
    # (B) 模擬寫入資料庫
    sql_cmd = f"INSERT INTO AnswerRecordTable(question, answer) VALUES('{state['question']}', '{final_ans}')"
    log_cmd = f"INSERT INTO Log(prompt, output) VALUES('Q: {state['question']}', 'A: {final_ans}')"

    return {
        "messages": [AIMessage(content=f"[FinalAnswerNode] {final_ans}")],
        "answer_text": final_ans,
        "db_sql_logs": [sql_cmd, log_cmd],
    }
