"""
TCAI Agent — terminal UI (Chinese localization).
"""
from __future__ import annotations

import sys


class UI:
    """TCAI Agent terminal interface."""

    def banner(self, session_id: str, model: str) -> None:
        """Print startup banner."""
        print()
        print("  ==========================================")
        print("   TCAI v6 — AI 诊断助手")
        print("   Windows 网吧无盘环境专用")
        print("  ------------------------------------------")
        print(f"   会话: {session_id}    模型: {model}")
        print("  ==========================================")
        print()
        print("  输入 /help 查看命令，/exit 退出")
        print()

    def prompt(self) -> str:
        """Read user input."""
        try:
            return input("  网管: ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    def response(self, text: str) -> None:
        """Print AI response."""
        print(f"\n  {text}\n")

    def status(self, msg: str) -> None:
        """Print status message."""
        sys.stderr.write(f"  [{msg}]\n")

    def error(self, msg: str) -> None:
        """Print error message."""
        sys.stderr.write(f"  [错误] {msg}\n")

    def help(self) -> None:
        """Print help text."""
        print("""
  命令:
    /help           显示帮助
    /exit           退出
    /new            开始新会话
    /machine <机号>  设置机器编号
    /learn <路径>    从会话日志提取知识

  直接输入故障描述即可开始诊断。
  例如：英雄联盟崩溃报错 3A 怎么解决？
""")

