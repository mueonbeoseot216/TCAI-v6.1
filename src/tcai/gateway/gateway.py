"""
TCAI Gateway — 5-step security pipeline orchestrator.

All write-tool operations pass through this pipeline before reaching the system:
  1. Scope Check     — path restrictions (C: block, UNC block)
  2. Deobfuscation   — anti-bypass (4-stage normalization)
  3. AST Rules       — allowlist/blocklist matching
  4. Circuit Breaker — rate/block/reject/score check
  5. Dispatch        — SAFE execute / RISKY approve / BLOCKED reject

This module orchestrates the pipeline; each step delegates to its
specialized module.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable

from . import scope_checker
from . import deobfuscate
from . import ast_rules
from . import circuit_breaker
from . import audit
from . import logging_setup
from .session_context import SessionContext, get_session
from .exceptions import SecurityBlockedError
from .ast_rules import Level

logger = logging_setup.get_logger(__name__)

# Tool name → Action string mapping (for AST rule matching)
TOOL_ACTION_MAP: dict[str, str] = {
    "file_write": "FileWrite",
    "file_delete": "FileDelete",
    "file_read": "FileRead",
    "reg_write": "RegistryWrite",
    "reg_delete_value": "RegistryDelete",
    "service_control": "ServiceControl",
    "process_kill": "ProcessTerminate",
    "firewall_rule": "FirewallRule",
    "disk_check": "DiskCheck",
    "system_file_scan": "SystemFileScan",
    "dism_health": "DismHealth",
}


def _get_action(tool_name: str) -> str:
    """Map a tool name to its AST action type."""
    return TOOL_ACTION_MAP.get(tool_name, tool_name)


def enforce_write(
    tool_name: str,
    params: dict[str, Any],
    session_id: str,
    *,
    execute_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Run a write-tool operation through the full 6-step security pipeline.

    §1.1 exemption: security pipeline orchestrator — coordinates 6 steps
    spanning scope, deobfuscation, AST rules, circuit breaker, and dispatch.
    """

    Args:
        tool_name: Name of the tool being called.
        params: Tool parameters (raw, before deobfuscation).
        session_id: Session identifier.
        execute_fn: The tool's execute function (called if SAFE verdict).

    Returns:
        Tool result dict with status, verdict, and result data.
    """
    ctx = get_session(session_id)

    # ── Step 0: Circuit breaker pre-check ──
    if circuit_breaker.is_open(ctx):
        audit.log_decision(
            session_id=session_id,
            tool=tool_name,
            params=params,
            verdict="blocked",
            reason=f"Circuit breaker open: {circuit_breaker.get_reason(ctx)}",
            level="circuit_blocked",
        )
        return {
            "status": "blocked",
            "verdict": "blocked",
            "reason": circuit_breaker.get_reason(ctx),
        }

    # ── Step 1: Scope Check ──
    path = params.get("path", params.get("key", ""))
    if path:
        normalized_path = scope_checker.normalize_path(str(path))
        allowed, reason = scope_checker.check_scope(normalized_path)
        if not allowed:
            audit.log_decision(
                session_id=session_id,
                tool=tool_name,
                params=params,
                verdict="blocked",
                reason=f"Scope check: {reason}",
                level="scope_blocked",
            )
            circuit_breaker.check(ctx, "blocked", tool_name)
            return {
                "status": "blocked",
                "verdict": "blocked",
                "reason": f"Scope blocked: {reason}",
            }
        # Update path with normalized version
        if "path" in params:
            params["path"] = normalized_path

    # ── Step 2: Deobfuscation ──
    try:
        normalized_params = deobfuscate.normalize(tool_name, params)
    except SecurityBlockedError as e:
        audit.log_decision(
            session_id=session_id,
            tool=tool_name,
            params=params,
            verdict="blocked",
            reason=f"Deobfuscation: {e.message}",
            level="deobfuscate_blocked",
        )
        circuit_breaker.check(ctx, "blocked", tool_name)
        return e.to_result()

    # ── Step 3: AST Rule Matching ──
    action = _get_action(tool_name)
    target = normalized_params.get("path", normalized_params.get("key", ""))
    target_name = normalized_params.get("name", "")

    level, reason = ast_rules.match(
        action=str(action),
        target=str(target),
        sub_action=normalized_params.get("action", ""),
        target_name=str(target_name),
    )

    match level:
        case Level.BLOCKED:
            audit.log_decision(
                session_id=session_id,
                tool=tool_name,
                params=normalized_params,
                verdict="blocked",
                reason=reason,
                level="ast_blocked",
            )
            circuit_breaker.check(ctx, "blocked", tool_name)
            return {
                "status": "blocked",
                "verdict": "blocked",
                "reason": reason,
            }
        case Level.RISKY:
            # RISKY operations require human approval
            circuit_breaker.check(ctx, "risky", tool_name)
            approval_id = str(uuid.uuid4())
            ctx.pending_approvals[approval_id] = {
                "tool_name": tool_name,
                "params": normalized_params,
                "status": "pending",
            }
            audit.log_decision(
                session_id=session_id,
                tool=tool_name,
                params=normalized_params,
                verdict="risky",
                reason=reason,
                level="ast_risky",
                approval_id=approval_id,
            )
            return {
                "status": "needs_approval",
                "verdict": "pending_approval",
                "reason": reason,
                "approval_id": approval_id,
                "params": normalized_params,
            }

    # Level.SAFE — fall through to execution
    logger.info(
        f"SAFE: {tool_name}({_summarize_params(normalized_params)})",
        extra={"session_id": session_id},
    )

    # ── Step 4: Circuit Breaker ──
    breaker_result = circuit_breaker.check(ctx, "safe", tool_name)
    if breaker_result == "blocked":
        audit.log_decision(
            session_id=session_id,
            tool=tool_name,
            params=normalized_params,
            verdict="blocked",
            reason=f"Circuit breaker tripped: {circuit_breaker.get_reason(ctx)}",
            level="circuit_blocked",
        )
        return {
            "status": "blocked",
            "verdict": "blocked",
            "reason": circuit_breaker.get_reason(ctx),
        }

    # ── Step 5: Dispatch (Execute) ──
    try:
        result = execute_fn(**normalized_params)
    except (OSError, ValueError, TypeError) as e:
        audit.log_decision(
            session_id=session_id,
            tool=tool_name,
            params=normalized_params,
            verdict="error",
            reason=str(e),
            level="execution_error",
            exit_code=-1,
        )
        return {"status": "error", "message": str(e)}

    audit.log_decision(
        session_id=session_id,
        tool=tool_name,
        params=normalized_params,
        verdict="safe",
        reason="Operation completed successfully",
        level="safe",
    )

    return result


def enforce_readonly(
    tool_name: str,
    params: dict[str, Any],
    session_id: str,
    *,
    execute_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Run a read-only tool through security checks.

    Read-only tools are inherently safe but still require:
      - DLP for sensitive file paths (file_read)
      - Injection filter for web content (web_search)
      - Audit logging for all readonly tool calls

    Args:
        tool_name: Name of the tool being called.
        params: Tool parameters.
        session_id: Session identifier.
        execute_fn: The tool's execute function.

    Returns:
        Tool result dict.
    """
    # ── Web search specific: query validation ──
    if tool_name == "web_search":
        query = str(params.get("query", "")).strip()
        if not query:
            return {"status": "error", "message": "Search query is empty"}
        # Check for injection patterns in the query itself
        from . import injection_filter
        filter_result = injection_filter.filter_text(query, source="user_search_query")
        if filter_result["blocked"]:
            audit.log_decision(
                session_id=session_id,
                tool=tool_name,
                params=params,
                verdict="blocked",
                reason=f"Injection filter blocked query: {filter_result['flags']}",
                level="injection_blocked",
            )
            return {
                "status": "blocked",
                "verdict": "blocked",
                "reason": f"Search query blocked by injection filter: {filter_result['flags']}",
            }

    # ── DLP check for sensitive paths ──
    path = params.get("path", "")
    key_path = params.get("key", "")
    check_path = str(path or key_path)

    if check_path and tool_name in ("file_read", "reg_query", "file_search"):
        from . import dlp
        level, reason, is_sensitive = dlp.check_sensitive(check_path)
        if is_sensitive and level == Level.RISKY:
            approval_id = str(uuid.uuid4())
            ctx.pending_approvals[approval_id] = {
                "tool_name": tool_name,
                "params": params,
                "status": "pending",
            }
            audit.log_decision(
                session_id=session_id,
                tool=tool_name,
                params=params,
                verdict="risky",
                reason=f"DLP: {reason}",
                level="dlp_risky",
                approval_id=approval_id,
            )
            return {
                "status": "needs_approval",
                "verdict": "pending_approval",
                "reason": f"DLP: {reason}",
                "approval_id": approval_id,
            }

    # ── Execute ──
    try:
        result = execute_fn(**params)
    except (OSError, ValueError, TypeError) as e:
        audit.log_decision(
            session_id=session_id,
            tool=tool_name,
            params=params,
            verdict="error",
            reason=str(e),
            level="execution_error",
            exit_code=-1,
        )
        return {"status": "error", "message": str(e)}

    # ── Audit log ──
    audit.log_decision(
        session_id=session_id,
        tool=tool_name,
        params=params,
        verdict="safe",
        reason="Read-only operation completed",
        level="safe",
    )

    return result


def _summarize_params(params: dict[str, Any]) -> str:
    """Create a short parameter summary for logging."""
    items = []
    for k, v in params.items():
        s = str(v)
        if len(s) > 60:
            s = s[:57] + "..."
        items.append(f"{k}={s}")
    return ", ".join(items[:5])  # Max 5 params in log
