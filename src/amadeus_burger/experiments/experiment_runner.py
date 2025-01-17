"""
ExperimentRunner for tracking and persisting agent experiment states.
Designed to work with LangGraph-based agent pipelines.
"""
from typing import TypeVar, Generic, Any
from datetime import datetime, UTC
from uuid import uuid4
import threading
import time

from amadeus_burger.constants.settings import Settings
from amadeus_burger.db import DBClient, get_client
from amadeus_burger.db.schemas import ExperimentRecord, Snapshot, S, Metric
from amadeus_burger.constants.enums import CompressorType, MetricType
from amadeus_burger.agents import AgentPipeline
from amadeus_burger.experiments.snapshot_compressors import get_compressor
from amadeus_burger.experiments.metrics import get_metric
from amadeus_burger.constants.enums import PipelineType, MetricType



class ExperimentRunner(Generic[S]):
    """Tracks and persists agent pipeline experiment states"""
    
    def __init__(
        self, 
        pipeline: AgentPipeline,
        db_client: str | None = None,
        db_client_params: dict[str, Any] | None = None,
        snapshot_interval: float | None = None,
        max_snapshots: int | None = None,
        snapshot_on_metrics: bool | None = None,
        collection_name: str | None = None,
        snapshot_compressor: CompressorType | None = None,
        metrics: list[MetricType] | None = None,
    ):
        self.pipeline = pipeline
        db_client = db_client or Settings.experiment_runner.db_client
        db_client_params = db_client_params or Settings.experiment_runner.db_client_params
        self._db_client: DBClient = get_client(
            db_client, 
            **(db_client_params or {})
        )

        self._snapshot_thread: threading.Thread | None = None
        self._current_experiment: ExperimentRecord[S] | None = None
        self._should_stop = threading.Event()

        self._snapshot_interval = snapshot_interval
        self._max_snapshots = max_snapshots
        self._snapshot_on_metrics = snapshot_on_metrics
        self._collection_name = collection_name
        self._snapshot_compressor = snapshot_compressor
        self._metrics = metrics
    
    @property
    def metrics(self) -> list[MetricType]:
        """Get current metrics to track"""
        return self._metrics or Settings.experiment_runner.metrics
    
    @metrics.setter
    def metrics(self, value: list[MetricType]) -> None:
        """Set metrics to track"""
        self._metrics = value
    
    def calculate_metrics(self, state: S) -> list[Metric]:
        """Calculate all registered metrics for a state"""
        metrics = []
        for metric_type in self.metrics:
            metric = get_metric(metric_type)  # Creates a new metric instance
            metric.calculate(state)  # Calculates and sets the value
            metrics.append(metric)
        return metrics
    
    def _record_metrics(self) -> None:
        """Record all metrics for current state"""
        if not self._current_experiment:
            return
            
        state = self.pipeline.get_current_state()
        new_metrics = self.calculate_metrics(state)
        
        # Add new metrics to experiment
        self._current_experiment.metrics.extend(new_metrics)
        
        # Save to database
        self.db_client.upsert(
            data={"metrics": [m.model_dump() for m in self._current_experiment.metrics]},
            query_str="id = :id",
            params={"id": self._current_experiment.id}
        )

    # Use the property pattern for all settings to allow dynamic updates
    @property
    def snapshot_interval(self) -> float | None:
        return self._snapshot_interval or Settings.experiment_runner.snapshot_interval
    
    @property
    def max_snapshots(self) -> int:
        return self._max_snapshots or Settings.experiment_runner.max_snapshots
    
    @property
    def snapshot_on_metrics(self) -> bool:
        return self._snapshot_on_metrics or Settings.experiment_runner.snapshot_on_metrics
    
    @property
    def collection_name(self) -> str:
        return self._collection_name or Settings.experiment_runner.collection_name
    
    @property
    def db_client(self) -> DBClient:
        return self._db_client
    
    @db_client.setter
    def db_client(self, value: DBClient) -> None:
        self._db_client = value

    @property
    def current_experiment(self) -> ExperimentRecord[S] | None:
        return self._current_experiment
    
    @property
    def snapshot_compressor(self) -> CompressorType | None:
        return self._snapshot_compressor or Settings.experiment_runner.compressor_type

    def update_current_experiment(self, update: dict[str, Any]) -> None:
        if not self._current_experiment:
            raise RuntimeError("No experiment in progress")
        for key, value in update.items():
            setattr(self._current_experiment, key, value)

    def start(
            self,
            experiment_name: str,
            initial_input: Any,
            snapshot_interval: float | None = None,
            max_snapshots: int = None,
            snapshot_on_metrics: bool = None,
            collection_name: str = None,
            compress_snapshots: bool = None,
            metrics: list[MetricType] | None = None,
        ) -> ExperimentRecord[S]:
        """Start tracking a new experiment"""
        if metrics is not None:
            self.metrics = metrics
            
        snapshot_interval = snapshot_interval or self.snapshot_interval
        max_snapshots = max_snapshots or self.max_snapshots
        snapshot_on_metrics = snapshot_on_metrics or self.snapshot_on_metrics
        collection_name = collection_name or self.collection_name
        compress_snapshots = compress_snapshots or self.compress_snapshots

        if self._current_experiment:
            raise RuntimeError("Experiment already in progress")
            
        self._current_experiment = ExperimentRecord[S](
            id=str(uuid4()),
            name=experiment_name,
            start_time=datetime.now(UTC),
            end_time=None,
            pipeline_type=self.pipeline.__class__.__name__,
            pipeline_config=self.pipeline.get_config(),
            metrics=[],  # Initialize empty list for metrics
            snapshots=[],
            status="running",
            initial_input=initial_input
        )
        
        # Record initial metrics
        self._record_metrics()
        
        # Start automatic snapshots if interval is set
        if snapshot_interval:
            self._should_stop.clear()
            self._snapshot_thread = threading.Thread(
                target=self._auto_snapshot_loop,
                daemon=True
            )
            self._snapshot_thread.start()

        # Save initial state
        self.db_client.upsert(data=self._current_experiment.model_dump())
        return self._current_experiment

    def take_snapshot(
            self,
            collection_name: str = None,
            snapshot_compressor: CompressorType | None = None
        ) -> None:
        """Record current state with proper typing"""
        if not self._current_experiment:
            raise RuntimeError("No experiment in progress")
        
        state = self.pipeline.get_current_state()
        collection_name = collection_name or self.collection_name
        snapshot_compressor = snapshot_compressor or self.snapshot_compressor
        
        if len(self._current_experiment.snapshots) >= self.max_snapshots:
            return  # Skip if max snapshots reached
        
        # Calculate metrics for this snapshot
        snapshot_metrics = self.calculate_metrics(state)
        
        snapshot = Snapshot[S](
            state=state,
            timestamp=datetime.now(UTC),
            metrics=snapshot_metrics  # Add metrics to snapshot
        )
        
        if snapshot_compressor is not None:
            compressor = get_compressor(snapshot_compressor)
            snapshot.compressed_data = compressor.compress(snapshot)
            snapshot.compression_type = snapshot_compressor
            # Clear uncompressed state to save space
            snapshot.state = None
        
        self._current_experiment.snapshots.append(snapshot)
        
        # only keeping the latest metrics for experiment record
        self._current_experiment.metrics = snapshot_metrics
        
        # Update experiment with new snapshot and metrics
        self.db_client.upsert(
            data={
                "snapshots": [s.model_dump() for s in self._current_experiment.snapshots],
                "metrics": [m.model_dump() for m in self._current_experiment.metrics]
            },
            query_str="id = :id",
            params={"id": self._current_experiment.id}
        )

    def _auto_snapshot_loop(self) -> None:
        """Background thread for taking automatic snapshots"""
        while not self._should_stop.is_set():
            if self._current_experiment and self.snapshot_interval:
                try:
                    self.take_snapshot()
                except Exception as e:
                    print(f"Error taking snapshot: {e}")  # TODO: proper logging
                time.sleep(self.snapshot_interval)

    def end(self, status: str = "completed") -> ExperimentRecord[S]:
        """End experiment tracking"""
        if not self._current_experiment:
            raise RuntimeError("No experiment in progress")

        if self._snapshot_thread:
            self._should_stop.set()
            self._snapshot_thread.join()
            self._snapshot_thread = None

        self._current_experiment.status = status
        self._current_experiment.end_time = datetime.now(UTC)
        
        # Record final metrics
        self._record_metrics()
        
        # Take final snapshot
        try:
            self.take_snapshot()
        except Exception:
            pass  # Don't fail if final snapshot fails
            
        # Update final state
        self.db_client.upsert(
            data={
                "status": status,
                "end_time": self._current_experiment.end_time,
                "metrics": self._current_experiment.metrics
            },
            query_str="id = :id",
            params={"id": self._current_experiment.id}
        )
        
        result = self._current_experiment
        self._current_experiment = None
        return result

