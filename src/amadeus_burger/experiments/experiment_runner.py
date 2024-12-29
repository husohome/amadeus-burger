"""
ExperimentRunner for tracking and persisting agent experiment states.
Designed to work with LangGraph-based agent pipelines.
"""
from typing import TypeVar, Generic, Any
from datetime import datetime
from uuid import uuid4
import threading
import time

from amadeus_burger import Settings
from amadeus_burger.db import DBClient, get_client
from amadeus_burger.db.schemas import ExperimentRecord, Snapshot, S
from amadeus_burger.constants.literals import CompressorTypes
from amadeus_burger.agents.base import AgentPipeline

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
        snapshot_compressor: CompressorTypes | None = None,
    ):
        self.pipeline = pipeline
        db_client = db_client or Settings.experiment_runner.db_client
        db_client_params = db_client_params or Settings.experiment_runner.db_client_params
        self.db_client: DBClient = db_client or get_client(
            Settings.experiment_runner.db_client, 
            **(db_client_params or {})
        )

        self._snapshot_thread: threading.Thread | None = None
        self._current_experiment: ExperimentRecord[S] | None = None
        self._snapshot_thread: threading.Thread | None = None
        self._should_stop = threading.Event()

        # make current experiment a property
        self.current_experiment: ExperimentRecord[S] | None = self._current_experiment

        self._snapshot_interval = snapshot_interval
        self._max_snapshots = max_snapshots
        self._snapshot_on_metrics = snapshot_on_metrics
        self._collection_name = collection_name
        self._snapshot_compressor = snapshot_compressor

    # use the property pattern for all settings
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
    def snapshot_compressor(self) -> CompressorTypes | None:
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
        ) -> ExperimentRecord[S]:
        """Start tracking a new experiment"""
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
            start_time=datetime.utcnow(),
            end_time=None,
            pipeline_type=self.pipeline.__class__.__name__,
            pipeline_config=self.pipeline.get_config(),
            metrics={},
            snapshots=[],
            status="running",
            initial_input=initial_input
        )
        
        # Start automatic snapshots if interval is set
        if snapshot_interval:
            self._should_stop.clear()
            self._snapshot_thread = threading.Thread(
                target=self._auto_snapshot_loop,
                daemon=True
            )
            self._snapshot_thread.start()

        # Save initial state
        self.db_client.save(
            collection=collection_name,
            data=self._current_experiment
        )
        return self._current_experiment


    # this should be directly using the pipeline state and should not be require a state argument
    def take_snapshot(self, collection_name: str = None, snapshot_compressor: CompressorTypes | None = None) -> None:
        """Record current state with proper typing"""
        if not self._current_experiment:
            raise RuntimeError("No experiment in progress")
        
        state = self.pipeline.get_current_state()
        collection_name = collection_name or self.collection_name
        snapshot_compressor = snapshot_compressor or self.snapshot_compressor
        
        if len(self._current_experiment.snapshots) >= self.max_snapshots:
            return  # Skip if max snapshots reached
        
        snapshot = Snapshot[S](state=state)
        
        if compress_snapshots:
            # Implement compression logic here
            pass
            
        self._current_experiment["snapshots"].append(snapshot)
        self.db_client.update(
            collection=Settings.experiment_runner.collection_name,
            query={"id": self._current_experiment["id"]},
            update={"snapshots": self._current_experiment["snapshots"]}
        )

    def _auto_snapshot_loop(self) -> None:
        """Background thread for taking automatic snapshots"""
        while not self._should_stop.is_set():
            if self._current_experiment and Settings.experiment_runner.snapshot_interval:
                try:
                    state = self.pipeline.get_current_state()
                    self.take_snapshot(state)
                except Exception as e:
                    print(f"Error taking snapshot: {e}")  # TODO: proper logging
                time.sleep(Settings.experiment_runner.snapshot_interval)

    def record_metric(self, name: str, value: Any) -> None:
        """Record a metric and optionally snapshot"""
        if not self._current_experiment:
            raise RuntimeError("No experiment in progress")
            
        self._current_experiment["metrics"][name] = value
        self.db_client.update(
            collection=Settings.experiment_runner.collection_name,
            query={"id": self._current_experiment["id"]},
            update={"metrics": self._current_experiment["metrics"]}
        )

        if Settings.experiment_runner.snapshot_on_metrics:
            state = self.pipeline.get_current_state()
            self.take_snapshot(state)

    def end(self, status: str = "completed") -> ExperimentRecord[S]:
        """End experiment tracking"""
        if not self._current_experiment:
            raise RuntimeError("No experiment in progress")

        if self._snapshot_thread:
            self._should_stop.set()
            self._snapshot_thread.join()
            self._snapshot_thread = None

        self._current_experiment["status"] = status
        self._current_experiment["end_time"] = datetime.utcnow()
        
        # Take final snapshot
        try:
            final_state = self.pipeline.get_current_state()
            self.take_snapshot(final_state)
        except Exception:
            pass  # Don't fail if final snapshot fails
            
        self.db_client.update(
            collection=Settings.experiment_runner.collection_name,
            query={"id": self._current_experiment["id"]},
            update=self._current_experiment
        )
        
        result = self._current_experiment
        self._current_experiment = None
        return result
