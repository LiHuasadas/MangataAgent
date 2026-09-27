"""Plan and Solve Agent实现 - 分解规划与逐步执行的智能体"""

import ast
import json
import re
from pathlib import Path
from typing import Optional, List, Dict

from ..context import ContextBuilder, ContextConfig
from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message
from ..protocols.types import AgentCard, Capabilities, Skill
from ..tools.builtin import MemoryTool, RAGTool, NoteTool, TerminalTool, SearchTool, MCPTool
from ..tools.registry import ToolRegistry

# 默认规划器提示词模板
DEFAULT_PLANNER_PROMPT = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表，其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

# 默认执行器提示词模板
DEFAULT_EXECUTOR_PROMPT = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决"当前步骤"，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对"当前步骤"的回答:
"""

class Planner:
    """规划器 - 负责将复杂问题分解为简单步骤"""

    def __init__(
            self,
            llm_client: HelloAgentsLLM,
            prompt_template: Optional[str] = None,
            user_id: Optional[str] = None,
            knowledge_base_path: Optional[str] = "./kb",  # 👈 新增参数
            rag_namespace: Optional[str] = "reports",  # 👈 对应导入时的命名空间
            **kwargs  # 👈 接收额外参数
    ):

        self.llm_client = llm_client
        self.prompt_template = prompt_template if prompt_template else DEFAULT_PLANNER_PROMPT

        # 初始化记忆工具
        self.memory_tool=MemoryTool(
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
                max_tokens = 8000,  # 总预算
                reserve_ratio = 0.15,  # 生成余量（10-20%）
                min_relevance = 0.3,  # 最小相关性阈值
                enable_mmr = True,  # 启用最大边际相关性（多样性）
                mmr_lambda = 0.7,  # MMR平衡参数（0=纯多样性, 1=纯相关性）
                system_prompt_template = "",  # 系统提示模板
                enable_compression = True  # 启用压缩
                )
        )

    def plan(self, input_text: str, **kwargs) -> List[str]:
        """
        生成执行计划

        Args:
            question: 要解决的问题
            **kwargs: LLM调用参数

        Returns:
            步骤列表
        """
        prompt = self.prompt_template.format(question=input_text)

        # initialization of context builder
        optimized_context = self.context_builder.build(
            user_query=input_text,
            conversation_history=[],
            system_instructions=prompt  # Essential system prompt words
        )

        messages = [{"role": "user", "content": optimized_context}]

        print("--- 正在生成计划 ---")
        response_text = self.llm_client.invoke(messages, **kwargs) or ""
        print(f"✅ 计划已生成:\n{response_text}")

        try:
            # 提取Python代码块中的列表
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ 解析计划时出错: {e}")
            print(f"原始响应: {response_text}")
            return []
        except Exception as e:
            print(f"❌ 解析计划时发生未知错误: {e}")
            return []

class Executor:
    """执行器 - 负责按计划逐步执行"""

    def __init__(self, llm_client: HelloAgentsLLM, prompt_template: Optional[str] = None):
        self.llm_client = llm_client
        self.prompt_template = prompt_template if prompt_template else DEFAULT_EXECUTOR_PROMPT

    def execute(self, question: str, plan: List[str], **kwargs) -> str:
        """
        按计划执行任务

        Args:
            question: 原始问题
            plan: 执行计划
            **kwargs: LLM调用参数

        Returns:
            最终答案
        """
        history = ""
        final_answer = ""

        print("\n--- 正在执行计划 ---")
        for i, step in enumerate(plan, 1):
            print(f"\n-> 正在执行步骤 {i}/{len(plan)}: {step}")
            prompt = self.prompt_template.format(
                question=question,
                plan=plan,
                history=history if history else "无",
                current_step=step
            )


            messages = [{"role": "user", "content": prompt}]

            response_text = self.llm_client.invoke(messages, **kwargs) or ""

            history += f"步骤 {i}: {step}\n结果: {response_text}\n\n"
            final_answer = response_text
            print(f"✅ 步骤 {i} 已完成，结果: {final_answer}")

        return history.strip()

class PlanAndSolveAgent(Agent):
    """
    Plan and Solve Agent - 分解规划与逐步执行的智能体
    
    这个Agent能够：
    1. 将复杂问题分解为简单步骤
    2. 按照计划逐步执行
    3. 维护执行历史和上下文
    4. 得出最终答案
    
    特别适合多步骤推理、数学问题、复杂分析等任务。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        custom_prompts: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
        knowledge_base_path: Optional[str] = "./kb",  # 👈 新增参数
        rag_namespace: Optional[str] = "reports",  # 👈 对应导入时的命名空间
        workspace: Optional[str] = "./project_notes",
        host: str = "localhost",
        port: int = 8001,
        **kwargs  # 👈 接收额外参数
    ):
        """
        初始化PlanAndSolveAgent

        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词
            config: 配置对象
            custom_prompts: 自定义提示词模板 {"planner": "", "executor": ""}
        """
        # 创建智能体名片
        agent_card = AgentCard(
            name="Plan and Solve Agent",
            description="规划任务并使用工具逐步执行",
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
                    id="orchestration",
                    name="Agent Orchestration",
                    description="Delegates tasks to specialized agents"
                ),
                Skill(
                    id="conversation",
                    name="Conversation Management",
                    description="Manages multi-turn conversations"
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

        self.llm_client = llm
        # 设置提示词模板：用户自定义优先，否则使用默认模板
        self.planner_prompt = (custom_prompts or {}).get("planner") or DEFAULT_PLANNER_PROMPT
        self.executor_prompt = (custom_prompts or {}).get("executor") or DEFAULT_EXECUTOR_PROMPT
        # 初始化记忆工具
        self.memory_tool=MemoryTool(
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
                max_tokens = 8000,  # 总预算
                reserve_ratio = 0.15,  # 生成余量（10-20%）
                min_relevance = 0.3,  # 最小相关性阈值
                enable_mmr = True,  # 启用最大边际相关性（多样性）
                mmr_lambda = 0.7,  # MMR平衡参数（0=纯多样性, 1=纯相关性）
                system_prompt_template = "",  # 系统提示模板
                enable_compression = True  # 启用压缩
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
        运行Plan and Solve Agent
        
        Args:
            input_text: 要解决的问题
            **kwargs: 其他参数
            
        Returns:
            最终答案
        """
        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        # 1. 生成计划
        plan = self.plan(input_text, **kwargs)

        if not plan:
            final_answer = "无法生成有效的行动计划，任务终止。"
            print(f"\n--- 任务终止 ---\n{final_answer}")

            # 保存到历史记录
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(final_answer, "assistant"))

            return final_answer

        # 2. 执行计划
        final_answer = self.execute(input_text, plan, **kwargs)
        print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))

        return final_answer

    def plan(self, input_text: str, **kwargs) -> List[str]:
        """
        生成执行计划
        Args:
            input_text: 要解决的问题
            **kwargs: LLM调用参数
        Returns:
            步骤列表
        """
        prompt = self.planner_prompt.format(question=input_text)

        # initialization of context builder
        optimized_context = self.context_builder.build(
            user_query=input_text,
            conversation_history=self._history,
            system_instructions=prompt  # Essential system prompt words
        )
        messages = [{"role": "user", "content": optimized_context}]
        print("--- 正在生成计划 ---")
        response_text = self.llm_client.invoke(messages, **kwargs) or ""
        print(f"✅ 计划已生成:\n{response_text}")
        try:
            # 提取Python代码块中的列表
            match = re.search(r"\[[\s\S]*?\]", response_text)
            plan_str = match.group(0) if match else response_text.strip()
            plan = ast.literal_eval(plan_str)
            return [step for step in plan if isinstance(step, str) and step.strip()] if isinstance(plan, list) else []
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ 解析计划时出错: {e}")
            print(f"原始响应: {response_text}")
            return []
        except Exception as e:
            print(f"❌ 解析计划时发生未知错误: {e}")
            return []

    def execute(self, input_text: str, plan: List[str], **kwargs) -> str:
        """
        按计划执行任务
        Args:
            input_text: 原始问题
            plan: 执行计划
            **kwargs: LLM调用参数
        Returns:
            最终答案
        """
        history = ""
        final_answer = ""

        print("\n--- 正在执行计划 ---")
        for i, step in enumerate(plan, 1):
            print(f"\n-> 正在执行步骤 {i}/{len(plan)}: {step}")
            prompt = self.executor_prompt.format(
                question=input_text,
                plan=plan,
                history=history if history else "无",
                current_step=step
            )

            # initialization of context builder
            optimized_context = self.context_builder.build(
                user_query=input_text,
                conversation_history=self._history,
                system_instructions=prompt  # Essential system prompt words
            )

            tool_prompt = (
                f"{optimized_context}\n可用工具:\n{self.tool_registry.get_tools_description()}\n"
                "需要工具时只输出 Action: 工具名[参数]；已有足够依据时输出 Finish[本步骤结论]。"
            )
            observations = []
            response_text = ""
            for _ in range(5):
                reply = self.llm_client.invoke(
                    [{"role": "user", "content": tool_prompt + "\n" + "\n".join(observations)}], **kwargs
                ) or ""
                action = re.search(r"(?:Action:\s*)?([\w-]+)\[([\s\S]*)\]", reply)
                if action and action.group(1) != "Finish":
                    result = self.tool_registry.execute_tool(action.group(1), action.group(2))
                    observations.append(f"Action: {action.group(0)}\nObservation: {result}")
                    continue
                response_text = action.group(2).strip() if action and action.group(1) == "Finish" else reply.strip()
                break
            if not response_text:
                response_text = "工具执行记录：\n" + "\n".join(observations)
            history += f"步骤 {i}: {step}\n结果: {response_text}\n\n"
            final_answer = response_text
            print(f"✅ 步骤 {i} 已完成，结果: {final_answer}")

        return history.strip()

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
