"""记忆类型层模块

按照第8章架构设计的记忆类型层：
- WorkingMemory: 工作记忆 - 短期上下文管理
- EpisodicMemory: 情景记忆 - 具体交互事件存储
- SemanticMemory: 语义记忆 - 抽象知识和概念存储
- PerceptualMemory: 感知记忆 - 多模态数据存储
"""

def __getattr__(name):
    modules = {
        "WorkingMemory": ".working",
        "EpisodicMemory": ".episodic", "Episode": ".episodic",
        "SemanticMemory": ".semantic", "Entity": ".semantic", "Relation": ".semantic",
        "PerceptualMemory": ".perceptual", "Perception": ".perceptual",
    }
    if name not in modules:
        raise AttributeError(name)
    from importlib import import_module
    return getattr(import_module(modules[name], __name__), name)

__all__ = [
    # 记忆类型
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "PerceptualMemory",

    # 辅助类
    "Episode",
    "Entity",
    "Relation",
    "Perception"
]
