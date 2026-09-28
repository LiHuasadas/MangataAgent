"""ReAct Agent实现 - 推理与行动结合的智能体"""

import re
import json
import datetime
from pathlib import Path
from typing import Optional, List, Tuple

from ..tools.builtin import MemoryTool, RAGTool
from ..context import ContextBuilder, ContextConfig

from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message
from ..protocols.types import AgentCard, Capabilities, Skill
from ..tools.builtin import NoteTool, SearchTool, MCPTool
from ..tools.registry import ToolRegistry
from ..tools.builtin import TerminalTool

# 默认ReAct提示词模板
DEFAULT_REACT_PROMPT = """你是一名顶尖的全栈软件研发工程师与深度交互排错专家（ReAct Deep Coder）。
你的核心职责是：针对用户的代码编写、系统调试、未知 Bug 排查或项目重构任务，通过严密的“思考-行动-观察”循环（Thought -> Action -> Observation），深入工程环境并动手解决实际问题。

## 可用工具集（本地工具与 MCP 扩展）
{tools}

## 核心行为准则
1. 继承图纸，精准施工：如果前序 Agent（如 plan_solve_agent）已提供了《技术调研报告与施工图纸》，请务必将其作为核心施工依据，按部就班地落实每个子步骤的真实文件改动，绝不重蹈覆辙做重复的空想规划。
2. 探查先行，杜绝臆想：面对代码修改或错误排查，优先使用文件或终端工具检查真实代码与环境，绝不凭空猜测文件路径或函数签名。
3. 动手编码，真实落地：代码修改必须真实写入文件（通过 filesystem_mcp 或 terminal），确保代码完整、语法正确，不留未实现的伪代码或空 TODO。
4. 试错与自愈：工具调用报错或命令执行失败时，在 Thought 中深入分析错误原因（如依赖缺失、语法报错、路径问题），并在下一步尝试修复它。
5. 阶段性推进与结论：当通过多次工具交互完成编码、修改与自测后，输出 Finish[最终答案]，详细陈述所做修改、核心逻辑及运行结论。

## 严格执行格式
每次回复必须且仅能包含一组 Thought 和 Action，严禁跳步：

**Thought:** 分析当前环境观察结果（Observation），思考下一步具体需要编写什么代码、调用什么工具或传参理由。
**Action:** 本次执行的具体动作，格式必须为以下之一：
- `{{tool_name}}[{{tool_input}}]` - 调用指定工具（参数按工具要求传入合法 JSON 或文本）
- `Finish[最终交付成果与修改详情]` - 当任务已完整达成且经过验证时，提供最终全面结论

## 当前任务
**Question:** {question}

## 交互与执行历史
{history}

## 当前运行时间
{current_time}

现在，请开始你的思考与行动："""

