"""核心框架模块"""

from .message import Message, ChatMessage


def __getattr__(name):
    # Chat storage only needs the message models; defer optional Agent/LLM imports.
    if name == "Agent":
        from .agent import Agent
        return Agent
    if name == "HelloAgentsLLM":
        from .llm import HelloAgentsLLM
        return HelloAgentsLLM
    if name == "Config":
        from .config import Config
        return Config
    if name == "HelloAgentsException":
        from .exceptions import HelloAgentsException
        return HelloAgentsException
    raise AttributeError(name)

__all__ = [
    "Agent",
    "HelloAgentsLLM",
    "Message",
    "ChatMessage",
    "Config",
    "HelloAgentsException"
]
