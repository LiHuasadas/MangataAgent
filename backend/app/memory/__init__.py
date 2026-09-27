"""HelloAgents记忆系统模块

按照第8章架构设计的分层记忆系统：
- Memory Core Layer: 记忆核心层
- Memory Types Layer: 记忆类型层
- Storage Layer: 存储层
- Integration Layer: 集成层
"""

# Memory Core Layer (记忆核心层)
from .base import MemoryItem, MemoryConfig, BaseMemory


def __getattr__(name):
    if name == "MemoryManager":
        from .manager import MemoryManager
        return MemoryManager
    if name in {"WorkingMemory", "EpisodicMemory", "SemanticMemory", "PerceptualMemory"}:
        from . import types
        return getattr(types, name)
    if name in {"DocumentStore", "SQLiteDocumentStore"}:
        from .storage import document_store
        return getattr(document_store, name)
    raise AttributeError(name)

__all__ = [
    # Core Layer
    "MemoryManager",

    # Memory Types
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "PerceptualMemory",

    # Storage Layer
    "DocumentStore",
    "SQLiteDocumentStore",

    # Base
    "MemoryItem",
    "MemoryConfig",
    "BaseMemory"
]
