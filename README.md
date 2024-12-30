# Amadeus Burger

An experimental AGI prototype focused on autonomous knowledge gathering and memory formation through knowledge graphs.

## 專案現況 Current Status

目前專案專注於介面設計，主要包含：

- ExperimentRunner：實驗生命週期管理與指標追蹤
- Database Interface (DBClient)：統一的資料存取模式
- Settings System：三層式的設定值覆寫機制
- Agent Interface：實驗性 AI agent 的基礎架構

## 專案結構 Project Structure

```
amadeus_burger/
├── agents/             # Agent module
│   ├── base.py         # Base classes and factory for agent pipelines
│   └── pipelines.py    # Concrete pipeline implementations
├── constants/          # Constants module
│   ├── literals.py     # Type literals and enums
│   └── settings.py     # Global settings configuration
├── db/                 # Database module
│   ├── clients.py      # Interface definitions and database client implementations
│   └── schemas.py      # Pydantic models for data structures
├── experiments/        # Experiments module
│   ├── experiment_runner.py  # Main experiment tracking
│   ├── metrics.py           # Metric interfaces and implementations
│   └── snapshot_compressors.py  # Snapshot compression
├── scratches/          # Scratch and previous version code
│   └── pervious_version/    # Previous implementations
├── utils/              # Utilities module
│   └── helpers.py      # Common utilities
└── visualizers/        # Visualization module
    ├── base.py         # Base classes for visualization
    └── visualizers.py  # Visualizer implementations
```

詳細的開發指南請參考 [docs/index.md](docs/index.md)。

## 類別架構 Class Architecture

專案中的類別分為以下幾種：

1. Base Interfaces：

   - `AgentPipeline`：Agent pipeline 的基礎類別
   - `DBClient`：Database client 的基礎介面
   - `Visualizer`：Visualizer 的基礎類別
   - `Metric`：Metric 的基礎類別
2. Data Models：

   - `ExperimentRecord`：實驗紀錄
   - `Snapshot`：實驗 snapshot
   - `State`：agent state
3. Concrete Implementations：

   - `SQLiteClient`：SQLite database client
   - `KnowledgeGraphVisualizer`：Knowledge graph visualization
   - 各種 metrics（如 `NodeCountMetric`）

## 使用範例 Usage Examples

### 基本實驗追蹤 Basic Experiment Tracking (AgentPipeline 等 Sam)

```python
from amadeus_burger import Settings
from amadeus_burger.experiments import ExperimentRunner
from amadeus_burger.db import SQLiteClient
from typing import TypedDict

# 設定 database
Settings.sqlite.connection_string = "experiments.db"
db = SQLiteClient()

# 建立 experiment runner
runner = ExperimentRunner[TypedDict](
    name="Knowledge Graph Experiment",
    description="Testing knowledge expansion",
)

# 開始實驗
runner.start()
# 實驗結束時會自動儲存最終結果
```

### 使用 Visualizers (等 Tao)

```python
from amadeus_burger.visualizers import KnowledgeGraphVisualizer

# 建立 visualizer
visualizer = KnowledgeGraphVisualizer()

# 在實驗中使用
with runner:
    for step in range(10):
        # ... experiment logic ...
      
        # Visualize current state
        state = runner.get_current_state()
        visualizer.render(state)
```

## 開發指南 Development Guide

### 詳細的開發指南請參考 [docs/index.md](docs/index.md)。

### 環境設定 Environment Setup

建議使用 virtual environment 以避免套件衝突：

```bash
# 建立 virtual environment
conda create -n amadeus python=3.12

# 啟動 virtual environment
conda activate amadeus

# 安裝專案套件
pip install -e .
```

### 設定與憑證 Settings and Credentials

本專案採用兩種不同的設定方式：

1. Settings：

   - 位於 `src/amadeus_burger/constants/settings.py`
   - 包含所有可調整的設定，如 LLM 參數、database 設定等
   - 支援三層覆寫機制：
     ```python
     # Global settings (lowest priority)
     from amadeus_burger import Settings
     Settings.llm = "gpt-4"

     # Class initialization (medium priority)
     agent = Agent(llm="claude-3")

     # Function call (highest priority)
     result = agent.generate(llm="gpt-4-turbo")
     ```
2. Credentials：

   - 存放於 `.env` 檔案（不納入版本控制）
   - 僅包含敏感資訊，如 API keys、database passwords 等
   - 請參考 `.env.example` 建立自己的 `.env` 檔案：
     ```bash
     # API Keys
     OPENAI_API_KEY=your-api-key-here
     ANTHROPIC_API_KEY=your-api-key-here
     TAVILY_API_KEY=your-api-key-here
     ```

### 目前開發者 Current Developers (照字母順序)

- Chris (add email)
- Chryth (add email)
- Nick (husohome98@gmail.com)
- Sam (add email)
- Tao (add email)

### 授權 License

MIT License