class ContextAwareAgent(Agent):
    """
    ContextAwareAgent (Reasoning and Acting) Agent

    结合推理和行动的智能体，能够：
    1. 分析问题并制定行动计划
    2. 调用外部工具获取信息
    3. 基于观察结果进行推理
    4. 迭代执行直到得出最终答案

    这是一个经典的Agent范式，特别适合需要外部信息的任务。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        user_id: str,
        knowledge_base_path: str,
        rag_namespace: str,
        workspace: str,
        tool_registry: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 12,
        custom_prompt: Optional[str] = None,
        host: str = "localhost",
        port: int = 8002,
        **kwargs  # 👈 接收额外参数
    ):
        """
        初始化ContextAwareAgent

        Args:
            name: Agent名称
            llm: LLM实例
            tool_registry: 工具注册表（可选，如果不提供则创建空的工具注册表）
            system_prompt: 系统提示词
            config: 配置对象
            max_steps: 最大执行步数
            custom_prompt: 自定义提示词模板
        """
        # 创建智能体名片
        agent_card = AgentCard(
            name="ReAct Agent",
            description="基于 ReAct 范式的深度代码编写、环境交互与调试排错",
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
                    id="coding",
                    name="Deep Coding",
                    description="基于 ReAct 循环进行代码实现与文件编辑"
                ),
                Skill(
                    id="debugging",
                    name="Interactive Debugging",
                    description="利用终端与观察反馈进行动态交互排错"
                )
            ]
        )

        super().__init__(name=name, llm=llm, agent_card=agent_card,
                         system_prompt=system_prompt, config=config)


        # 如果没有提供tool_registry，创建一个空的
        if tool_registry is None:
            self.tool_registry = ToolRegistry()
        else:
            self.tool_registry = tool_registry

        self.max_steps = max_steps
        self.current_history: List[str] = []

        # 设置提示词模板：用户自定义优先，否则使用默认模板
        self.prompt_template = custom_prompt if custom_prompt else DEFAULT_REACT_PROMPT

        # 创建记忆工具
        self.memory_tool = MemoryTool(
            user_id=user_id,
            memory_types=["working", "episodic", "semantic"], # , "perceptual"
        )
        # 创建RAG工具（指向 reports 命名空间）
        self.rag_tool = RAGTool(
            knowledge_base_path=knowledge_base_path,
            rag_namespace=rag_namespace
        )
        # 初始化上下文构建器
        self.context_builder = ContextBuilder(
            memory_tool = self.memory_tool,
            rag_tool = self.rag_tool,
            config=ContextConfig(
                max_tokens= 1000000,
                reserve_ratio=0.15,
                min_relevance=0.3,
                enable_mmr=True,
                mmr_lambda=0.7,
                system_prompt_template="",
                enable_compression=True
            )
        )

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


    def run(self, input_text: str, **kwargs) -> str:
        """
        运行ReAct Agent
        Args:
            input_text: 用户问题
            **kwargs: 其他参数
        Returns:
            最终答案
        """
        self.current_history = []
        current_step = 0

        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            # 获取当前时间
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 1、构建提示词
            tools_desc = self.tool_registry.get_tools_description()
            history_str = "\n".join(self.current_history)
            prompt = self.prompt_template.format(
                tools=tools_desc,
                question=input_text,
                history=history_str,
                current_time=current_time
            )
            """
                2、structure optimized_context use ContextBuild
            """
            optimized_context = self.context_builder.build(
                user_query= input_text,
                conversation_history= self._history,
                system_instructions= prompt  # Essential system prompt words
            )

            # 调用LLM
            messages = [{"role": "user", "content": optimized_context}]
            response_text = self.llm.invoke(messages, **kwargs)
            """LLM的回复"""
            print("模型原始回复：", repr(response_text))
            if not response_text:
                print("❌ 错误：LLM未能返回有效响应。")
                break

            # 解析输出
            thought, action = self._parse_output(response_text)

            if thought:
                print(f"🤔 思考: {thought}")

            if not action:
                print("⚠️ 警告：未能解析出有效的Action，流程终止。")
                break

            # 检查是否完成
            tool_name, tool_input = self._parse_action(action)
            if tool_name == "Finish":
                final_answer = tool_input.strip()
                print(f"🎉 最终答案: {final_answer}")

                # 保存到历史记录 List[Message] format
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(final_answer, "assistant"))

                return final_answer
                # return f"{final_answer}\n{self.current_history[-1]}"

            # 工具调用参数
            if not tool_name or tool_input is None:
                self.current_history.append("Observation: 无效的Action格式，请检查。")
                continue
            print(f"🎬 行动: {tool_name}[{tool_input}]")
            # 调用工具
            observation = self.tool_registry.execute_tool(tool_name, tool_input)
            print(f"👀 观察: {observation}")

            # 更新历史
            self.current_history.append(f"Action: {action}")
            self.current_history.append(f"Observation: {observation}")

        print("⏰ 已达到最大步数，流程终止。")
        final_answer = self.llm.invoke([{"role": "user", "content":
            f"任务：{input_text}\n执行记录：{chr(10).join(self.current_history)}\n"
            "请根据已有观察给出具体结论，说明尚未完成的部分；不要再调用工具。"}], **kwargs) or "\n".join(self.current_history)

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))

        return final_answer
        # return f"{final_answer}\n{self.current_history[-1]}"

    def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析LLM输出，提取思考和行动（增强容错版）"""
        # 移除加粗标记
        clean_text = re.sub(
            r"\*\*(Thought|Action)(:)?\*\*",
            r"\1\2",
            text,
        )

        # 1. 提取 Thought
        thought_match = re.search(r"Thought:\s*(.*?)(?=(?:Action:|Finish\[|$))", clean_text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None

        # 2. 提取 Action
        action_match = re.search(r"Action:\s*(.*)", clean_text, re.DOTALL)
        if action_match:
            action = action_match.group(1).strip().strip('`').strip()
        else:
            # 容错：如果模型漏写了 Action:，但直接写了 Finish[...] 或 工具名[...]
            fallback_match = re.search(r"(\w+\[.*\])", clean_text, re.DOTALL)
            action = fallback_match.group(1).strip().strip('`').strip() if fallback_match else None

        return thought, action

    def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析行动文本，提取工具名称和输入（支持多行输入）"""
        match = re.fullmatch(r"([\w-]+)\[([\s\S]*)\]", action_text.strip())
        if match:
            return match.group(1), match.group(2)
        return None, None

    def _parse_action_input(self, action_text: str) -> str:
        """解析行动输入（支持多行输入）"""
        match = re.match(r"\w+\[([\s\S]*)\]", action_text)
        return match.group(1) if match else action_text


    # def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
    #     """解析LLM输出，提取思考和行动"""
    #     text = text.replace("**", "")
    #     thought_match = re.search(r"Thought: (.*)", text)
    #     action_match = re.search(r"Action: (.*)", text)
    #
    #     thought = thought_match.group(1).strip() if thought_match else None
    #     action = action_match.group(1).strip() if action_match else None
    #
    #     return thought, action
    #
    # def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
    #     """解析行动文本，提取工具名称和输入"""
    #     match = re.match(r"(\w+)\[(.*)\]", action_text)
    #     if match:
    #         return match.group(1), match.group(2)
    #     return None, None
    #
    # def _parse_action_input(self, action_text: str) -> str:
    #     """解析行动输入"""
    #     match = re.match(r"\w+\[(.*)\]", action_text)
    #     return match.group(1) if match else ""
