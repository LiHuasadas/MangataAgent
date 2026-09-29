"""Plan and Solve Agent实现 - 分解规划与逐步执行的智能体"""

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

# 默认规划器提示词模板
DEFAULT_PLANNER_PROMPT = """
你是一位顶尖的软件工程架构调研专家与任务规划师。
你的职责是：针对用户提出的复杂编程与工程开发任务，进行严密的“实地调研勘探与架构蓝图规划”，坚决杜绝脱离实际代码的“纸上谈兵”。

## 规划核心哲学：没有调查就没有发言权
一个优秀的工程方案制定必须分解为以下关键调研与设计阶段：
1. 【前置实地侦察与技术调研阶段】（必须先调用工具调研真实事实）：
   - 使用搜索工具（SearchTool / RAGTool）检索官方最新技术规范、API 参数与设计模式。
   - 使用文件工具（filesystem / note）或终端（terminal）勘探当前工作区中现有代码文件、目录树、依赖配置（如 requirements.txt/package.json）与运行环境。
2. 【施工蓝图与分步图纸制定阶段】：
   - 结合前序探查到的真实代码与文档事实，设计整体技术方案与数据模型。
   - 制定专供后续主力施工智能体（ReactAgent）执行的《详细分步施工清单》（明确标注每个步骤待修改的文件路径、类/函数签名、核心逻辑与验收测试命令）。

## 规划输出要求
请将规划过程拆解为 3 到 5 个明确、有序的子步骤，步骤中必须包含前置调研动作与最终施工图纸输出。
你的输出必须严格为一个 Python 列表，严禁输出任何额外说明或开场白：
```python
[
  "步骤1: 使用搜索/RAG工具检索官方最新技术规范与文档",
  "步骤2: 使用文件工具/终端勘探工作区现有代码结构、配置文件与依赖现状",
  "步骤3: 结合调研事实，设计系统架构方案并评估技术风险",
  "步骤4: 汇总调研与方案，输出供开发主力（ReactAgent）施工的详细分步图纸与测试建议"
]
```

## 用户任务目标
{question}

请输出你的计划列表：
"""

# 默认执行器提示词模板
DEFAULT_EXECUTOR_PROMPT = """
你是一位严谨的前置技术侦察与事实探查执行器（Technical Reconnaissance & Fact Scout）。
你的核心使命是：严格按照规划，调用工具执行当前步骤，重点在于“搜集真实事实、探查代码现状与技术求证”，为后续主力开发智能体（ReactAgent）提供精准真实的施工材料，而不是自己大包大揽去写完所有最终业务代码。

## 核心行为准则
1. 专注侦察，求真务实：
   - 若当前步骤涉及文档调研：使用 search 或 rag 工具检索官方文档与真实接口规范。
   - 若当前步骤涉及代码勘探：使用 filesystem、terminal 或 note 工具真实探查工作区文件内容与目录。
   - 若当前步骤涉及制定图纸：基于前面步骤搜集到的真实事实，输出详尽、可直接落地的《工程施工图纸》（包含具体文件路径、改动点与验收测试命令）。
2. 聚焦当步，绝不越界：只执行【当前步骤】，绝不随意跨越或提前执行其他步骤。
3. 充分继承前置事实：结合【前序步骤执行历史与成果】，在已有事实基础上继续深化。
4. 协作约定：
   - 需要使用工具调研时输出：Action: 工具名[参数]
   - 当本步骤调研/规划完成时输出：Finish[本步骤调研发现或施工图纸细节]

# 原始任务目标:
{question}

# 完整工程计划:
{plan}

# 前序步骤执行历史与调研事实:
{history}

# 本次必须专注解决的【当前步骤】:
{current_step}

请专注于【当前步骤】并推进侦察与执行：
"""


