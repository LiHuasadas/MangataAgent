"""
主机智能体（编排器），基于 Google ADK 的设计思路。
"""
import asyncio
import json
import os
import uuid
import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Awaitable, Callable


from backend.app.context import ContextBuilder, ContextConfig
from backend.app.core import HelloAgentsLLM, Agent
from backend.app.core.message import Message as LLMMessage
from backend.app.protocols.a2a.client import A2AClient
from backend.app.protocols.a2a.server import A2ABaseServer
from backend.app.protocols.types import AgentCard, Capabilities, Skill, Task, TaskState, Message, TextPart
from backend.app.protocols.types import TaskTenantContext
from backend.app.tools.builtin import SearchTool, TerminalTool, NoteTool, MCPTool, MemoryTool, RAGTool
from backend.app.tools.registry import ToolRegistry

DEFAULT_ROUTER_PROMPT = """
你是 Host Agent，云端多租户编程与工程多智能体系统的总控架构师与调度编排器。
你的唯一职责是：全面分析用户的开发任务诉求，将其拆解并路由给最合适的专长 Agent，或者编排一个顺序执行的 Agent 流水线。
【核心纪律】你自己绝对不直接编写业务代码，不直接解答技术细节，只做精准的流程规划与路由决策。

## 可用 Agent 注册表
{agent_catalog}

## 各 Agent 职责定位与编排策略
1. plan_solve_agent（技术调研与架构蓝图规划）：
   - 角色定位：架构师与技术侦察兵（Scout & Architect）。
   - 核心行为：先调用搜索工具（查官方文档）和文件/终端工具（探查代码现状），摸清真实环境后，输出《技术调研报告与详细施工图纸》。它不直接承担后续大段业务代码编写。
2. react_agent（核心代码开发与施工主力）：
   - 角色定位：主力建造工程师（Builder & Lead Developer）。
   - 核心行为：接棒 plan_solve_agent 产出的精准施工图纸，使用文件与终端工具深入工程环境，完成真实代码编写、文件重构、动态调试与报错自愈。
3. reflection_agent（代码审查与测试质检）：
   - 角色定位：QA 质检官与测试审查员（Code Reviewer & Tester）。
   - 核心行为：对写好的代码进行审查，并在终端真实运行测试命令验证。
4. simple_agent（轻量快速直答）：
   - 适用场景：概念解释、语法常识速查、简单的单点工具查询（如读单个文件、执行单条查询），无需多步规划与深度探索的场景。

## 典型编排流水线示例
- 复杂完整工程开发：["plan_solve_agent", "react_agent", "reflection_agent"]
  （第1步：实地勘探与架构图纸设计 -> 第2步：主力接棒图纸进行真实编码与调试 -> 第3步：自动化测试验证与审查质检）
- 聚焦型编码实现与质检：["react_agent", "reflection_agent"]
- 纯架构/方案规划：["plan_solve_agent"]
- 纯代码审查/测试排查：["reflection_agent"]
- 日常单点问答/速查：["simple_agent"]

## 用户请求
{question}

## 输出要求（必须严格遵守）
仅输出一个 Python 列表格式，严禁包含任何多余文字、开场白或解释：
```python
["plan_solve_agent", "react_agent", "reflection_agent"]
```
"""

DEFAULT_CONSOLIDATE_PROMPT = """
你是 Host Agent 的结果汇总器与工程交付报告生成器。

## 任务
结合用户提出的原始问题，系统化汇总各专长 Agent 产出的技术成果（规划方案、代码实现、测试与审查结果），生成一份专业、连贯、高可读性的工程交付报告（Markdown 格式）。

## 汇总规则
1. 真实客观：严格基于各 Agent 实际产出的代码与事实，严禁主观臆造任何未发生的事实或伪代码。
2. 结构清晰：按交付内容分节梳理，使用清晰的 Markdown 标题（例如：## 1. 架构规划方案、## 2. 代码实现与改动、## 3. 测试验证与代码审查）。
3. 容错呈现：若某个 Agent 在执行中发生异常或未通过验证，客观指出失败原因与当前阻断点，不要掩盖问题。
4. 交付摘要：开头用 1～2 句话精炼概括最终完成情况；结尾提供明确的后续使用或运行指引。
5. 纯净输出：仅输出 Markdown 正文，不要输出任何元解释或关于你汇总过程的闲聊。

## 用户原问题
{question}

## 各 Agent 实际产出
{agent_results}
"""

