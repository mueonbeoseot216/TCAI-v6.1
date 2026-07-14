"""
TCAI Agent — MCP stdio client.

Communicates with the Gateway subprocess via stdin/stdout JSON-RPC 2.0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from ..gateway.paths import PROJECT_ROOT


class MCPClient:
    """MCP stdio JSON-RPC client for Gateway communication."""

    def __init__(self) -> None:
        self._python: str = sys.executable
        self._gateway: Path = PROJECT_ROOT / "run_gateway.py"
        self._process: subprocess.Popen[str] | None = None
        self._request_id: int = 0
        self._tools: list[dict] = []
        self._initialized: bool = False
        self._stderr_thread: threading.Thread | None = None

    def start(self) -> bool:
        """Launch Gateway subprocess and complete MCP handshake."""
        if not self._gateway.exists():
            sys.stderr.write(f"[MCP] 网关脚本不存在: {self._gateway}\n")
            return False

        try:
            self._process = subprocess.Popen(
                [self._python, "-X", "utf8", "-u", str(self._gateway)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": str(PROJECT_ROOT / "src"),
                },
            )
        except (OSError, BrokenPipeError, RuntimeError) as e:
            sys.stderr.write(f"[MCP] 启动网关失败: {e}\n")
            return False

        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, daemon=True
        )
        self._stderr_thread.start()

        result = self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "tcai-v6", "version": "6.0"},
        })
        if result is None:
            return False

        self._send_notification("notifications/initialized", {})

        tools_result = self._send("tools/list", {})
        if tools_result and "tools" in tools_result:
            self._tools = tools_result["tools"]
            sys.stderr.write(f"[MCP] 已连接网关，{len(self._tools)} 个工具可用\n")

        self._initialized = True
        return True

    def stop(self) -> None:
        """Terminate the Gateway subprocess."""
        if self._process:
            try:
                self._process.stdin.close()
                self._process.stdout.close()
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except OSError:
                import logging
                logging.getLogger(__name__).warning("Gateway stop OSError", exc_info=True)
            self._process = None
        self._initialized = False

    def list_tools(self) -> list[dict]:
        """Return all available tool schemas."""
        return self._tools

    def get_tool_names(self) -> list[str]:
        """Return all tool names."""
        return [t["name"] for t in self._tools]

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool on the Gateway."""
        args = {**arguments, "_session_id": getattr(self, "_session_id", "default")}
        return self._send("tools/call", {
            "name": name,
            "arguments": args,
        }) or {"status": "error", "message": "网关无响应"}

    def approve(self, approval_id: str, approved: bool = True) -> dict:
        """Approve a pending operation."""
        return self._send("tools/approve", {
            "approval_id": approval_id,
            "approved": approved,
            "_session_id": getattr(self, "_session_id", "default"),
        }) or {"status": "error", "message": "审批请求失败"}

    def reset_session(self) -> dict:
        """Reset the Gateway session state."""
        return self._send("tools/reset", {
            "_session_id": getattr(self, "_session_id", "default"),
        }) or {"status": "error", "message": "重置失败"}

    def _drain_stderr(self) -> None:
        """Background thread: read gateway stderr to prevent pipe deadlock."""
        try:
            while self._process and self._process.poll() is None:
                line = self._process.stderr.readline()
                if not line:
                    break
                sys.stderr.write(f"[网关] {line.rstrip()}\n")
        except (OSError, BrokenPipeError):
            import logging
            logging.getLogger(__name__).warning("Gateway stderr drain pipe error", exc_info=True)

    def _send(self, method: str, params: dict) -> dict | None:
        """Send a JSON-RPC request and return the result."""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        try:
            line = json.dumps(request, ensure_ascii=False)
            self._process.stdin.write(line + "\n")
            self._process.stdin.flush()
        except (OSError, BrokenPipeError) as e:
            sys.stderr.write(f"[MCP] 写入失败: {e}\n")
            return None
        return self._read_response()

    def _send_notification(self, method: str, params: dict) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        try:
            line = json.dumps(request, ensure_ascii=False)
            self._process.stdin.write(line + "\n")
            self._process.stdin.flush()
        except (OSError, BrokenPipeError) as e:
            sys.stderr.write(f"[MCP] 通知发送失败: {e}\n")

    def _read_response(self) -> dict | None:
        """Read one JSON-RPC response line from gateway stdout."""
        if not self._process or self._process.stdout.closed:
            return None
        try:
            line = self._process.stdout.readline()
            if not line:
                return None
            response = json.loads(line.strip())
            if "error" in response:
                err = response["error"]
                sys.stderr.write(f"[MCP] 网关错误 {err.get('code')}: {err.get('message')}\n")
                return None
            result = response.get("result", {})
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        try:
                            return json.loads(item["text"])
                        except json.JSONDecodeError:
                            return {"text": item["text"]}
            return result
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[MCP] 网关返回无效 JSON: {e}\n")
            return None
        except (OSError, BrokenPipeError) as e:
            sys.stderr.write(f"[MCP] 读取响应失败: {e}\n")
            return None

    @property
    def is_running(self) -> bool:
        """Check if the Gateway subprocess is alive."""
        return (
            self._initialized
            and self._process is not None
            and self._process.poll() is None
        )

