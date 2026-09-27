"""内置工具模块

HelloAgents框架的内置工具集合，包括：
- SearchTool: 网页搜索工具
- CalculatorTool: 数学计算工具
- MemoryTool: 记忆工具
- RAGTool: 检索增强生成工具
- NoteTool: 结构化笔记工具（第9章）
- TerminalTool: 命令行工具（第9章）
- MCPTool: MCP 协议工具（第10章 - 基于 mcp v1.15.0）
- A2ATool: A2A 协议工具（第10章 - 基于 python-a2a v0.5.10）
- ANPTool: ANP 协议工具（第10章 - 基于 agent-connect v0.3.7）
- BFCLEvaluationTool: BFCL评估工具（第12章）
- GAIAEvaluationTool: GAIA评估工具（第12章）
- LLMJudgeTool: LLM Judge评估工具（第12章）
- WinRateTool: Win Rate评估工具（第12章）
"""

def __getattr__(name):
    modules = {
        "SearchTool": ".search_tool", "MemoryTool": ".memory_tool",
        "RAGTool": ".rag_tool", "NoteTool": ".note_tool",
        "TerminalTool": ".terminal_tool", "MCPTool": ".protocol_tools",
        "A2ATool": ".protocol_tools", "ANPTool": ".protocol_tools",
    }
    if name not in modules:
        raise AttributeError(name)
    from importlib import import_module
    return getattr(import_module(modules[name], __name__), name)

__all__ = [
    "SearchTool",
    "MemoryTool",
    "RAGTool",
    "NoteTool",
    "TerminalTool",
    "MCPTool",
    "A2ATool",
    "ANPTool",
]