class HostAgent(Agent):
    """编排其他专长智能体的主机智能体。

    作为中心协调者，接收用户请求，并按请求类型委派给专长智能体。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        user_id: str,
        knowledge_base_path: str,
        rag_namespace: str,
        workspace: str,
        host: str = "localhost",
        port: int = 8000,
        plan_solve_agent_url: str = "http://localhost:8001",
        react_agent_url: str = "http://localhost:8002",
        reflection_agent_url: str = "http://localhost:8003",
        simple_agent_url: str = "http://localhost:8004",
        **kwargs  # 👈 接收额外参数
    ):
        """初始化主机智能体。

        Args:
            api_key: ADK 模型的 API 密钥
            host: 绑定的主机地址
            port: 绑定的端口
        """
        # 创建智能体名片
        agent_card = AgentCard(
            name="Host Agent",
            description="云端多租户多智能体总编排器与路由调度大脑",
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
                    description="任务意图分析与多智能体工作流流水线编排"
                ),
                Skill(
                    id="consolidation",
                    name="Result Consolidation",
                    description="多智能体产物整合与工程交付报告生成"
                )
            ]
        )

        # 初始化 Agent 与 A2A 服务端
        super().__init__(name=name, llm=llm, agent_card=agent_card)

        # 保存配置
        self.host = host
        self.port = port
        self._history: list[LLMMessage] = []

        # 新增主机智能体 CrewAI 的 LLM 封装：
        self.llm = llm
        self.user_id = user_id
        self.tool_registry = ToolRegistry()

        # 保存各专长智能体 URL
        self.agent_urls = {
            "plan_solve_agent": plan_solve_agent_url,
            "react_agent": react_agent_url,
            "reflection_agent": reflection_agent_url,
            "simple_agent": simple_agent_url,
        }

        # 用于与其他智能体通信的 A2A 客户端
        self.client = A2AClient()

        # 缓存已发现的智能体能力  agent : card
        self.agent_capabilities = {}

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
                max_tokens = 1000000,  # 总预算
                reserve_ratio = 0.15,  # 生成余量（10-20%）
                min_relevance = 0.3,  # 最小相关性阈值
                enable_mmr = True,  # 启用最大边际相关性（多样性）
                mmr_lambda = 0.7,  # MMR平衡参数（0=纯多样性, 1=纯相关性）
                system_prompt_template = "",  # 系统提示模板
                enable_compression = True  # 启用压缩
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

    async def startup(self):
        """启动时发现可用的专长智能体。"""
        for agent_type, url in self.agent_urls.items():
            try:
                agent_card = await self.client.discover_agent(url)

                self.agent_capabilities[agent_type] = agent_card
                print(f"Discovered {agent_type} agent at {url}")

            except Exception as e:
                print(f"Error discovering {agent_type} agent: {e}")

    async def handle_task(
        self,
        task: Task,
        *,
        conversation_history: Optional[list[LLMMessage]] = None,
        progress_callback: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> Task:
        """处理一次编排任务。

        解析用户请求，决定调用哪些专长智能体，并汇总它们的回复。

        Args:
            task: 要处理的任务

        Returns:
            带有汇总结果的任务
        """
        if task.tenant_context is None:
            raise ValueError("Task tenant context is required")
        print(f"\n--------------------------------\n")
        print(f"\nRunning method handle_task()\n")
        print(f"\n--------------------------------\n")

        # 提取消息文本
        message_text = "No input provided"
        print(f"Task: {task}")

        if task.status.message and task.status.message.parts:
            for part in task.status.message.parts:
                if hasattr(part, 'text'):
                    message_text = part.text
                    break

        if progress_callback:
            await progress_callback({"type": "progress", "stage": "preparing", "message": "正在准备上下文"})

        # Jev 前置意图打标与预研 (场景 1)
        from backend.app.core.jev_service import JevService
        jev = JevService()
        jev_analysis = await asyncio.to_thread(jev.pre_analyze_request, message_text)
        task.metadata["jev_analysis"] = jev_analysis

        jev_prefix = f"""【Jev System-One 意图打标与预研】
- 任务类型: {jev_analysis.get('task_type')}
- 复杂度评分: {jev_analysis.get('complexity')}
- 是否需要前置侦察调研: {jev_analysis.get('needs_scout')}
- 来源: {jev_analysis.get('source')}

