"""Jev 决策服务 - 基于 TypeSafe AI System One 的极速结构化决策层与安全护栏。"""
from __future__ import annotations

import os
import re
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

try:
    from typesafe_sdk import TypeSafeClient, Choice, Noul, Score
    HAS_TYPESAFE = True
except ImportError:
    HAS_TYPESAFE = False


class JevService:
    """提供基于 Jev 的前置意图分析、后置记忆/笔记智能分流与高危操作安全护栏。"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY", "")
        env_enabled = os.getenv("JEV_ENABLED", "true").lower() in ("true", "1", "yes")
        self.enabled = env_enabled and bool(self.api_key) and HAS_TYPESAFE

    # -------------------------------------------------------------
    # 场景 1：HostAgent 执行前的前置意图分析与元数据打标
    # -------------------------------------------------------------
    def pre_analyze_request(self, question: str) -> Dict[str, Any]:
        """在 HostAgent 规划前，用毫秒级响应给出结构化意图分析，注入上下文。"""
        if not self.enabled:
            return self._fallback_pre_analyze(question)

        try:
            with TypeSafeClient(api_key=self.api_key) as client:
                resp = client.system_one(
                    state=f"用户需求: {question}",
                    questions={
                        "task_type": Choice(
                            instructions="用户请求的工程类型是什么？",
                            criteria={
                                "simple_qa": "概念咨询、语法释义、无须写代码的简单问答",
                                "full_engineering": "需要新增功能、编写多文件、完整重构的复杂工程开发任务",
                                "quick_fix": "单文件修改、局部调试或快速补丁",
                                "code_review": "纯代码审查、漏洞分析或运行测试自验",
                                "architecture_planning": "纯架构设计方案、技术选型与分步规划"
                            }
                        ),
                        "complexity": Score(
                            instructions="任务的复杂度和波及面有多高？",
                            criteria=["简单单点 (低)", "中等跨文件 (中)", "复杂全系统 (高)"]
                        ),
                        "needs_scout": Noul(
                            instructions="是否需要前置查阅官方第三方文档或探查现有工程代码？"
                        )
                    }
                )
                task_type = resp.answers["task_type"].choice
                complexity_score = float(resp.answers["complexity"].score)
                needs_scout = bool(resp.answers["needs_scout"].noul > 0.5)

                return {
                    "task_type": task_type,
                    "complexity": complexity_score,
                    "needs_scout": needs_scout,
                    "source": "jev_system_one"
                }
        except Exception as e:
            print(f"⚠️ Jev 调用异常，切换至规则兜底: {e}")
            return self._fallback_pre_analyze(question)

    def _fallback_pre_analyze(self, question: str) -> Dict[str, Any]:
        """无 Jev Key 或离线时的确定性启发式规则兜底。"""
        text = question.strip()
        # 1. 纯审查
        if any(k in text for k in ["审查", "code review", "测试验证", "跑测试", "质检", "自审"]):
            return {"task_type": "code_review", "complexity": 0.5, "needs_scout": False, "source": "rule_fallback"}
        # 2. 简单速问
        if len(text) < 30 and any(k in text for k in ["什么是", "怎么用", "解释", "含义", "你好", "hello"]):
            return {"task_type": "simple_qa", "complexity": 0.2, "needs_scout": False, "source": "rule_fallback"}
        # 3. 架构规划
        if any(k in text for k in ["设计方案", "架构规划", "技术选型", "方案设计"]):
            return {"task_type": "architecture_planning", "complexity": 0.7, "needs_scout": True, "source": "rule_fallback"}
        # 4. 复杂工程开发
        return {"task_type": "full_engineering", "complexity": 0.8, "needs_scout": True, "source": "rule_fallback"}

    # -------------------------------------------------------------
    # 场景 2：大模型输出后，自动判定是否调用 memory_tool
    # -------------------------------------------------------------
    def evaluate_memory_update(self, prompt: str, response: str) -> Optional[Dict[str, Any]]:
        """判定本轮对话是否产生了需要持久化的用户专属偏好、项目事实或硬性约束。"""
        if not self.enabled:
            return self._fallback_evaluate_memory(prompt, response)

        try:
            with TypeSafeClient(api_key=self.api_key) as client:
                resp = client.system_one(
                    state=f"用户输入: {prompt}\n助手回复: {response[:1500]}",
                    questions={
                        "should_remember": Noul(
                            instructions="该交互是否包含用户专属偏好、项目固有约束、关键技术栈或后续会话必须记忆的事实？"
                        ),
                        "memory_type": Choice(
                            instructions="最适合的记忆类型是什么？",
                            criteria={
                                "working": "当前会话的短期目标与进行中状态",
                                "semantic": "通用的事实、技术栈版本或硬性业务规则",
                                "episodic": "具体发生过的问题与解决经历"
                            }
                        )
                    }
                )
                prob = float(resp.answers["should_remember"].noul)
                if prob > 0.65:
                    return {
                        "should_remember": True,
                        "memory_type": resp.answers["memory_type"].choice,
                        "confidence": prob,
                        "source": "jev_system_one"
                    }
                return None
        except Exception as e:
            print(f"⚠️ Jev 记忆判定异常: {e}")
            return self._fallback_evaluate_memory(prompt, response)

    def _fallback_evaluate_memory(self, prompt: str, response: str) -> Optional[Dict[str, Any]]:
        """记忆规则兜底。"""
        combined = (prompt + " " + response).lower()
        if any(k in combined for k in ["记住", "请记住", "偏好", "我的名字", "以后默认", "项目规范要求"]):
            return {"should_remember": True, "memory_type": "semantic", "confidence": 0.8, "source": "rule_fallback"}
        return None

    # -------------------------------------------------------------
    # 场景 3：大模型输出后，自动判定是否调用 note_tool 沉淀笔记
    # -------------------------------------------------------------
    def evaluate_note_update(self, prompt: str, response: str) -> Optional[Dict[str, Any]]:
        """判定本轮交互是否产出了值得沉淀为 project_notes 的架构决策或技术资产。"""
        if not self.enabled:
            return self._fallback_evaluate_note(prompt, response)

        try:
            with TypeSafeClient(api_key=self.api_key) as client:
                resp = client.system_one(
                    state=f"用户任务: {prompt}\n执行成果: {response[:2000]}",
                    questions={
                        "should_record_note": Noul(
                            instructions="是否产出了架构设计决策(ADR)、完整的排错根因分析或阶段性施工蓝图？"
                        ),
                        "note_category": Choice(
                            instructions="属于哪种工程笔记？",
                            criteria={
                                "architecture_decision": "架构选型与系统设计决策说明",
                                "troubleshooting_log": "严重 Bug 的定位与修复记录",
                                "task_blueprint": "详细的开发施工图纸与接口定义"
                            }
                        )
                    }
                )
                prob = float(resp.answers["should_record_note"].noul)
                if prob > 0.68:
                    return {
                        "should_record_note": True,
                        "category": resp.answers["note_category"].choice,
                        "confidence": prob,
                        "source": "jev_system_one"
                    }
                return None
        except Exception as e:
            print(f"⚠️ Jev 笔记判定异常: {e}")
            return self._fallback_evaluate_note(prompt, response)

    def _fallback_evaluate_note(self, prompt: str, response: str) -> Optional[Dict[str, Any]]:
        """笔记规则兜底。"""
        if len(response) > 50 and any(k in response for k in ["架构调研与工程实施蓝图", "施工图纸", "架构决策", "修复日志", "Bug根因"]):
            cat = "task_blueprint" if "施工图纸" in response else "architecture_decision"
            return {"should_record_note": True, "category": cat, "confidence": 0.75, "source": "rule_fallback"}
        return None

    # -------------------------------------------------------------
    # 场景 4：终端与文件高危操作安全护栏
    # -------------------------------------------------------------
    def check_security(self, action_type: str, payload: str, workspace_root: str) -> Tuple[bool, str]:
        """毫秒级检测命令或文件操作是否具有破坏性或逃逸租户沙箱。"""
        payload_lower = payload.lower().strip()

        # 1. 本地硬编码高危特征瞬间熔断 (0ms)
        high_risk_patterns = [
            r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f*|-f[a-zA-Z]*r[a-zA-Z]*)\s+(/|/\*|[a-zA-Z]:\\|\*)",
            r":\(\)\s*\{\s*:\|:&\s*\};:",  # fork 炸弹
            r"\bmkfs\b",
            r"\bdd\s+if=/dev/",
            r"chmod\s+-R\s+777\s+/",
            r"del\s+/[fF]\s+/[sS]\s+/[qQ]\s+[cC]:\\",
            r"rmdir\s+/[sS]\s+/[qQ]\s+[cC]:\\",
            r"\bformat\s+[a-zA-Z]:",
            r"\b(curl|wget)\s+.*\|\s*(bash|sh)\b",
        ]
        for pattern in high_risk_patterns:
            if re.search(pattern, payload_lower):
                return False, f"高危指令硬拦截：检测到不可逆系统破坏行为"

        # 2. 跨目录逃逸检测 (越权读取敏感密钥/配置文件)
        escape_targets = [
            "/etc/shadow", "/etc/passwd", "~/.ssh", "/root",
            "c:\\windows\\system32", "id_rsa", "id_ed25519"
        ]
        for target in escape_targets:
            if target in payload_lower:
                return False, f"沙箱越权拦截：禁止访问租户工作区外部敏感路径 '{target}'"

        # 3. 若配置了 Jev，执行毫秒级模型语义安全仲裁
        if self.enabled:
            try:
                with TypeSafeClient(api_key=self.api_key) as client:
                    resp = client.system_one(
                        state=f"操作类型: {action_type}\n执行参数: {payload}\n允许的租户工作区路径: {workspace_root}",
                        questions={
                            "is_dangerous": Noul(
                                instructions="该操作是否试图逃逸出租户工作区、篡改宿主机关键文件、下载执行恶意反弹shell或具有系统破坏性？"
                            )
                        }
                    )
                    prob = float(resp.answers["is_dangerous"].noul)
                    if prob > 0.60:
                        return False, f"Jev 安全护栏拦截：操作被判定为高危操作（风险置信度: {prob:.2f}）"
            except Exception as e:
                print(f"⚠️ Jev 安全审查异常，已按本地硬规则放行: {e}")

        return True, "放行"