if __name__ == "__main__":
    from amadeus_burger.agents import get_pipeline
    from amadeus_burger.constants.settings import Settings
    from amadeus_burger.constants.enums import PipelineType, MetricType
    import time
    from typing import TypedDict
    
    # Example 1: Basic usage with default metrics
    pipeline = get_pipeline(PipelineType.STRUCTURED_LEARNING)
    runner = ExperimentRunner[TypedDict](
        pipeline=pipeline,
        metrics=[MetricType.NUM_KNOWLEDGE_NODES, MetricType.NUM_KNOWLEDGE_EDGES]
    )
    
    experiment = runner.start(
        experiment_name="結構化學習實驗_1",  # Structured Learning Experiment 1
        initial_input="學習Python的async/await概念"  # Learn Python async/await concepts
    )
    
    # Each snapshot will calculate and store metrics
    time.sleep(2)  # Agent doing work...
    runner.take_snapshot()
    
    # Print latest metrics
    for metric in experiment.metrics:
        print(f"{metric.name}: {metric.value} ({metric.timestamp})")
    
    time.sleep(2)  # More work...
    runner.take_snapshot()
    
    # Print metrics from all snapshots
    for snapshot in experiment.snapshots:
        print(f"\nSnapshot at {snapshot.timestamp}:")
        for metric in snapshot.metrics:
            print(f"  {metric.name}: {metric.value}")
    
    final_record = runner.end()
    print(f"\n實驗 {final_record.id} 完成")
    print(f"快照數量: {len(final_record.snapshots)}")
    print("最終指標:")
    for metric in final_record.metrics:
        print(f"  {metric.name}: {metric.value}")
    
    # Example 2: Automatic snapshots with perplexity tracking
    pipeline = get_pipeline(PipelineType.ADAPTIVE_LEARNING)
    runner = ExperimentRunner(
        pipeline=pipeline,
        snapshot_interval=1.0,  # Take snapshot every second
        max_snapshots=5,
        metrics=[MetricType.AVERAGE_PERPLEXITY]  # Only track perplexity
    )
    
    experiment = runner.start(
        experiment_name="自適應學習實驗_1",  # Adaptive Learning Experiment 1
        initial_input="學習Python裝飾器的概念"  # Learn Python decorator concepts
    )
    
    # Let automatic snapshots record metrics
    time.sleep(3)  # Will take 3 snapshots with metrics
    
    final_record = runner.end()
    # print(f"\n實驗 {final_record.id} 完成")
    # print(f"快照數量: {len(final_record.snapshots)}")
    # print("最終困惑度:", final_record.metrics[0].value)
    