"""
        # initialization of context builder
        optimized_context = await asyncio.to_thread(lambda: self.context_builder.build(
            user_query=message_text,
            conversation_history=conversation_history if conversation_history is not None else self._history,
            system_instructions=None
        ))
        optimized_context = jev_prefix + optimized_context

        # 分析请求，决定要调用哪些智能体
        if progress_callback:
            await progress_callback({"type": "progress", "stage": "routing", "message": "正在分析请求"})
        agents_to_call = await self._analyze_request(optimized_context)
        if progress_callback:
            await progress_callback({"type": "progress", "stage": "routed", "agents": agents_to_call,
                                     "message": "已选择专长智能体"})
        print(f"\n _analyze_request() Selected agents: {agents_to_call}\n")

        results = []
        for agent_type in agents_to_call:
            if agent_type not in self.agent_urls:
                continue
            prior = "\n\n".join(
                f"{item['agent_type']}: {item['response']}" for item in results if item['success']
            )
            delegated_message = message_text + (f"\n\n前序 Agent 的结果：\n{prior}" if prior else "")
            import inspect
            sig = inspect.signature(self._call_agent)
            if progress_callback:
                await progress_callback({"type": "progress", "stage": "agent_started",
                                         "agent_type": agent_type, "message": f"{agent_type} 正在执行"})
            call_kwargs = {}
            if "metadata" in sig.parameters:
                call_kwargs["metadata"] = task.metadata
            if "progress_callback" in sig.parameters:
                call_kwargs["progress_callback"] = progress_callback
            result = await self._call_agent(agent_type, delegated_message, task.tenant_context, **call_kwargs)
            results.append(result)
            if progress_callback:
                await progress_callback({"type": "progress", "stage": "agent_finished",
                                         "agent_type": agent_type, "success": result.get("success", False),
                                         "message": f"{agent_type} {'已完成' if result.get('success') else '执行失败'}"})
                await progress_callback({"type": "agent_result", "agent_type": agent_type,
                                         "success": result.get("success", False),
                                         "response": result.get("response", "No response")})

        # 保存各 Agent 的原始回复到 metadata，供前端展示

        agent_results_meta = []
        for result in results:
            artifact_ids = [a.id for a in result.get("artifacts", [])]
            agent_results_meta.append({
                "agent_type": result.get("agent_type", "unknown"),
                "success": result.get("success", False),
                "response": result.get("response", "No response"),
                "artifact_ids": artifact_ids,
            })
        task.metadata["agent_results"] = agent_results_meta
        print(f"\nTask metadata: {task.metadata}\n")

        if not results or not any(result.get("success") for result in results):
            failures = "; ".join(
                f"{result.get('agent_type', 'unknown')}: {result.get('response', 'unknown error')}"
                for result in results
            ) or "no specialist agents were selected"
            raise RuntimeError(f"没有可用的专长智能体：{failures}")

        # 大模型 汇总结果
        if progress_callback:
            await progress_callback({"type": "progress", "stage": "consolidating", "message": "正在汇总结果"})
        consolidated_result = await self._consolidate_results(
            message_text,
            results,
            progress_callback=progress_callback,
        )
        print(f"\n _consolidate_results() Consolidated result: {consolidated_result}\n")

        # 把汇总结果写回任务
        task.status.state = TaskState.COMPLETED
        task.status.message = Message(parts=[
            TextPart(text=consolidated_result["response"])
        ])
        print(f"\nTask status: {task.status}\n")

        # 合并各智能体产出的产物
        for result in results:
            task.artifacts.extend(result.get("artifacts", []))

        final_answer = consolidated_result.get("response", "")

        # 场景 2：Jev 后置智能记忆判定与自动持久化
        try:
            mem_decision = jev.evaluate_memory_update(message_text, final_answer)
            if mem_decision and mem_decision.get("should_remember") and hasattr(self, "memory_tool"):
                mem_type = mem_decision.get("memory_type", "working")
                self.memory_tool.run({
                    "action": "store",
                    "memory_type": mem_type,
                    "content": f"[Jev自动记忆] 关于需求 [{message_text[:80]}]: {final_answer[:250]}"
                })
                task.metadata["jev_memory_saved"] = mem_decision
                print(f"🧠 Jev 自动触发记忆写入: {mem_type}")
        except Exception as e:
            print(f"⚠️ Jev 自动记忆更新非阻断异常: {e}")

        # 场景 3：Jev 后置工程笔记自动判定与归档
        try:
            note_decision = jev.evaluate_note_update(message_text, final_answer)
            if note_decision and note_decision.get("should_record_note") and hasattr(self, "note_tool"):
                cat = note_decision.get("category", "task_blueprint")
                note_title = f"Jev沉淀_{cat}_{task.id or 'turn'}"
                self.note_tool.run({
                    "action": "create",
                    "title": note_title,
                    "content": f"## {cat}\n\n**原始需求**: {message_text}\n\n**技术方案产出**:\n{final_answer}",
                    "note_type": "conclusion",
                    "tags": ["jev_auto", cat]
                })
                task.metadata["jev_note_saved"] = note_decision
                print(f"📝 Jev 自动触发工程笔记沉淀: {note_title}")
        except Exception as e:
            print(f"⚠️ Jev 自动笔记沉淀非阻断异常: {e}")

        return task

    def _fromat_agent_results(self, result: List[Dict[str, Any]]) -> str:
        blocks = []
        for r in result:
            agent = r.get("agent_type", "unknown")
            status = "成功" if r.get("success") else "失败"
            response = r.get("response", "No response")
            n_art = len(r.get("artifacts") or [])
            blocks.append(
                f"###{agent} Agent\n"
                f"- 状态：{status}\n"
                f"- 产物数：{n_art}\n"
                f"- 回复：\n{response}\n"
            )
            print(f"\n_format_agent_results(): \n"
                  f"###{agent} Agent\n"
                  f"- 状态：{status}\n"
                  f"- 产物数：{n_art}\n"
                  f"- 回复：\n{response}\n"
                  )
        return "\n".join(blocks) if blocks else "(没有任何 Agent 返回结果)"

    def _build_agent_catalog(self) -> str:

        lines = []
        for agent_type, card in self.agent_capabilities.items():

            skills = ",".join(f"{s.name}: {s.description}" for s in card.skills)
            lines.append(
                f"type = {agent_type} | name = {card.name}"
                f"desc = {card.description} | skills = [{skills}]"
            )
        return "\n".join(lines) or "(暂无已发现的Agent)"

    async def _analyze_request(self, message: str) -> List[str]:
        """分析用户请求，决定调用哪些智能体。

        Args:
            message: 用户消息

        Returns:
            要调用的智能体类型列表
        """
        # 完整实现里会用 ADK/LLM 做意图分析
        # 这里先用简单的关键词匹配做演示
        agents = []

        # 实现crewAI
        # 1.拼接提示词模板 prompt (提示词 + agent智能体卡片)
        # self.agent_capabilities[agent_type] = agent_card
        prompt = DEFAULT_ROUTER_PROMPT.format(
            agent_catalog = self._build_agent_catalog(),
            question = message
        )

        # 同步调用；在 async 方法里建议丢到线程，避免堵事件循环
        # raw = await asyncio.to_thread(lambda: self.llm.call(prompt))

        # 也可以直接：raw = self.llm.call(prompt)
        # raw 类似：'["planning", "creative"]'
        raw = await asyncio.to_thread(self.llm.call, [
            {"role": "system", "content": "你只做路由，只输出 Python 列表。"},
            {"role": "user", "content": prompt},
        ])

        print(f"\n HostAgent Thinking select agent: \n{raw}")
        agents = self._parse_agents(raw)

        # # 数据分析相关关键词
        # if any(kw in message.lower() for kw in ["data", "analyze", "statistics", "csv", "excel", "json"]):
        #     agents.append("data")
        # # 规划相关关键词
        # if any(kw in message.lower() for kw in ["plan", "schedule", "task", "timeline", "project"]):
        #     agents.append("planning")
        # # 创意相关关键词
        # if any(kw in message.lower() for kw in ["create", "generate", "write", "story", "content"]):
        #     agents.append("creative")
        # # 没有命中任何专长时，三个都调用
        # if not agents:
        #     agents = ["data", "planning", "creative"]

        return agents

    def _parse_agents(self,raw: str) -> List[str]:
        """从大模型的回复中解析出智能体类型列表。
        Args:
            raw: 大模型的原始回复
        Returns:
            智能体类型列表

        ## 输出格式（必须严格遵守）
        只输出一个 Python 列表，不要解释：
        ```python
        ["data"]
        或
        ["planning", "creative", "data"]
        """
        match = re.search(r"\[.*?\]", raw, re.S)
        if not match:
            return ["simple_agent"]

        try:
            agents = ast.literal_eval(match.group(0))
        except (ValueError, SyntaxError):
            return ["simple_agent"]
        allowed = set(self.agent_urls)

        return list(dict.fromkeys(a for a in agents if isinstance(a, str) and a in allowed)) or ["simple_agent"]

    async def _call_agent(self, agent_type: str, message: str, context: TaskTenantContext,
                          metadata: Optional[Dict[str, Any]] = None,
                          progress_callback: Optional[Callable[[dict], Awaitable[None]]] = None) -> Dict[str, Any]:
        """调用一个专长智能体。

        Args:
            agent_type: 智能体类型
            message: 发给该智能体的消息
            context: 租户上下文
            metadata: 任务元数据

        Returns:
            该智能体的响应
        """
        agent_url = self.agent_urls.get(agent_type)
        if not agent_url:
            return {
                "agent_type": agent_type,
                "success": False,
                "response": f"Agent {agent_type} not available",
                "artifacts": []
            }

        try:
            # 向智能体发送任务
            # 第一步：单次请求（普通 await）
            task = await self.client.send_task(agent_url, message, context=context, metadata=metadata)

            # 订阅任务更新（用于流式进度）
            final_response = task
            # 第二步：流式订阅（async for）
            async for update in self.client.subscribe_to_task(agent_url, task.id, user_id=context.user_id):
                final_response = update
                print(f"{agent_type} Agent Thinking: {update}")
                if progress_callback:
                    await progress_callback({"type": "progress", "stage": "agent_update",
                                             "agent_type": agent_type, "state": update.status.state.value,
                                             "message": f"{agent_type}: {update.status.state.value}"})

            # 取最终结果
            # 提取回复文本：收集全部文本片段，避免丢失多段回复
            text_parts = []
            if (final_response.status.message and
                final_response.status.message.parts):
                for part in final_response.status.message.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
            response_text = "\n\n".join(text_parts) if text_parts else "No response"

            return {
                "agent_type": agent_type,
                "success": final_response.status.state == TaskState.COMPLETED,
                "response": response_text,
                "artifacts": final_response.artifacts
            }

        except Exception as e:
            return {
                "agent_type": agent_type,
                "success": False,
                "response": f"Error calling {agent_type} agent: {str(e)}",
                "artifacts": []
            }

    async def _consolidate_results(
        self,
        original_message: str,
        results: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """汇总多个智能体的结果。

        Args:
            original_message: 用户原始消息
            results: 各专长智能体的结果

        Returns:
            汇总后的回复
        """
        # 完整实现里会用 ADK/LLM 生成连贯回复
        # 这里先用简单模板拼接做演示

        prompt = DEFAULT_CONSOLIDATE_PROMPT.format(
            question=original_message,
            agent_results=self._fromat_agent_results(results),
        )
        try:
            # raw = self.llm.call([
            #     {"role": "system", "content": "你只做路由，只输出 Python 列表。"},
            #     {"role": "user", "content": prompt},
            # ])
            messages = [
                {"role": "system", "content": "你只做汇总，只输出 Markdown 格式。"},
                {"role": "user", "content": prompt},
            ]
            if progress_callback and hasattr(self.llm, "stream_invoke"):
                loop = asyncio.get_running_loop()

                def collect_stream():
                    chunks = []
                    for chunk in self.llm.stream_invoke(messages):
                        chunks.append(chunk)
                        asyncio.run_coroutine_threadsafe(
                            progress_callback({"type": "delta", "content": chunk}), loop
                        ).result()
                    return "".join(chunks)

                markdown = await asyncio.to_thread(collect_stream)
            else:
                markdown = await asyncio.to_thread(self.llm.call, messages)
            # markdown = await asyncio.to_thread(lambda: self.llm.call(prompt))
            print(f"\n大模型汇总结果：\n{markdown}")
            return {"response" : (markdown or "").strip()}

        except Exception as e:
            consolidated_text = "Here's what I found:\n\n"
            for result in results:
                agent_type = result.get("agent_type", "unknown")
                success = result.get("success", False)
                response = result.get("response", "No response")
                artifacts = result.get("artifacts", [])
                if success:
                    consolidated_text += f"**{agent_type.capitalize()} Agent**:\n{response}\n\n"
                    if artifacts:
                        consolidated_text += f"*{len(artifacts)} artifacts produced*\n\n"
                else:
                    consolidated_text += f"**{agent_type.capitalize()} Agent**: Unable to complete task\n\n"
            consolidated_text +=f"\n(consolidated LLM failed:{e})_"
            return {
                "response": consolidated_text.strip()
            }

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

    def run(self):
        """启动智能体服务。"""
        import uvicorn

        # 先做智能体发现
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(self.startup())

        # 再启动 HTTP 服务
        uvicorn.run(self.app, host=self.host, port=self.port)

