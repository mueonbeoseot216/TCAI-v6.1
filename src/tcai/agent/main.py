"""
TCAI v6 — Agent entry point.

Spawns the Gateway subprocess, initializes all modules, and runs the
interactive terminal loop.

Usage:
    python -m tcai.agent.main    (with src/ on PYTHONPATH)
"""
from __future__ import annotations

import os
import sys

from ..gateway.config import config
from .mcp_client import MCPClient
from .prompt_engine import PromptEngine
from .prompt_gate import PromptGate
from .session import Session
from .learn import LearnExtractor
from .loop import AgentLoop
from .ui import UI

def _clean_path(raw: str) -> str:
    """Strip quotes (Chinese + ASCII) and whitespace from a path string."""
    quotes = {
        '"', "'",
        '\u201c', '\u201d',
        '\u2018', '\u2019',
        '\uff02', '\uff07',
    }
    s = raw.strip()
    while s and (s[0] in quotes or s[-1] in quotes):
        if s[0] in quotes and s[-1] in quotes and s[0] == s[-1]:
            s = s[1:-1].strip()
        elif s[0] in quotes:
            s = s[1:].strip()
        elif s[-1] in quotes:
            s = s[:-1].strip()
        else:
            break
    return s

def main() -> None:
    """TCAI v6 main entry point."""
    ui = UI()

    ui.status("启动 MCP 网关中...")
    mcp = MCPClient()
    if not mcp.start():
        ui.error("无法启动 MCP 网关")
        sys.exit(1)

    ui.status("加载提示词引擎中...")
    prompt_engine = PromptEngine()

    ui.status("初始化知识库中...")
    session = Session()
    ui.status("初始化安全监视器中...")
    gate = PromptGate()

    learn_extractor = LearnExtractor()

    ui.status("启动 Agent 主循环中...")
    loop = AgentLoop(
        mcp, prompt_engine, gate, gate.adapter, session,
        knowledge_path=config.knowledge_path,
    )

    model = os.environ.get("TCAI_MODEL", "deepseek-chat")
    ui.banner(session.session_id, model)

    while True:
        try:
            user_input = ui.prompt()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if user_input == "/exit":
                break
            elif user_input == "/help":
                ui.help()
                continue
            elif user_input == "/new":
                session.reset()    # Generate new session ID first
                loop.reset()       # Then propagate new ID to gateway
                ui.status("会话已重置")
                continue
            elif user_input.startswith("/machine"):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 2:
                    session.set_machine(parts[1].strip())
                    ui.status(f"机号设置为 {parts[1].strip()}")
                else:
                    ui.status("用法: /machine <机号>")
                continue
            elif user_input.startswith("/learn"):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 2:
                    ui.status("从会话日志提取知识中...")
                    filepath = _clean_path(parts[1])
                    if not filepath:
                        ui.status("用法: /learn <会话日志路径>")
                    elif not os.path.isfile(filepath):
                        ui.status(f"文件不存在: {filepath}")
                    else:
                        result = learn_extractor.handle_learn(filepath)
                        ui.response(result)
                else:
                    ui.status("用法: /learn <会话日志路径>")
                continue
            else:
                ui.status(f"未知命令: {user_input}")
                continue

        ui.status("诊断中...")
        try:
            response = loop.run(user_input)
        except Exception:
            import logging
            logging.getLogger(__name__).critical("loop.run() fatal error", exc_info=True)
            response = "诊断异常，请重试或联系管理员。"
        ui.response(response)

    ui.status("保存会话记录中...")
    session.close()
    ui.status("关闭网关中...")
    mcp.stop()
    ui.status("再见")

if __name__ == "__main__":
    main()

