from abc import ABC, abstractmethod
from typing import Any
from amadeus_burger.db.schemas import Snapshot, S
from amadeus_burger.constants.enums import CompressorType

class SnapshotCompressor(ABC):
    """Abstract base class for snapshot compression strategies"""
    @abstractmethod
    def compress(self, snapshot: Snapshot[S]) -> bytes:
        """Compress a snapshot"""
        pass
        
    @abstractmethod 
    def decompress(self, data: bytes) -> Snapshot[S]:
        """Decompress snapshot data"""
        pass

class JsonCompressor(SnapshotCompressor):
    """Simple JSON-based compression"""
    def compress(self, snapshot: Snapshot[S]) -> bytes:
        pass
    
    def decompress(self, data: bytes) -> Snapshot[S]:
        pass

class BinaryCompressor(SnapshotCompressor):
    """Binary serialization compression"""
    def compress(self, snapshot: Snapshot[S]) -> bytes:
        pass
        
    def decompress(self, data: bytes) -> Snapshot[S]:
        pass

def get_compressor(compressor_type: CompressorType) -> SnapshotCompressor:
    if compressor_type == CompressorType.JSON:
        return JsonCompressor()
    if compressor_type == CompressorType.BINARY:
        return BinaryCompressor()
    raise ValueError(f"Unknown compressor type: {compressor_type}") 
