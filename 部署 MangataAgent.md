# MangataAgent 服务器生产部署指南

MangataAgent 是一个基于 **A2A（Agent-to-Agent）协议** 与 **FastAPI** 的多智能体协作系统。在服务器上部署的关键在于：
1. **多进程集群内部互联**（Host 网关 8000 与专长 Agent 8001~8004 端口）；
2. **中间件与知识引擎**（Redis 会话锁、Qdrant 向量检索库、Neo4j 图数据库）；
3. **前端反向代理与 AI SSE（Server-Sent Events）长连接流式打字机优化**。

---

## 🌟 推荐部署拓扑图

```
                [ 公网用户浏览器 ]
                        │
                        ▼ (HTTP 80 / HTTPS 443)
              ┌───────────────────┐
              │    Nginx 网关     │ (对外开放 80 / 443)
              └─────────┬─────────┘
                        │
       ┌────────────────┴────────────────┐
       ▼ (静态资源 /)                    ▼ (/api/ 转发)
[ 前端 Web UI (dist) ]      [ Host Agent 网关 : 8000 ]
                                         │
                        ┌────────────────┼────────────────┐ (A2A 内部通信)
                        ▼                ▼                ▼
                 [ Plan & Solve ]     [ ReAct ]     [ Reflection / Simple ]
                     : 8001            : 8002           : 8003 / 8004
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
 [ Redis : 6379 ]               [ Qdrant : 6333 ]               [ Neo4j : 7687/7474 ]
 (会话状态与分布式锁)            (向量长记忆库 & RAG)            (知识图谱与复杂关系推理)
```

> 🛡️ **安全规范**：云服务器安全组仅需放行 **80、443（及 SSH 22）**。各 Agent 端口（8000~8004）、Redis（6379）、Qdrant（6333）和 Neo4j（7687）**严禁向公网开放**，容器间通过 Docker 内部虚拟网络互联。

---

## 🚀 方案一：Docker Compose 一键容器化部署（强烈推荐）

所有组件（前端、后端集群、Redis、Qdrant、Neo4j）均已编排在根目录 [docker-compose.yml](file:///e:/PythonCode/Agent_project/MangataAgent/docker-compose.yml) 中。

### 1. 将代码拉取至服务器并配置 `.env`
```bash
cd MangataAgent
cp backend/.env.example backend/.env
vim backend/.env
```
生产环境关键参数示例：
```env
# 大模型 API 密钥
LLM_MODEL_ID=qwen-plus
LLM_API_KEY=sk-your-actual-api-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# A2A 服务通信令牌（生产环境请务必改为强随机密码）
A2A_SERVICE_TOKEN=your-random-production-secret-token-2026

# Qdrant 与 Neo4j 认证配置（需与 docker-compose.yml 一致）
QDRANT_API_KEY=hello-agents-key
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=12345
```

### 2. 一键构建并启动全套集群
```bash
# 启动包含 Redis, Qdrant, Neo4j, Backend 的服务（自动直接接入已有的 app-net 网络）
docker compose up -d --build
```
> 后端镜像已引入 **`uv`** 高性能包管理器，依赖下载与轮子安装仅需 10~20 秒。

### 3. 查看容器健康状态与日志
```bash
# 查看所有容器健康状态
docker compose ps

# 查看后端多智能体协同日志
docker compose logs -f backend

# 查看前端与反向代理访问日志
docker compose logs -f frontend
```

### 4. 服务访问与控制台地址
- **Web 前端应用**：`http://<服务器公网IP>`
- **Host Agent Swagger 接口文档**：`http://127.0.0.1:8000/docs`（服务器本地）
- **Qdrant 向量可视化控制台**：`http://127.0.0.1:6333/dashboard`（服务器本地）
- **Neo4j 浏览器控制台**：`http://127.0.0.1:7474`（用户名：`neo4j`，密码：`12345`）

---

## 🛠️ 方案二：Linux 宿主机裸机直接部署（uv + Systemd + Nginx）

若直接在物理机或云服务器 Linux 宿主机上运行：

### 1. 安装基础依赖与 `uv`
以 Ubuntu 22.04 / 24.04 为例：
```bash
# 安装基础系统库
sudo apt update && sudo apt install -y curl git nginx nodejs npm redis-server

# 安装 uv 高性能 Python 管理工具
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### 2. 使用 `uv` 安装 Python 3.11 并安装依赖
```bash
cd /opt/MangataAgent

# 自动拉取纯净 Python 3.11 并创建虚拟环境
uv venv .venv --python 3.11

# 极速秒级安装依赖
source .venv/bin/activate
uv pip install -r backend/requirements-agents.txt
```

### 3. 编译前端静态资源
```bash
cd /opt/MangataAgent/frontend
npm install
npm run build
# 打包产物位于 /opt/MangataAgent/frontend/dist
```

### 4. 配置 Systemd 托管多智能体集群
使用现成服务文件 [deploy/mangata-agent.service](file:///e:/PythonCode/Agent_project/MangataAgent/deploy/mangata-agent.service)：
```bash
sudo cp /opt/MangataAgent/deploy/mangata-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mangata-agent

# 查看运行状态
sudo systemctl status mangata-agent
```

### 5. 配置宿主机 Nginx（支持 SSE 流式长连接）
复制并使用已优化配置 [deploy/nginx.conf](file:///e:/PythonCode/Agent_project/MangataAgent/deploy/nginx.conf)：
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## ⚠️ 生产运维避坑与核心配置说明

### 1. Nginx SSE 打字机流式长连接防卡顿
AI 大模型长文本与多 Agent 协同思考必须配置如下 Nginx 参数，否则打字机效果会完全卡住并在结束时一次性刷出：
```nginx
proxy_buffering off;
proxy_cache off;
proxy_set_header X-Accel-Buffering no;
proxy_http_version 1.1;
proxy_set_header Connection "";
chunked_transfer_encoding on;
proxy_read_timeout 600s;
```

### 2. 持久化数据目录（宿主机 /data/mangata 挂载）
各容器的数据已统一直接映射到宿主机 `/data/mangata/` 目录下，便于备份与持久化：
- `/data/mangata/redis/`：Redis 会话状态与分布式锁数据
- `/data/mangata/qdrant/`：Qdrant 向量长记忆索引库
- `/data/mangata/neo4j/data/` 与 `logs/`：Neo4j 知识图谱数据库与运行日志
- `/data/mangata/project/`：智能体生成与编辑的代码工作区
- `/data/mangata/kb/`：知识库文档切片与离线报告
- `/data/mangata/memory_data/`：智能体情景反思记忆库
