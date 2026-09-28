"""Reflection Agent实现 - 自我反思与迭代优化的智能体"""

import ast
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..context import ContextBuilder, ContextConfig
from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message
from ..protocols.types import AgentCard, Capabilities, Skill
from ..tools.builtin import MemoryTool, RAGTool, NoteTool, TerminalTool, SearchTool, MCPTool
from ..tools.registry import ToolRegistry
from ..tools.base import Tool
from ..tools.registry import ToolRegistry


# 默认提示词模板
DEFAULT_PROMPTS = {
    "initial": """
你是一位严谨的高级代码审查架构师与自动化测试质检专家。
你的职责是：针对用户提出的开发任务或待审查内容，建立高质量的基准实现或初步审查方案。

任务要求:
{task}

请提供完整、准确、符合生产级规范的实现方案或基线代码。
""",
    "reflect": """
你是一位顶级的代码评审专家（Code Reviewer）与质量测试仲裁者。
你的职责是：对当前产出的代码和执行结果进行严苛的质量反思与漏洞审查。

# 原始任务目标:
{task}

# 待审查的代码与执行/验证现状:
{content}

## 审查维度指南
1. 正确性与逻辑自洽：是否存在逻辑死循环、边界条件失效、未处理的空值或异常？
2. 测试验证状态：如果包含【实际验证结果】，重点分析自动化测试/命令执行是否报错（如 pytest 失败或终端报错）。
3. 安全性与资源规范：是否有内存/句柄未释放、SQL/命令注入隐患、多租户路径未隔离等问题？
4. 命名与工程规范：是否易于维护、注释清晰、结构优雅？

## 判定准则（必须严格遵循）
- 若发现任何逻辑缺陷、报错或可明确改进的漏洞，请明确列出具体的问题所在，并给出清晰、可执行的修改建议。
- 若代码逻辑严密无误、实际验证测试全部通过，且达到工程交付标准，请在回答中明确包含"无需改进"（系统将据此认定质检通过并终止迭代）。
""",
    "refine": """
你是一位精益求精的代码重构与缺陷修复专家。
你的职责是：根据评审专家的反思反馈以及测试报错，对上一轮的代码实现进行针对性的修复与优化。

# 原始任务目标:
{task}

# 上一轮实现方案:
{last_attempt}

# 评审员反馈与测试缺陷报告:
{feedback}

## 修复要求
1. 直击要害：精准解决反馈中指出的缺陷与测试报错，不引入次生问题。
2. 保持完整：输出优化重构后的完整高质量代码，并附带简要的修复点对照说明。

请提供改进重构后的完整回答：
"""
}

class Memory:
    """
    简单的短期记忆模块，用于存储智能体的行动与反思轨迹。
    """
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str):
        """向记忆中添加一条新记录"""
        self.records.append({"type": record_type, "content": content})
        print(f"📝 记忆已更新，新增一条 '{record_type}' 记录。")

    def get_trajectory(self) -> str:
        """将所有记忆记录格式化为一个连贯的字符串文本"""
        trajectory = ""
        for record in self.records:
            if record['type'] == 'execution':
                trajectory += f"--- 上一轮尝试 (代码) ---\n{record['content']}\n\n"
            elif record['type'] == 'reflection':
                trajectory += f"--- 评审员反馈 ---\n{record['content']}\n\n"
        return trajectory.strip()

    def get_last_execution(self) -> str:
        """获取最近一次的执行结果"""
        for record in reversed(self.records):
            if record['type'] == 'execution':
                return record['content']
        return ""

