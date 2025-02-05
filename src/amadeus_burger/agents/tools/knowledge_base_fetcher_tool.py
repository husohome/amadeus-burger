# graph_knowledge_tool.py

import os
from neo4j import GraphDatabase
from langchain_core.tools import tool

@tool
def knowledge_base_fetcher_tool(cypher_query: str) -> str:
    """
    執行 LLM 生成的 Cypher 語句，連線本地端 Neo4J 並返回查詢結果。

    需要在 .env 中設定:
      - NEO4J_URI
      - NEO4J_USER
      - NEO4J_PASSWORD

    Parameters
    ----------
    cypher_query : str
        由 LLM 自行產生的查詢語法 (Cypher)

    Returns
    -------
    str
        查詢結果的文字描述，或錯誤訊息。
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    session = driver.session()

    try:
        result = session.run(cypher_query)
        rows = result.data()

        if not rows:
            return f"[Neo4J] 查詢語句：{cypher_query}\n結果：無匹配資料。"

        # 轉成簡單文字輸出
        output_lines = [f"[Neo4J] 查詢語句：{cypher_query}"]
        for idx, row in enumerate(rows, start=1):
            output_lines.append(f"Row{idx}: {row}")
        return "\n".join(output_lines)

    except Exception as e:
        return f"[Neo4J Error] 查詢失敗: {str(e)}\n(查詢語句: {cypher_query})"
    finally:
        session.close()
        driver.close()
