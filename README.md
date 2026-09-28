# MangataAgent 多智能体协同开发平台

MangataAgent 是一个基于 **A2A（Agent-to-Agent）协议** 与 **FastAPI** 构建的分布式多智能体协作系统。系统采用总控编排（Host Agent）+ 专长分工（Specialist Agents）的微服务架构，支持多角色协同开发、工具调用、记忆检索与前端实时交互。

---

## 🌟 系统架构

```
               [ 前端 Web UI (Vite + React) : 5173 ]
                                 │
                                 ▼ (HTTP / SSE)
            [ 主机编排网关 (Host Agent Gateway) : 8000 ]
                                 │
                ┌────────────────┼────────────────┬────────────────┐
                │ (A2A 协议)     │                │                │
                ▼                ▼                ▼                ▼
       [ Plan & Solve ]       [ ReAct ]      [ Reflection ]     [ Simple ]
         (架构与侦察)         (主力编码)       (审查与测试)      (敏捷直答)
           : 8001               : 8002           : 8003           : 8004
                │                │                │                │
                └────────────────┴────────────────┴────────────────┘
                                 │
                    [ 共享基础设施与工具集 ]
             (Redis 会话锁 / Qdrant 向量库 / Neo4j 知识图谱 / MCP 工具)
```

### 智能体角色分工

| 智能体 | 监听端口 | 角色定位 | 核心职责 |
| :--- | :--- | :--- | :--- |
| **Host Agent** | `8000` | 总控架构师与网关 | 意图分析、工作流流水线编排、多智能体产物聚合交付 |
| **Plan & Solve Agent** | `8001` | 架构师与侦察兵 | 官方文档检索、代码现状探查、输出技术方案与施工蓝图 |
| **ReAct Agent** | `8002` | 主力建造工程师 | 依据蓝图进行多步推理、真实代码编写、动态调试与报错自愈 |
| **Reflection Agent** | `8003` | QA 质检与审查员 | 代码安全与规范审查、执行测试用例验证 |
| **Simple Agent** | `8004` | 敏捷开发助手 | 概念速查、语法解释、单点轻量工具调用 |

---

## 🚀 快速上手与运行系统

系统支持两种灵活的启动方式：**方式 1（分别启动独立组件，便于单体开发与断点调试）** 与 **方式 2（一键启动全部智能体集群，最推荐日常使用）**。

### 方式 1：分别启动各个组件（单体调试模式）

在不同终端分别执行各组件的启动命令：

1. **启动架构规划智能体（Plan & Solve）**：
   ```bash
   python main.py --agent plan_solve --port 8001
   ```

2. **启动主力编码智能体（ReAct）**：
   ```bash
   python main.py --agent react --port 8002
   ```

3. **启动代码审查智能体（Reflection）**：
   ```bash
   python main.py --agent reflection --port 8003
   ```

4. **启动轻量直答智能体（Simple）**：
   ```bash
   python main.py --agent simple --port 8004
   ```

5. **启动主机编排网关（Host Agent Gateway）**：
   ```bash
   python main.py --agent host --port 8000
   ```

6. **启动前端 Web UI**：
   ```bash
   python run_ui.py --port 5173
   ```

> 💡 **参数覆盖提示**：命令行支持随时指定模型与接口，例如：
> ```bash
> python main.py --agent simple --model qwen-plus --port 8004
> ```

---

### 方式 2：一次性启动所有智能体（推荐开发模式）

在项目根目录下只需一条命令，即可一键在后台多进程拉起所有 4 个专长智能体与 1 个 Host 网关：

```bash
python main.py --agent all
```

如果希望**连同前端 Web 界面一起一键拉起**，只需附加 `--with-ui` 参数：

```bash
python main.py --agent all --with-ui
```

- 系统会自动为各 Agent 分配标准端口（8000 ~ 8004）并完成探活。
- 按键盘 **`Ctrl + C`** 即可一键安全停止所有服务进程，无残留孤儿进程。

---

## 🌐 访问地址清单

- **Web 前端交互界面**：[http://localhost:5173](http://localhost:5173)
- **Host 网关 Swagger 接口文档**：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **各智能体 AgentCard 发现接口**：
  - Plan & Solve: `http://127.0.0.1:8001/.well-known/agent.json`
  - ReAct: `http://127.0.0.1:8002/.well-known/agent.json`
  - Reflection: `http://127.0.0.1:8003/.well-known/agent.json`
  - Simple: `http://127.0.0.1:8004/.well-known/agent.json`

---

## ⚙️ 环境配置说明

核心配置位于 `backend/.env`：

- **LLM 配置**：`LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL`
- **A2A 服务通信令牌**：`A2A_SERVICE_TOKEN=mangata-secret-token-2026`（多终端启动时共享鉴权）
- **Redis 会话数据库**：`CHAT_REDIS_URL=redis://127.0.0.1:6378/0`
- **向量与图数据库（可选）**：`QDRANT_URL`、`NEO4J_URI`
