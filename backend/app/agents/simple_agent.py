"""简单Agent实现 - 基于OpenAI原生API"""
import json
from pathlib import Path
from typing import Optional, Iterator, TYPE_CHECKING
import re

from ..context import ContextBuilder, ContextConfig
from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message
from ..protocols.types import AgentCard, Capabilities, Skill
from ..tools.builtin import MemoryTool, RAGTool, NoteTool, TerminalTool, SearchTool, MCPTool
from ..tools.registry import ToolRegistry

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry

class SimpleAgent(Agent):
    """简单的对话Agent，支持可选的工具调用"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional['ToolRegistry'] = None,
        enable_tool_calling: bool = True,
        user_id: Optional[str] = None,
        knowledge_base_path: Optional[str] = "./kb",  # 👈 新增参数
        rag_namespace: Optional[str] = "reports",  # 👈 对应导入时的命名空间
        workspace: Optional[str] = "./project_notes",
        host: str = "localhost",
        port: int = 8004,
        **kwargs  # 👈 接收额外参数
    ):
        """
        初始化SimpleAgent
        
        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词
            config: 配置对象
            tool_registry: 工具注册表（可选，如果提供则启用工具调用）
            enable_tool_calling: 是否启用工具调用（只有在提供tool_registry时生效）
        """

        # 创建智能体名片
        agent_card = AgentCard(
            name="Simple Agent",
            description="对话与工具调用",
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
        self.tool_registry = tool_registry or ToolRegistry()
        self.enable_tool_calling = enable_tool_calling

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
                max_tokens=8000,  # 总预算
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

    def _get_enhanced_system_prompt(self) -> str:
        """构建增强的系统提示词，包含工具信息"""
        base_prompt = self.system_prompt or "你是一个有用的AI助手。"

        if not self.enable_tool_calling or not self.tool_registry:
            return base_prompt

        # 获取工具描述
        tools_description = self.tool_registry.get_tools_description()
        if not tools_description or tools_description == "暂无可用工具":
            return base_prompt

        tools_section = "\n\n## 可用工具\n"
        tools_section += "你可以使用以下工具来帮助回答问题：\n"
        tools_section += tools_description + "\n"

        tools_section += "\n## 工具调用格式\n"
        tools_section += "当需要使用工具时，请使用以下格式：\n"
        tools_section += "`[TOOL_CALL:{tool_name}:{parameters}]`\n\n"

        tools_section += "### 参数格式说明\n"
        tools_section += "1. **多个参数**：使用 `key=value` 格式，用逗号分隔\n"
        tools_section += "   示例：`[TOOL_CALL:calculator_multiply:a=12,b=8]`\n"
        tools_section += "   示例：`[TOOL_CALL:filesystem_read_file:path=README.md]`\n\n"
        tools_section += "2. **单个参数**：直接使用 `key=value`\n"
        tools_section += "   示例：`[TOOL_CALL:search:query=Python编程]`\n\n"
        tools_section += "3. **简单查询**：可以直接传入文本\n"
        tools_section += "   示例：`[TOOL_CALL:search:Python编程]`\n\n"

        tools_section += "### 重要提示\n"
        tools_section += "- 参数名必须与工具定义的参数名完全匹配\n"
        tools_section += "- 数字参数直接写数字，不需要引号：`a=12` 而不是 `a=\"12\"`\n"
        tools_section += "- 文件路径等字符串参数直接写：`path=README.md`\n"
        tools_section += "- 工具调用结果会自动插入到对话中，然后你可以基于结果继续回答\n"

        return base_prompt + tools_section

    def _parse_tool_calls(self, text: str) -> list:
        """解析文本中的工具调用"""
        pattern = r'\[TOOL_CALL:([^:]+):([^\]]+)\]'
        matches = re.findall(pattern, text)

        tool_calls = []
        for tool_name, parameters in matches:
            tool_calls.append({
                'tool_name': tool_name.strip(),
                'parameters': parameters.strip(),
                'original': f'[TOOL_CALL:{tool_name}:{parameters}]'
            })

        return tool_calls

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """执行工具调用"""
        if not self.tool_registry:
            return f"❌ 错误：未配置工具注册表"

        try:
            # 获取Tool对象
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                parsed = self._parse_tool_parameters(tool_name, parameters)
                result = self.tool_registry.execute_tool(
                    tool_name, json.dumps(parsed, ensure_ascii=False)
                )
                return f"🔧 工具 {tool_name} 执行结果：\n{result}"

            # 智能参数解析
            param_dict = self._parse_tool_parameters(tool_name, parameters)

            # 调用工具
            result = tool.run(param_dict)
            return f"🔧 工具 {tool_name} 执行结果：\n{result}"

        except Exception as e:
            return f"❌ 工具调用失败：{str(e)}"

    def _parse_tool_parameters(self, tool_name: str, parameters: str) -> dict:
        """智能解析工具参数"""
        import json
        param_dict = {}

        # 尝试解析JSON格式
        if parameters.strip().startswith('{'):
            try:
                param_dict = json.loads(parameters)
                # JSON解析成功，进行类型转换
                param_dict = self._convert_parameter_types(tool_name, param_dict)
                return param_dict
            except json.JSONDecodeError:
                # JSON解析失败，继续使用其他方式
                pass

        if '=' in parameters:
            # 格式: key=value 或 action=search,query=Python
            if ',' in parameters:
                # 多个参数：action=search,query=Python,limit=3
                pairs = parameters.split(',')
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        param_dict[key.strip()] = value.strip()
            else:
                # 单个参数：key=value
                key, value = parameters.split('=', 1)
                param_dict[key.strip()] = value.strip()

            # 类型转换
            param_dict = self._convert_parameter_types(tool_name, param_dict)

            # 智能推断action（如果没有指定）
            if 'action' not in param_dict:
                param_dict = self._infer_action(tool_name, param_dict)
        else:
            # 直接传入参数，根据工具类型智能推断
            param_dict = self._infer_simple_parameters(tool_name, parameters)

        return param_dict

    def _convert_parameter_types(self, tool_name: str, param_dict: dict) -> dict:
        """
        根据工具的参数定义转换参数类型

        Args:
            tool_name: 工具名称
            param_dict: 参数字典

        Returns:
            类型转换后的参数字典
        """
        if not self.tool_registry:
            return param_dict

        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return param_dict

        # 获取工具的参数定义
        try:
            tool_params = tool.get_parameters()
        except:
            return param_dict

        # 创建参数类型映射
        param_types = {}
        for param in tool_params:
            param_types[param.name] = param.type

        # 转换参数类型
        converted_dict = {}
        for key, value in param_dict.items():
            if key in param_types:
                param_type = param_types[key]
                try:
                    if param_type == 'number' or param_type == 'integer':
                        # 转换为数字
                        if isinstance(value, str):
                            converted_dict[key] = float(value) if param_type == 'number' else int(value)
                        else:
                            converted_dict[key] = value
                    elif param_type == 'boolean':
                        # 转换为布尔值
                        if isinstance(value, str):
                            converted_dict[key] = value.lower() in ('true', '1', 'yes')
                        else:
                            converted_dict[key] = bool(value)
                    else:
                        converted_dict[key] = value
                except (ValueError, TypeError):
                    # 转换失败，保持原值
                    converted_dict[key] = value
            else:
                converted_dict[key] = value

        return converted_dict

    def _infer_action(self, tool_name: str, param_dict: dict) -> dict:
        """根据工具类型和参数推断action"""
        if tool_name == 'memory':
            if 'recall' in param_dict:
                param_dict['action'] = 'search'
                param_dict['query'] = param_dict.pop('recall')
            elif 'store' in param_dict:
                param_dict['action'] = 'add'
                param_dict['content'] = param_dict.pop('store')
            elif 'query' in param_dict:
                param_dict['action'] = 'search'
            elif 'content' in param_dict:
                param_dict['action'] = 'add'
        elif tool_name == 'rag':
            if 'search' in param_dict:
                param_dict['action'] = 'search'
                param_dict['query'] = param_dict.pop('search')
            elif 'query' in param_dict:
                param_dict['action'] = 'search'
            elif 'text' in param_dict:
                param_dict['action'] = 'add_text'

        return param_dict

    def _infer_simple_parameters(self, tool_name: str, parameters: str) -> dict:
        """为简单参数推断完整的参数字典"""
        if tool_name == 'rag':
            return {'action': 'search', 'query': parameters}
        elif tool_name == 'memory':
            return {'action': 'search', 'query': parameters}
        else:
            return {'input': parameters}

    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """
        运行SimpleAgent，支持可选的工具调用
        
        Args:
            input_text: 用户输入
            max_tool_iterations: 最大工具调用迭代次数（仅在启用工具时有效）
            **kwargs: 其他参数
            
        Returns:
            Agent响应
        """
        # 构建消息列表
        messages = []

        # 添加系统消息（可能包含工具信息）
        enhanced_system_prompt = self._get_enhanced_system_prompt()
        messages.append({"role": "system", "content": enhanced_system_prompt})

        # 添加历史消息
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})

        # 添加当前用户消息
        messages.append({"role": "user", "content": input_text})

        # 如果没有启用工具调用，使用原有逻辑
        if not self.enable_tool_calling:
            response = self.llm.invoke(messages, **kwargs)
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(response, "assistant"))
            return response

        # 迭代处理，支持多轮工具调用
        current_iteration = 0
        final_response = ""

        while current_iteration < max_tool_iterations:
            """
                2、structure optimized_context use ContextBuild
            """
            optimized_context = self.context_builder.build(
                user_query= input_text + "\n" + "\n".join(
                    str(message["content"]) for message in messages[-2:]
                ),
                conversation_history= self._history,
                system_instructions= enhanced_system_prompt
            )

            # 调用LLM
            response = self.llm.invoke([{"role": "user", "content": optimized_context}], **kwargs) or ""

            # 检查是否有工具调用
            tool_calls = self._parse_tool_calls(response)

            if tool_calls:
                # 执行所有工具调用并收集结果
                tool_results = []
                clean_response = response

                for call in tool_calls:
                    result = self._execute_tool_call(call['tool_name'], call['parameters'])
                    tool_results.append(result)
                    # 从响应中移除工具调用标记
                    clean_response = clean_response.replace(call['original'], "")

                # 构建包含工具结果的消息
                messages.append({"role": "assistant", "content": clean_response})

                # 添加工具结果
                tool_results_text = "\n\n".join(tool_results)
                messages.append({"role": "user", "content": f"工具执行结果：\n{tool_results_text}\n\n请基于这些结果给出完整的回答。"})

                current_iteration += 1
                continue

            # 没有工具调用，这是最终回答
            final_response = response
            break

        # 如果超过最大迭代次数，获取最后一次回答
        if current_iteration >= max_tool_iterations and not final_response:
            final_response = self.llm.invoke(messages + [{"role": "user", "content": "请根据已执行的工具结果给出最终回答，不再调用工具。"}], **kwargs) or ""

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_response, "assistant"))

        return final_response

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


    def remove_tool(self, tool_name: str) -> bool:
        """移除工具（便利方法）"""
        if self.tool_registry:
            return self.tool_registry.unregister_tool(tool_name)
        return False

    def list_tools(self) -> list:
        """列出所有可用工具"""
        if self.tool_registry:
            return self.tool_registry.list_tools()
        return []

    def has_tools(self) -> bool:
        """检查是否有可用工具"""
        return self.enable_tool_calling and self.tool_registry is not None

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """
        流式运行Agent；启用工具时先完成工具调用，再输出最终回答。
        
        Args:
            input_text: 用户输入
            **kwargs: 其他参数
            
        Yields:
            Agent响应片段
        """
        if self.enable_tool_calling:
            yield self.run(input_text, **kwargs)
            return

        # 构建消息列表
        messages = []

        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": input_text})

        # 流式调用LLM
        full_response = ""
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full_response += chunk
            yield chunk

        # 保存完整对话到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(full_response, "assistant"))