class ReflectionAgent(Agent):
    """
    Reflection Agent - 自我反思与迭代优化的智能体

    这个Agent能够：
    1. 执行初始任务
    2. 对结果进行自我反思
    3. 根据反思结果进行优化
    4. 迭代改进直到满意

    特别适合代码生成、文档写作、分析报告等需要迭代优化的任务。

    支持多种专业领域的提示词模板，用户可以自定义或使用内置模板。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        user_id: str,
        knowledge_base_path: str,
        rag_namespace: str,
        workspace: str,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_iterations: int = 3,
        custom_prompts=None,
        host: str = "localhost",
        port: int = 8003,
        **kwargs  # 👈 接收额外参数
    ):
        """
        初始化ReflectionAgent

        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词
            config: 配置对象
            max_iterations: 最大迭代次数
            custom_prompts: 自定义提示词模板 {"initial": "", "reflect": "", "refine": ""}
        """
        # 创建智能体名片
        agent_card = AgentCard(
            name="Reflection Agent",
            description="代码深度审查、自动化测试物理验证与迭代重构",
            url=f"http://{host}:{port}",
            version="1.0.0",
            capabilities=Capabilities(
                streaming=True,
                pushNotifications=True
            ),
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
            skills=[
                Skill(
                    id="code_review",
                    name="Code Review",
                    description="代码质量深度审查与逻辑缺陷识别"
                ),
                Skill(
                    id="verification",
                    name="Test & Verification",
                    description="结合自动化测试命令运行物理验证与缺陷修复迭代"
                )
            ]
        )

        super().__init__(name=name, llm=llm, agent_card=agent_card,
                         system_prompt=system_prompt, config=config)
        self.tool_registry = ToolRegistry()
        self.max_iterations = max_iterations
        self.memory = Memory()

        # 设置提示词模板：用户自定义优先，否则使用默认模板
        self.prompts = {**DEFAULT_PROMPTS, **(custom_prompts or {})}

        # 初始化记忆工具
        self.memory_tool = MemoryTool(
            user_id=user_id,
            memory_types=["working", "episodic", "semantic", "perceptual"]
        )
        # initialization of RAG tool
        self.rag_tool = RAGTool(
            knowledge_base_path=knowledge_base_path,
            rag_namespace=rag_namespace
        )
        # 初始化上下文构建器
        self.context_builder = ContextBuilder(
            memory_tool=self.memory_tool,
            rag_tool=self.rag_tool,
            # """上下文构建配置"""
            config=ContextConfig(
                max_tokens= 1000000,  # 总预算
                reserve_ratio=0.15,  # 生成余量（10-20%）
                min_relevance=0.3,  # 最小相关性阈值
                enable_mmr=True,  # 启用最大边际相关性（多样性）
                mmr_lambda=0.7,  # MMR平衡参数（0=纯多样性, 1=纯相关性）
                system_prompt_template="",  # 系统提示模板
                enable_compression=True  # 启用压缩
            )
        )
        # self.planner = Planner(self.llm, planner_prompt)
        # self.executor = Executor(self.llm, executor_prompt)

        # 注册工具
        self.add_tool(self.memory_tool)
        self.add_tool(self.rag_tool)
        # 结构化笔记工具
        self.note_tool = NoteTool(workspace)
        self.add_tool(self.note_tool)
        # terminal 工具
        self.terminal = TerminalTool(
            workspace=workspace,
            timeout=30  # 30秒超时
        )
        self.add_tool(self.terminal)
        # 构建网页搜索工具
        self.search_tool = SearchTool()
        # 构建fileSystem工具
        files_dir = Path(workspace).resolve()
        files_dir.mkdir(parents=True, exist_ok=True)
        filesystem_mcp = MCPTool(
            name="filesystem",
            auto_expand=False,
            server_command=[
                "cmd", "/c", "npx", "-y",
                "@modelcontextprotocol/server-filesystem",
                str(files_dir),
            ]
        )
        self.add_tool(filesystem_mcp)
        # 构建githup工具
        github_mcp = MCPTool(
            name="github",
            auto_expand=False,
            server_command=[
                "npx", "-y",
                "@modelcontextprotocol/server-github"]
        )
        self.add_tool(github_mcp)

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行Reflection Agent

        Args:
            input_text: 任务描述
            **kwargs: 其他参数

        Returns:
            最终优化后的结果
        """
        print(f"\n🤖 {self.name} 开始处理任务: {input_text}")

        # 重置记忆
        self.memory = Memory()

        # 1. 初始执行
        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = self.prompts["initial"].format(task=input_text)
        initial_result = self._get_llm_response(initial_prompt, **kwargs)
        self.memory.add_record("execution", initial_result)
        validation_command = kwargs.get("validation_command")
        validation = self.terminal.run({"command": validation_command}) if validation_command else ""

        # 2. 迭代循环：反思与优化
        for i in range(self.max_iterations):
            print(f"\n--- 第 {i+1}/{self.max_iterations} 轮迭代 ---")

            # a. 反思
            print("\n-> 正在进行反思...")
            last_result = self.memory.get_last_execution()
            reflect_prompt = self.prompts["reflect"].format(
                task=input_text,
                content=last_result + (f"\n实际验证结果：\n{validation}" if validation else "")
            )

            """
                2、structure optimized_context use ContextBuild
            """
            optimized_context = self.context_builder.build(
                user_query= input_text,
                conversation_history= self._history,
                system_instructions= reflect_prompt  # Essential system prompt words
            )

            feedback = self._get_llm_response(optimized_context, **kwargs)
            if validation and (validation.startswith("⚠️") or validation.startswith("❌")):
                feedback = feedback.replace("无需改进", "需要改进")
            self.memory.add_record("reflection", feedback)

            # b. 检查是否需要停止
            if "无需改进" in feedback or "no need for improvement" in feedback.lower():
                print("\n✅ 反思认为结果已无需改进，任务完成。")
                break

            # c. 优化
            print("\n-> 正在进行优化...")
            refine_prompt = self.prompts["refine"].format(
                task=input_text,
                last_attempt=last_result,
                feedback=feedback
            )
            refined_result = self._get_llm_response(refine_prompt, **kwargs)
            self.memory.add_record("execution", refined_result)
            if validation_command:
                validation = self.terminal.run({"command": validation_command})

        final_result = self.memory.get_last_execution()
        if validation_command:
            status = "验证未通过" if validation.startswith(("⚠️", "❌")) else "验证通过"
            final_result += f"\n\n{status}：\n{validation}"
        print(f"\n--- 任务完成 ---\n最终结果:\n{final_result}")

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_result, "assistant"))

        return final_result

    def _get_llm_response(self, prompt: str, **kwargs) -> str:
        """调用LLM并获取完整响应"""
        llm_kwargs = {key: value for key, value in kwargs.items() if key != "validation_command"}
        observations = []
        for _ in range(5):
            messages = [{"role": "user", "content":
                prompt + "\n可用工具：\n" + self.tool_registry.get_tools_description()
                + "\n需要事实或验证时输出 Action: 工具名[参数]；完成时输出 Finish[完整回答]。\n"
                + "\n".join(observations)}]
            reply = self.llm.invoke(messages, **llm_kwargs) or ""
            action = re.search(r"(?:Action:\s*)?([\w-]+)\[([\s\S]*)\]", reply)
            if action and action.group(1) != "Finish":
                result = self.tool_registry.execute_tool(action.group(1), action.group(2))
                observations.append(f"Action: {action.group(0)}\nObservation: {result}")
                continue
            return action.group(2).strip() if action and action.group(1) == "Finish" else reply.strip()
        return "\n".join(observations)

    def add_tool(self, tool):
        """
        添加本地工具，或展开 MCP 工具并适配 ReAct 的字符串输入。
        """
        # 1. 如果是 MCP 工具（具备 auto_expand 属性），保持展开逻辑
        if getattr(tool, "auto_expand", False):
            expanded_tools = tool.get_expanded_tools()
            if not expanded_tools:
                raise ValueError("未发现 MCP 工具，请检查服务器启动日志")

            for expanded_tool in expanded_tools:
                def execute(input_text, wrapped=expanded_tool):
                    parameters = wrapped.get_parameters()
                    text = input_text.strip()
                    if text.startswith("{"):
                        arguments = json.loads(text)
                    elif len(parameters) == 1 and parameters[0].type == "string":
                        arguments = {parameters[0].name: input_text}
                    elif not parameters and not text:
                        arguments = {}
                    else:
                        raise ValueError("请使用 JSON 对象传入工具参数")
                    return wrapped.run(arguments)

                parameters = expanded_tool.get_parameters()
                if len(parameters) == 1 and parameters[0].type == "string":
                    hint = f" 输入 {parameters[0].name} 的文本即可。"
                else:
                    hint = " 输入 JSON 对象，参数定义：" + json.dumps(
                        expanded_tool.tool_info.get("input_schema", {}),
                        ensure_ascii=False,
                    )
                self.tool_registry.register_function(
                    expanded_tool.name, expanded_tool.description + hint, execute
                )
            print(f"✅ MCP工具 '{tool.name}' 已展开为 {len(expanded_tools)} 个独立工具")
            return

        # 2. 本地普通 Tool 的正确注册（如 MemoryTool, RAGTool）
        parameters = tool.get_parameters()
        # 将 ToolParameter 列表序列化为对 LLM 友好的参数结构提示
        param_schema = {}
        for p in parameters:
            req_mark = "(必填)" if p.required else "(可选)"
            param_schema[p.name] = f"{p.type} {req_mark}: {p.description}"
        hint = " 输入 JSON 对象，参数定义：" + json.dumps(param_schema, ensure_ascii=False)
        full_description = f"{tool.description}。{hint}"

        # 封装执行函数，支持容错解析 LLM 生成的 JSON 格式
        def execute_local_tool(input_text: str, target_tool=tool):
            text = input_text.strip()
            # 兼容 markdown 代码块包裹的 json
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()
            if text.startswith("{") and text.endswith("}"):
                arguments = json.loads(text)
            elif len(parameters) == 1 and parameters[0].type == "string":
                arguments = {parameters[0].name: text}
            else:
                try:
                    arguments = json.loads(text)
                except Exception as e:
                    return f"❌ 参数格式错误：工具 '{target_tool.name}' 要求传入合法的 JSON 对象。错误: {e}"
            return target_tool.run(arguments)

        # 注册为函数工具（或直接 register_tool 并自定义 description）
        self.tool_registry.register_function(
            tool.name,
            full_description,
            execute_local_tool
        )
        print(f"✅ 本地工具 '{tool.name}' 注册成功，包含 {len(parameters)} 个参数说明")
