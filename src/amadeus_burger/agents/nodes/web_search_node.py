import os
import requests

from langchain_core.messages import AIMessage


def web_search_node(state) -> dict:
    """
    這個 Node 負責「外部搜尋」動作，使用 Perplexity API 查詢。
    並可把搜尋結果暫存到 state["knowledge_chunks"] 或 state["external_data"]。

    Parameters
    ----------
    state : AppState
        - subquestions (list[str]): 要搜尋的子問題列表
        - knowledge_chunks (list[str]): 可選擇把搜尋結果放在這
        - external_data (list[str]): 可用於存放更細緻的外部查詢結果

    Returns
    -------
    dict
        - "messages": [AIMessage(...)]：通知已搜尋完成與結果
    """
    subs = state["subquestions"]
    if not subs:
        return {"messages": [AIMessage(content="[WebSearchNode] 沒有子問題可搜尋。")]}

    # 從 .env 取得 Perplexity API Token
    perplexity_token = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_token:
        return {"messages": [AIMessage(content="[WebSearchNode] 未找到 PERPLEXITY_API_KEY，無法查詢。")]}

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {perplexity_token}",
        "Content-Type": "application/json"
    }

    search_results = {}
    for q in subs:
        # 為每個子問題組裝要傳給 Perplexity 的 payload
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            # 依據 Perplexity API 格式，若需要傳遞訊息，可在此添加 messages
            "messages": [
                {
                    "role": "user",
                    "content": q
                }
            ]
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            # 解析回傳的 JSON
            result_json = response.json()
            
            # 取出最終回答
            # 注意: result_json["choices"][0]["message"]["content"] 為回應內文
            # 若結構有變動，請依最新Perplexity API為準
            content = result_json["choices"][0]["message"]["content"] \
                if "choices" in result_json and result_json["choices"] else "無回應"

            search_results[q] = content

        except Exception as e:
            # 若API錯誤，則記錄錯誤訊息
            search_results[q] = f"[Perplexity API Error] {e}"

    # 更新 knowledge_chunks 和 external_data
    aggregated_info = "\n".join([f"{k}: {v}" for k, v in search_results.items()])
    state["knowledge_chunks"].append(f"[WebSearchResult]\n{aggregated_info}")

    if "external_data" not in state:
        state["external_data"] = []
    for k, v in search_results.items():
        state["external_data"].append(f"{k}: {v}")

    # 回傳訊息與結果
    msg = AIMessage(content=f"[WebSearchNode] 已查詢外部 => {search_results}")
    return {"messages": [msg]}
