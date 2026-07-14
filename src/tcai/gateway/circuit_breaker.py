"""
TCAI Gateway — circuit breaker (4-dimensional).

Dimensions: rate, block, reject, score.
When a session exceeds thresholds, the circuit opens and blocks all further ops.
"""
from __future__ import annotations

import time

from .session_context import SessionContext, CircuitState
from .config import config
from . import logging_setup

logger = logging_setup.get_logger(__name__)


def check(
    ctx: SessionContext,
    verdict: str,
    tool_name: str = "",
) -> str:
    """Check an operation verdict against circuit breaker thresholds.

    Args:
        ctx: Session context with circuit state.
        verdict: Operation verdict: "safe", "risky", or "blocked".
        tool_name: Tool name for logging.

    Returns:
        "ok" if passed, "blocked" if circuit is open.
    """
    state = ctx.circuit

    # Auto-expire stale locked circuits (save age BEFORE updating last_activity)
    if state.locked:
        age = time.monotonic() - state.last_activity
        if age > config.circuit_stale_seconds:
            state.locked = False
            state.lock_reason = ""
            state.risky_count = 0
            state.blocked_count = 0
            state.cumulative_score = 0
            logger.info(
                f"Circuit auto-expired after {age:.0f}s",
                extra={"session_id": ctx.session_id},
            )

    state.last_activity = time.monotonic()

    # If already locked, no further operations allowed
    if state.locked:
        return "blocked"

    match verdict:
        case "risky":
            state.risky_count += 1
            state.cumulative_score += 10
        case "blocked":
            state.blocked_count += 1
            state.cumulative_score += 25
        case "safe":
            pass  # Safe ops don't count against limits

    # Check thresholds
    if state.risky_count > config.risky_rate_limit:
        state.locked = True
        state.lock_reason = (
            f"RISKY rate limit exceeded ({state.risky_count} > "
            f"{config.risky_rate_limit})"
        )
        logger.warning(
            f"Circuit breaker OPEN: {state.lock_reason}",
            extra={"session_id": ctx.session_id, "tool": tool_name},
        )
        return "blocked"

    if state.blocked_count >= config.blocked_limit:
        state.locked = True
        state.lock_reason = (
            f"BLOCKED limit reached ({state.blocked_count} >= "
            f"{config.blocked_limit})"
        )
        logger.warning(
            f"Circuit breaker OPEN: {state.lock_reason}",
            extra={"session_id": ctx.session_id, "tool": tool_name},
        )
        return "blocked"

    if state.cumulative_score >= config.score_lock_threshold:
        state.locked = True
        state.lock_reason = (
            f"Cumulative risk score exceeded ({state.cumulative_score} >= "
            f"{config.score_lock_threshold})"
        )
        logger.warning(
            f"Circuit breaker OPEN: {state.lock_reason}",
            extra={"session_id": ctx.session_id, "tool": tool_name},
        )
        return "blocked"

    return "ok"


def is_open(ctx: SessionContext) -> bool:
    """Check if the circuit breaker is currently open (locked)."""
    return ctx.circuit.locked


def get_reason(ctx: SessionContext) -> str:
    """Get the reason why the circuit is open, or empty string if closed."""
    return ctx.circuit.lock_reason if ctx.circuit.locked else ""

