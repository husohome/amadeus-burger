# Amadeus Burger

An experimental AGI prototype focused on autonomous knowledge gathering and memory formation through knowledge graphs.

## 專案現況 Current Status

目前專案專注於介面設計，主要包含：
- 資料庫介面 (DBClient)：統一的資料存取模式
- 設定值系統：三層式的設定值覆寫機制
- Agent 介面：實驗性 AI agent 的基礎架構

## 開發指南 Development Guide

### 環境設定 Environment Setup

建議使用虛擬環境以避免套件衝突：

```bash
# 建立虛擬環境
conda create -n amadeus python=3.12

# 啟動虛擬環境
conda activate amadeus

# 安裝專案套件
pip install -e .
```

### 設定值覆寫機制 Settings Override Pattern

本專案採用三層設定值覆寫機制，優先順序由低至高：

1. 全域設定 (最低優先)：
```python
from amadeus_burger import Settings
Settings.llm = "gpt-4"
```

2. 類別初始化 (中優先)：
```python
agent = Agent(llm="claude-3")  # 覆寫此實例的 llm
```

3. 函數呼叫 (最高優先)：
```python
result = agent.generate(llm="gpt-4-turbo")  # 僅此次呼叫使用
```

### 目前開發者 Current Developers (照字母順序)

- Chris (add email)
- Chryth (add email)
- Nick (husohome98@gmail.com)
- Sam (add email)
- Tao (add email)

### 開發規範 Development Guidelines

- 使用 Python 3.12
- 使用 Ruff 進行程式碼檢查與格式化 (Optional)
  - Ruff 是一個快速的 Python linter 和 formatter，用 Rust 編寫
  - 安裝：`pip install ruff`
  - 檢查程式碼：`ruff check .`
  - 自動修正：`ruff format .`
- 提交前請執行測試：`pytest tests/`

### 授權 License

MIT License

---

## 使用範例 Usage Examples

```python
from amadeus_burger import Settings
from amadeus_burger.db import SQLiteClient

# 全域設定
Settings.sqlite.connection_string = "experiments.db"

# 建立資料庫客戶端
db = SQLiteClient()  # 使用全域設定
# 或是覆寫連線字串
db = SQLiteClient(connection_string="custom.db")

# 查詢資料
results = db.query("status = :status", {"status": "完成"})
```
