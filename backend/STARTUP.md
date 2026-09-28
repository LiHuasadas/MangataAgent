# MangataAgent 服务启动说明

本系统现已提供与统一的多智能体启动方式（根目录 `main.py` 与 `run_ui.py`），完全免除繁琐配置。

---

## 推荐启动方式

### 1. 一键启动所有智能体集群（推荐）
在项目根目录下直接运行：
```powershell
python main.py --agent all
```
或连同前端 Web UI 一起拉起：
```powershell
python main.py --agent all --with-ui
```
按 `Ctrl+C` 可一键安全退出所有子智能体。

---

### 2. 分别在独立终端启动（单体调试模式）

在不同终端分别执行：
```powershell
# 终端 1: 架构与规划 Agent
python main.py --agent plan_solve --port 8001

# 终端 2: 主力编码 Agent
python main.py --agent react --port 8002

# 终端 3: 代码审查 Agent
python main.py --agent reflection --port 8003

# 终端 4: 敏捷直答 Agent
python main.py --agent simple --port 8004

# 终端 5: 主机编排网关
python main.py --agent host --port 8000

# 终端 6: 前端 Web 界面
python run_ui.py --port 5173
```

---

## 环境变量说明

`backend/.env` 已预设默认通信令牌：
```env
A2A_SERVICE_TOKEN=mangata-secret-token-2026
A2A_HOST=127.0.0.1
A2A_PORT=8000
```
各独立终端进程自动读取共享令牌，无需手动传参或担心鉴权失败。
