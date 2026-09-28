"""Tests for Jev Service integration across all 4 scenarios."""
import pytest
from backend.app.core.jev_service import JevService
from backend.app.tools.builtin.terminal_tool import TerminalTool


def test_jev_pre_analyze_request_fallback():
    jev = JevService()
    # 1. 复杂工程开发需求
    res1 = jev.pre_analyze_request("请帮我重构用户认证模块，支持 OAuth2 和多租户隔离")
    assert res1["task_type"] == "full_engineering"
    assert res1["needs_scout"] is True
    assert res1["complexity"] >= 0.7

    # 2. 简单速问
    res2 = jev.pre_analyze_request("什么是 asyncio.to_thread？")
    assert res2["task_type"] == "simple_qa"
    assert res2["needs_scout"] is False

    # 3. 审查与质检
    res3 = jev.pre_analyze_request("请对以下代码进行审查和测试验证")
    assert res3["task_type"] == "code_review"


def test_jev_evaluate_memory_update():
    jev = JevService()
    # 触发记忆保存
    res = jev.evaluate_memory_update("请记住我喜欢使用 Python 3.12 并且以后默认开启严格类型提示", "好的，我已经记录了您的偏好。")
    assert res is not None
    assert res["should_remember"] is True
    assert res["memory_type"] == "semantic"

    # 无需记忆的普通问答
    no_mem = jev.evaluate_memory_update("今天天气怎么样", "今天天气晴朗")
    assert no_mem is None


def test_jev_evaluate_note_update():
    jev = JevService()
    # 包含技术蓝图与施工图纸的产出
    detailed_blueprint = (
        "## 架构调研与工程实施蓝图\n\n"
        "### 1. 调研发现\n"
        "现有项目结构采用 FastAPI 分层架构...\n\n"
        "### 2. 施工图纸\n"
        "- 步骤1: 修改 auth.py 引入 JWT 校验\n"
        "- 步骤2: 编写 test_auth.py 进行单元测试验证\n"
        "这里是一段超过两百五十个字符的详细工程设计说明，以便验证笔记提取规则能够成功捕捉到高质量的架构决策或施工图纸资产。"
    )
    res = jev.evaluate_note_update("请给出认证模块设计方案", detailed_blueprint)
    assert res is not None
    assert res["should_record_note"] is True
    assert res["category"] in ("task_blueprint", "architecture_decision")


def test_jev_security_guardrail_blocks_dangerous_commands(tmp_path):
    jev = JevService()

    # 1. 破坏性命令拦截
    safe, reason = jev.check_security("terminal_command", "rm -rf /", str(tmp_path))
    assert safe is False
    assert "高危指令硬拦截" in reason

    # 2. 叉子炸弹拦截
    safe, reason = jev.check_security("terminal_command", ":(){ :|:& };:", str(tmp_path))
    assert safe is False

    # 3. 敏感路径越权拦截
    safe, reason = jev.check_security("terminal_command", "cat /etc/shadow", str(tmp_path))
    assert safe is False
    assert "沙箱越权拦截" in reason

    # 4. 正常命令放行
    safe, reason = jev.check_security("terminal_command", "pytest tests/", str(tmp_path))
    assert safe is True


def test_terminal_tool_integrates_jev_security(tmp_path):
    terminal = TerminalTool(workspace=str(tmp_path))

    # 执行高危指令被拦截
    output = terminal.run({"command": "rm -rf /"})
    assert "❌ 安全拦截" in output

    # 正常命令放行
    output_ok = terminal.run({"command": "echo hello_jev"})
    assert "hello_jev" in output_ok