class Planner:
    """规划器 - 负责将复杂问题分解为简单步骤"""

    def __init__(
        self,
        llm_client: HelloAgentsLLM,
        prompt_template: Optional[str] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.llm_client = llm_client
        self.prompt_template = prompt_template if prompt_template else DEFAULT_PLANNER_PROMPT
        self.context_builder = context_builder

    def plan(self, input_text: str, **kwargs) -> List[str]:
        """生成执行计划"""
        prompt = self.prompt_template.format(question=input_text)

        if self.context_builder:
            optimized_context = self.context_builder.build(
                user_query=input_text,
                conversation_history=[],
                system_instructions=prompt
            )
        else:
            optimized_context = prompt

        messages = [{"role": "user", "content": optimized_context}]

        print("--- 正在生成计划 ---")
        response_text = self.llm_client.invoke(messages, **kwargs) or ""
        print(f"✅ 计划已生成:\n{response_text}")

        try:
            # 1. 优先提取 markdown 代码块内容
            clean_text = response_text.strip()
            code_block_match = re.search(r"```(?:python|json)?\s*([\s\S]*?)\s*```", clean_text)
            if code_block_match:
                clean_text = code_block_match.group(1).strip()

            # 2. 贪婪匹配最外层的列表括号 [ ... ]，避免被步骤内部的 List[int] 或测试数据截断
            match = re.search(r"\[[\s\S]*\]", clean_text)
            candidate_str = match.group(0) if match else clean_text

            # 3. 优先使用 json.loads 解析
            try:
                plan = json.loads(candidate_str)
                if isinstance(plan, list):
                    valid_steps = [str(step).strip() for step in plan if str(step).strip()]
                    if valid_steps:
                        return valid_steps
            except Exception:
                pass

            # 4. 尝试 ast.literal_eval（兼容 Python 风格单引号与字面量）
            try:
                plan = ast.literal_eval(candidate_str)
                if isinstance(plan, list):
                    valid_steps = [str(step).strip() for step in plan if str(step).strip()]
                    if valid_steps:
                        return valid_steps
            except Exception:
                pass

            # 5. 兜底方案：正则逐项提取带引号的“步骤/step”内容
            items = re.findall(r'["\']((?:步骤|\d+\.|\bstep\b)[\s\S]*?)["\']', candidate_str, re.IGNORECASE)
            if items:
                return [it.strip() for it in items if it.strip()]

            print(f"❌ 无法从模型响应中提取列表格式的步骤")
            print(f"原始响应: {response_text}")
            return []
        except Exception as e:
            print(f"❌ 解析计划时发生未知错误: {e}")
            print(f"原始响应: {response_text}")
            return []


class Executor:
    """执行器 - 负责按计划逐步执行并调用工具"""

    def __init__(
        self,
        llm_client: HelloAgentsLLM,
        prompt_template: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.llm_client = llm_client
        self.prompt_template = prompt_template if prompt_template else DEFAULT_EXECUTOR_PROMPT
        self.tool_registry = tool_registry
        self.context_builder = context_builder

    def execute(self, question: str, plan: List[str], **kwargs) -> str:
        """按计划逐步执行任务"""
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

            if self.context_builder:
                optimized_context = self.context_builder.build(
                    user_query=question,
                    conversation_history=[],
                    system_instructions=prompt
                )
            else:
                optimized_context = prompt

            if self.tool_registry and self.tool_registry.list_tools():
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
            else:
                messages = [{"role": "user", "content": optimized_context}]
                response_text = (self.llm_client.invoke(messages, **kwargs) or "").strip()

            history += f"步骤 {i}: {step}\n结果: {response_text}\n\n"
            final_answer = response_text
            print(f"✅ 步骤 {i} 已完成，结果: {final_answer}")

        return history.strip()


class PlanAndSolveAgent(Agent):
    """
    Plan and Solve Agent - 分解规划与逐步执行的智能体
    
    这个Agent能够：
    1. 将复杂问题分解为简单步骤 (Planner)
    2. 按照计划逐步执行并调用工具 (Executor)
    3. 维护执行历史和上下文
    4. 得出最终答案
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
        custom_prompts: Optional[Dict[str, str]] = None,
        host: str = "localhost",
        port: int = 8001,
        **kwargs
    ):
        # 创建智能体名片
        agent_card = AgentCard(
            name="Plan and Solve Agent",
            description="技术调研勘探与架构施工图纸规划",
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
                    id="reconnaissance",
                    name="Technical Reconnaissance",
                    description="调用工具实地检索技术文档与勘探代码现状"
                ),
                Skill(
                    id="blueprint_planning",
                    name="Blueprint Planning",
                    description="架构方案设计与制定详细分步施工图纸"
                )
            ]
        )
        super().__init__(name=name, llm=llm, agent_card=agent_card,
                         system_prompt=system_prompt, config=config)

        # 工具注册表
        self.tool_registry = tool_registry if tool_registry is not None else ToolRegistry()
        self.llm_client = llm

        # 设置提示词模板
        self.planner_prompt = (custom_prompts or {}).get("planner") or DEFAULT_PLANNER_PROMPT
        self.executor_prompt = (custom_prompts or {}).get("executor") or DEFAULT_EXECUTOR_PROMPT

        # 初始化记忆工具
        self.memory_tool = MemoryTool(
            user_id=user_id,
            memory_types=["working", "episodic", "semantic", "perceptual"]
        )
        # 初始化 RAG 工具
        self.rag_tool = RAGTool(
            knowledge_base_path=knowledge_base_path,
            rag_namespace=rag_namespace
        )
        # 初始化上下文构建器
        self.context_builder = ContextBuilder(
            memory_tool=self.memory_tool,
            rag_tool=self.rag_tool,
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

        # 注册所有工具（完全保留）
        self.add_tool(self.memory_tool)
        self.add_tool(self.rag_tool)
        # 结构化笔记工具
        self.note_tool = NoteTool(workspace)
        self.add_tool(self.note_tool)
        # terminal 工具
        self.terminal = TerminalTool(
            workspace=workspace,
            timeout=30
        )
        self.add_tool(self.terminal)
        # 网页搜索工具
        self.search_tool = SearchTool()
        # fileSystem 工具
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
        # github 工具
        github_mcp = MCPTool(
            name="github",
            auto_expand=False,
            server_command=[
                "npx", "-y",
                "@modelcontextprotocol/server-github"
            ]
        )
        self.add_tool(github_mcp)

        # 初始化实用的 Planner 与 Executor
        self.planner = Planner(
            llm_client=self.llm_client,
            prompt_template=self.planner_prompt,
            context_builder=self.context_builder
        )
        self.executor = Executor(
            llm_client=self.llm_client,
            prompt_template=self.executor_prompt,
            tool_registry=self.tool_registry,
            context_builder=self.context_builder
        )

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
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(final_answer, "assistant"))
            return final_answer

        # 2. 执行计划
        final_answer = self.execute(input_text, plan, **kwargs)
        print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")

        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))
        return final_answer

    def plan(self, input_text: str, **kwargs) -> List[str]:
        """生成执行计划"""
        return self.planner.plan(input_text, **kwargs)

    def execute(self, input_text: str, plan: List[str], **kwargs) -> str:
        """按计划逐步执行任务"""
        return self.executor.execute(input_text, plan, **kwargs)

    def add_tool(self, tool):
        """
        添加本地工具，或展开 MCP 工具并适配 ReAct 的字符串输入。
        """
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

        parameters = tool.get_parameters()
        param_schema = {}
        for p in parameters:
            req_mark = "(必填)" if p.required else "(可选)"
            param_schema[p.name] = f"{p.type} {req_mark}: {p.description}"
        hint = " 输入 JSON 对象，参数定义：" + json.dumps(param_schema, ensure_ascii=False)
        full_description = f"{tool.description}。{hint}"

        def execute_local_tool(input_text: str, target_tool=tool):
            text = input_text.strip()
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

        self.tool_registry.register_function(
            tool.name,
            full_description,
            execute_local_tool
        )
        print(f"✅ 本地工具 '{tool.name}' 注册成功，包含 {len(parameters)} 个参数说明")
