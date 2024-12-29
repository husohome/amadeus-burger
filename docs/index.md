# Amadeus Burger Documentation
# Amadeus Burger 文件

## Project Structure 專案結構

```
amadeus_burger/
├── agents/             # Agent module 代理人模組
│   ├── base.py         # Base classes and factory for agent pipelines 代理人管線基礎類別與工廠
│   └── pipelines.py    # Concrete pipeline implementations 具體管線實作
├── constants/          # Constants module 常數模組
│   ├── literals.py     # Type literals and enums 型別字面值與列舉
│   └── settings.py     # Global settings configuration 全域設定
├── db/                 # Database module 資料庫模組
│   ├── clients.py      # Interface definitions and concrete database client implementations 抽象介面定義及具體資料庫客戶端實作
│   └── schemas.py      # Pydantic models for data structures Pydantic 資料結構模型
├── experiments/        # Experiments module 實驗模組
│   ├── experiment_runner.py  # Main experiment tracking 主要實驗追蹤
│   ├── metrics.py           # Metric interfaces and implementations 指標介面與實作
│   └── snapshot_compressors.py  # Snapshot compression snapshot壓縮
├── scratches/          # Scratch and previous version code 草稿與舊版程式碼
│   └── pervious_version/    # Previous implementations 先前實作
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

優先順序範例：
```python
# 全域設定（最低優先）
Settings.experiment_runner.snapshot_interval = 30.0

# 實例設定（覆蓋全域）
runner = ExperimentRunner(snapshot_interval=10.0)

# 函數參數（最高優先）
runner.start(snapshot_interval=5.0)
```

## Implementation Guidelines 實作指南

### For Sam: Adding Agent Pipelines 新增代理管線

1. Define your pipeline class in `agents/pipelines.py` 在 `agents/pipelines.py` 定義你的管線類別：
```python
from amadeus_burger.agents.base import AgentPipeline
from amadeus_burger.db.schemas import S

class YourPipeline(AgentPipeline[S]):
    def get_current_state(self) -> S:
        # 實作狀態獲取邏輯
        pass

    def get_config(self) -> dict[str, Any]:
        # 回傳管線配置
        pass
```

2. Add pipeline type to `constants/literals.py` 在 `constants/literals.py` 新增管線類型：
```python
PipelineTypes = Literal[
    "structured_learning",
    "your_pipeline_type"  # 在此加入你的類型
]
```

3. Register in factory (`agents/base.py`) 在工廠方法中註冊：
```python
def get_pipeline(pipeline_type: PipelineTypes) -> AgentPipeline:
    if pipeline_type == "your_pipeline_type":
        return YourPipeline()
```

### For Chris: Adding Database Clients 新增資料庫客戶端

1. Implement client in `db/clients.py` 在 `db/clients.py` 實作客戶端：
```python
from amadeus_burger.db.base import DBClient

class YourClient(DBClient):
    def upsert(self, data: dict[str, any], query_str: str | None = None) -> str:
        # 實作更新插入邏輯
        pass

    def query(self, query_str: str, params: dict[str, any] | None = None) -> QueryResult:
        # 實作查詢邏輯
        pass

    def delete(self, delete_str: str, params: dict[str, any] | None = None) -> int:
        # 實作刪除邏輯
        pass
```

2. Add client type to `constants/literals.py` 在 `constants/literals.py` 新增客戶端類型：
```python
DBClientTypes = Literal[
    "sqlite",
    "your_client"  # 在此加入你的類型
]
```

3. Register in factory 在工廠方法中註冊：
```python
def get_client(db_client: DBClientTypes) -> DBClient:
    if db_client == "your_client":
        return YourClient()
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

2. Add visualizer type to `constants/literals.py` 在 `constants/literals.py` 新增視覺化類型：
```python
VisualizerTypes = Literal[
    "knowledge_graph",
    "your_visualizer"  # 在此加入你的類型
]
```

3. Register in factory 在工廠方法中註冊：
```python
def get_visualizer(visualizer_type: VisualizerTypes) -> Visualizer:
    if visualizer_type == "your_visualizer":
        return YourVisualizer()
```

## Important Notes 重要說明

### Schema-First Development 模型優先開發
`db/schemas.py` 中的模型是資料結構的來源：

1. `ExperimentRecord`：核心實驗資料結構
2. `Snapshot`：狀態快照與指標
3. `Metric`：所有指標的基礎類別
4. `S` (State)：代理狀態的泛型類型

開發新功能時：
1. 先實作具體類別
2. 過程中重更新 schema
3. 最後加入工廠方法

### Placeholder Status 
注意：大部分的實作都是 placeholder，除了：
1. ExperimentRunner（核心功能）
2. 資料庫模型（資料結構）
3. 設定系統（配置）

實作具體類別時：
1. 遵循現有模式
2. 維持型別安全
3. 更新相關字面值
4. 加入工廠方法
5. 新增測試

### Adding New Metrics 新增指標

1. Create concrete metric class 建立具體指標類別：
```python
class YourMetric(Metric):
    name = "你的指標名稱"
    description = "指標描述"
    
    def calculate(self, state: S) -> Any:
        # 實作計算邏輯
        self.value = calculated_value
        return self.value
```

2. Add to metric types 加入指標類型：
```python
MetricTypes = Literal[
    "知識節點數量",
    "your_metric"  # 在此加入你的類型
]
```

3. Register in metrics mapping 在指標映射中註冊：
```python
metric_classes = {
    MetricTypes.YOUR_METRIC: YourMetric
}
``` 