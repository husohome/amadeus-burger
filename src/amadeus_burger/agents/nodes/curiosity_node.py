from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from appstate.appstate import AppState


@lru_cache(maxsize=1)
def get_curiosity_model() -> ChatOpenAI:
    """
    Curiosity Node 專用的 LLM，可用於生成子問題。
    """
    model = ChatOpenAI(temperature=0.7, model_name="gpt-4")
    return model


def curiosity_node(state: AppState) -> dict:
    """
    (3) Curiosity Node

    根據最終回答，進一步產生跨領域 / 新奇子問題，若不滿意可重複生成。

    Parameters
    ----------
    state : AppState
        - question (str): 主問題
        - answer_text (str): 最終回答 (做為產生子問題的語境)
        - need_regenerate_subq (bool): 若 True 代表要再次生成子問題

    Returns
    -------
    dict
        - "messages": [AIMessage(...)]: LLM生成子問題後的回饋
    """
    model = get_curiosity_model()
    messages_for_llm = [
        {"role": "system", "content": "你是Curiosity Node，請幫我想一些跨領域、新奇的子問題。"},
        {"role": "user", "content": f"Here is the final answer: {state['answer_text']}\n請給我新奇子問題:"}
    ]
    llm_response = model.invoke(messages_for_llm)
    
    # 假設 LLM 的回答用換行拆分 => 生成 subquestions
    new_subquestions = [q.strip() for q in llm_response.content.split("\n") if q.strip()]
    
    # 存入 state["subquestions"]
    state["subquestions"] = new_subquestions
    
    # 如果您想根據 LLM 輸出判斷是否要 "need_regenerate_subq = True"，
    # 可以在這裡做判斷 => 例如: 如果 LLM 回傳內容太少就再來一次
    if len(new_subquestions) < 2:
        state["need_regenerate_subq"] = True
    else:
        state["need_regenerate_subq"] = False
    
    return {
        "messages": [AIMessage(content=f"[CuriosityNode] 生成子問題: {new_subquestions}")]
    }


def route_curiosity(state: AppState) -> str:
    """
    Curiosity Node 結束後，看 need_regenerate_subq:
    - True => 回到 curiosity_node
    - False => 去 external_search_node
    """
    if state.get("need_regenerate_subq", False):
        return "curiosity_node"
    return "external_search_node"
