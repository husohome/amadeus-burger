# Amadeus Burger Documentation
# Amadeus Burger 文件

## Project Structure 專案結構

```
amadeus_burger/
├── agents/             # Agent module 代理人模組
│   ├── base.py         # Base classes for agent pipelines 代理人管線基礎類別
│   └── pipelines.py    # Concrete pipeline implementations 具體管線實作
├── constants/          # Constants module 常數模組
│   ├── enums.py        # Enums for type safety 型別安全的列舉
│   └── settings.py     # Global settings configuration 全域設定
├── db/                 # Database module 資料庫模組
│   ├── clients.py      # Database client implementations 資料庫客戶端實作
│   └── schemas.py      # Pydantic models for data structures Pydantic 資料結構模型
├── experiments/        # Experiments module 實驗模組
│   ├── experiment_runner.py  # Main experiment tracking 主要實驗追蹤
│   ├── metrics.py           # Metric interfaces and implementations 指標介面與實作
│   └── snapshot_compressors.py  # Snapshot compression snapshot壓縮
├── utils/              # Utilities module 工具模組
│   └── helpers.py      # Common utilities 通用工具函數
└── visualizers/        # Visualization module 視覺化模組
    ├── base.py         # Base classes for visualization 視覺化基礎類別
    └── visualizers.py  # Visualizer implementations 視覺化實作
```

## Settings Precedence Pattern 設定優先順序模式

專案遵循嚴格的設定優先順序：

1. Function Parameter Values (Highest Priority) 函數參數值（最高優先）
   - 直接傳遞給函數的值優先於所有其他設定
   - 範例：`runner.start(snapshot_interval=5.0)` 會覆蓋所有其他設定

2. Class Instance Settings 類別實例設定
   - 在類別初始化時設定的值
   - 範例：`ExperimentRunner(snapshot_interval=10.0)`

3. Global Settings (Lowest Priority) 全域設定（最低優先）
   - `Settings` 類別中的預設值
   - 範例：`Settings.experiment_runner.snapshot_interval`

## Implementation Guidelines 實作指南

### For Sam: Adding Agent Pipelines 新增代理管線

1. Define your pipeline class in `agents/pipelines.py` 在 `agents/pipelines.py` 定義你的管線類別：
```python
from amadeus_burger.agents import AgentPipeline

class YourPipeline(AgentPipeline):
    def get_current_state(self) -> dict[str, Any]:
        # 實作狀態獲取邏輯
        pass

    def get_config(self) -> dict[str, Any]:
        # 回傳管線配置
        pass
```

2. Add pipeline type to `constants/enums.py` 在 `constants/enums.py` 新增管線類型：
```python
class PipelineType(Enum):
    STRUCTURED_LEARNING = "structured_learning"
    YOUR_PIPELINE = "your_pipeline"  # 在此加入你的類型
```

3. Register in factory (`agents/pipelines.py`) 在工廠方法中註冊：
```python
def get_pipeline(pipeline_type: PipelineType) -> AgentPipeline:
    pipelines = {
        PipelineType.YOUR_PIPELINE: YourPipeline
    }
```

### For Chris: Adding Database Clients 新增資料庫客戶端

1. Implement client in `db/clients.py` 在 `db/clients.py` 實作客戶端：
```python
from amadeus_burger.db import DBClient

class YourClient(DBClient):
    def upsert(self, data: dict[str, Any], query_str: str | None = None) -> str:
        # 實作更新插入邏輯
        pass

    def query(self, query_str: str, params: dict[str, Any] | None = None) -> QueryResult:
        # 實作查詢邏輯
        pass
```

2. Add client type to `constants/enums.py` 在 `constants/enums.py` 新增客戶端類型：
```python
class DBClientType(Enum):
    SQLITE = "sqlite"
    YOUR_CLIENT = "your_client"  # 在此加入你的類型
```

### For Tao: Adding Visualizers 新增視覺化工具

1. Implement visualizer in `experiments/visualizers.py` 在 `experiments/visualizers.py` 實作視覺化工具：
```python
from amadeus_burger.experiments.base import Visualizer

class YourVisualizer(Visualizer):
    def render(self, data: Any) -> None:
        # 實作視覺化邏輯
        pass
```

2. Add visualizer type to `constants/enums.py` 在 `constants/enums.py` 新增視覺化類型：
```python
class VisualizerType(Enum):
    KNOWLEDGE_GRAPH = "knowledge_graph"
    YOUR_VISUALIZER = "your_visualizer"  # 在此加入你的類型
```

### Adding New Metrics 新增指標

1. Create concrete metric class 建立具體指標類別：
```python
class YourMetric(Metric):
    name: str = "your_metric_name"
    description: str = "Metric description"
    
    def calculate(self, state: Any) -> Any:
        # 實作計算邏輯
        self.value = calculated_value
        return self.value
```

2. Add to metric types in `constants/enums.py` 在 `constants/enums.py` 加入指標類型：
```python
class MetricType(Enum):
    NUM_KNOWLEDGE_NODES = "num_knowledge_nodes"
    YOUR_METRIC = "your_metric"  # 在此加入你的類型
```