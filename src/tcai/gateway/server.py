"""
TCAI Gateway — MCP JSON-RPC server (stdio transport).

Entry point for the gateway subprocess. Communicates with the Agent
process over stdin/stdout using JSON-RPC 2.0 protocol.

Handles:
  - initialize / notifications/initialized
  - tools/list
  - tools/call (routes to readonly or write enforcement)
  - tools/approve (replay approved write operations)
  - knowledge search (FTS5 via knowledge_bridge)
"""
from __future__ import annotations

import json
import sys
from typing import Any

from . import tool_registry
from . import gateway as _gateway
from . import logging_setup
from .session_context import get_session, reset_session

logger = logging_setup.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# JSON-RPC helpers
# ═══════════════════════════════════════════════════════════════════════


def _ok(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON-RPC success response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    """Build a JSON-RPC error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _send(response: dict[str, Any]) -> None:
    """Write a JSON-RPC response to stdout."""
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════
# Request handlers
# ═══════════════════════════════════════════════════════════════════════


def _handle_initialize(request_id: Any, params: dict[str, Any]) -> None:
    """Handle MCP initialize request."""
    _send(_ok(request_id, {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "TCAI Gateway",
            "version": "6.0.0",
        },
        "capabilities": {
            "tools": {},
        },
    }))


def _handle_tools_list(request_id: Any, _params: dict[str, Any]) -> None:
    """Handle MCP tools/list request."""
    schemas = tool_registry.get_tool_schemas()
    _send(_ok(request_id, {"tools": schemas}))


def _handle_tools_call(request_id: Any, params: dict[str, Any]) -> None:
    """Handle MCP tools/call request.

    Routes to readonly (DLP only) or write (full 6-step pipeline).
    """
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
    session_id = arguments.pop("_session_id", "default")

    # Find handler
    handler = tool_registry.get_handler(tool_name)
    if handler is None:
        _send(_ok(request_id, {
            "content": [{"type": "text", "text": json.dumps({
                "status": "error",
                "message": f"Unknown tool: {tool_name}",
            }, ensure_ascii=False)}],
        }))
        return

    # Route based on tool type
    try:
        if tool_registry.is_readonly(tool_name):
            result = _gateway.enforce_readonly(
                tool_name, arguments, session_id, execute_fn=handler,
            )
        else:
            result = _gateway.enforce_write(
                tool_name, arguments, session_id, execute_fn=handler,
            )
    except Exception as e:
        logger.error(f"Tool call failed: {tool_name}: {e}", exc_info=True)
        result = {"status": "error", "message": str(e)}

    _send(_ok(request_id, {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
    }))


def _handle_tools_approve(request_id: Any, params: dict[str, Any]) -> None:
    """Handle MCP tools/approve request.

    Replays an approved write operation that was previously held for approval.
    """
    approval_id = params.get("approval_id", "")
    session_id = params.get("_session_id", "default")

    # Approvals are managed through the session context
    ctx = get_session(session_id)
    pending = ctx.pending_approvals.get(approval_id)

    if pending is None:
        from . import audit as _audit
        _audit.log_decision(
            session_id=session_id, tool="approve", params=params,
            verdict="error", reason=f"Approval not found: {approval_id}", level="approval_error",
        )
        _send(_ok(request_id, {
            "content": [{"type": "text", "text": json.dumps({
                "status": "error",
                "message": f"Approval not found: {approval_id}",
            }, ensure_ascii=False)}],
        }))
        return

    # Mark as approved
    pending["status"] = "approved"

    # Replay the operation (route to enforce_readonly or enforce_write)
    tool_name = pending.get("tool_name", "")
    arguments = pending.get("params", {})

    try:
        handler = tool_registry.get_handler(tool_name)
        if handler is None:
            result = {"status": "error", "message": f"Unknown tool: {tool_name}"}
        elif tool_registry.is_readonly(tool_name):
            result = _gateway.enforce_readonly(
                tool_name, arguments, session_id, execute_fn=handler,
            )
        else:
            result = _gateway.enforce_write(
                tool_name, arguments, session_id, execute_fn=handler,
            )
    except Exception as e:
        result = {"status": "error", "message": str(e)}

    del ctx.pending_approvals[approval_id]

    _send(_ok(request_id, {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
    }))


def _handle_reset(request_id: Any, params: dict[str, Any]) -> None:
    """Handle MCP tools/reset request — reset session state."""
    session_id = params.get("_session_id", "default")
    reset_session(session_id)
    _send(_ok(request_id, {"status": "ok", "message": "Session reset"}))


def _handle_knowledge_search(request_id: Any, params: dict[str, Any]) -> None:
    """Handle knowledge base FTS5 search."""
    query = params.get("query", "")
    limit = params.get("limit", 5)

    try:
        from .knowledge_bridge import search as kb_search
        results = kb_search(query, limit=limit)
        _send(_ok(request_id, {
            "content": [{"type": "text", "text": json.dumps({
                "status": "ok",
                "query": query,
                "count": len(results),
                "results": results,
            }, ensure_ascii=False)}],
        }))
    except Exception as e:
        _send(_ok(request_id, {
            "content": [{"type": "text", "text": json.dumps({
                "status": "error",
                "message": str(e),
            }, ensure_ascii=False)}],
        }))


# ═══════════════════════════════════════════════════════════════════════
# Method router
# ═══════════════════════════════════════════════════════════════════════

_METHOD_MAP: dict[str, Any] = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
    "tools/approve": _handle_tools_approve,
    "tools/reset": _handle_reset,
    "knowledge/search": _handle_knowledge_search,
}


# ═══════════════════════════════════════════════════════════════════════
# Main loop
# ═══════════════════════════════════════════════════════════════════════


def mcp_main() -> None:
    """MCP JSON-RPC main loop — reads stdin, writes stdout.

    This is the entry point for the gateway subprocess.
    Never returns; runs until stdin closes or process is terminated.

    Usage:
        python run_gateway.py
    """
    # Initialize logging
    logging_setup.setup_logging()

    # Ensure stdout uses UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

    logger.info("TCAI 网关 v6.0.0 启动中")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"stdin JSON 解析失败: {e}")
            _send(_error(None, -32700, "Parse error"))
            continue

        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        # Handle notifications (no id field) — fire and forget
        if request_id is None and method == "notifications/initialized":
            logger.info("MCP 客户端已初始化")
            continue

        # Route to handler
        handler = _METHOD_MAP.get(method)
        if handler is None:
            logger.warning(f"未知方法: {method}")
            _send(_error(request_id, -32601, f"未知方法: {method}"))
            continue

        try:
            handler(request_id, params)
        except Exception as e:
            logger.error(f"处理 {method} 时出错: {e}", exc_info=True)
            # Log to audit trail for forensic traceability
            from . import audit
            audit.log_decision(
                session_id=params.get("_session_id", params.get("arguments", {}).get("_session_id", "unknown")),
                tool=params.get("name", method),
                params=params,
                verdict="error",
                reason=f"服务器内部错误: {e}",
                level="fatal_error",
                exit_code=-1,
            )
            _send(_error(request_id, -32603, "服务器内部错误"))

    logger.info("TCAI 网关已关闭")


if __name__ == "__main__":
    mcp_main()
