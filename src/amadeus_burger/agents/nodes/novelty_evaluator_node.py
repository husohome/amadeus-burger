from langchain_core.messages import AIMessage



def novelty_evaluator_node(state) -> dict:
    """
    NoveltyEvaluator Node

    功能：
    - 從 state['subquestions'] 讀取子問題列表
    - 逐一檢查是否包含 '跨領域' 或 '新奇' 字樣
    - 過濾後的子問題寫回 state['subquestions']

    Parameters
    ----------
    state : AppState
        - subquestions (list[str]): 待檢查的新奇子問題

    Returns
    -------
    dict
        - "messages": [AIMessage(...)]：回饋當前Node的過濾結果
    """
    state["novelty_test"] = False
    subqs = state["subquestions"]

    # 評斷相對目標問題和當前知識庫是否足夠新奇

    if subqs:
        state["novelty_test"] = True
        msg = AIMessage(content=f"NoveltyEvaluatorNode 經篩選，子問題足夠新奇 => {subqs}")
        pass

    msg = AIMessage(content=f"NoveltyEvaluatorNode 經篩選，子問題不夠新奇，重新生成 => {subqs}")
    return {"messages": [msg]}


def route_novelty_evaluator(state) -> str:
    """
    假設篩選完之後，一定要進下一個 Node，
    或若篩選結果為空就走某條分支...可在此判斷

    """
    if state["novelty_test"]:
        # 若沒有子問題可搜尋 => 也可考慮跳到其他 Node
        return "external_search_node"
    return "curiosity_node"
