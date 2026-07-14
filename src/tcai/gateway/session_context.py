"""
TCAI Gateway — unified session context.

Replaces the scattered module-level mutable globals across 5 modules.
A single SessionContext instance holds all session-scoped state.

Modules receive a SessionContext via dependency injection instead of
managing their own module-level dicts.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CircuitState:
    """State for a single circuit breaker session."""

    risky_count: int = 0
    blocked_count: int = 0
    reject_count: int = 0
    cumulative_score: int = 0
    locked: bool = False
    lock_reason: str = ""
    last_activity: float = field(default_factory=time.monotonic)


@dataclass
class SessionStack:
    """Operation stack for intent chain tracking."""

    operations: list[dict[str, Any]] = field(default_factory=list)
    max_size: int = 50


@dataclass
class SessionGuard:
    """Tool loop guard state for a single session."""

    call_history: list[dict[str, Any]] = field(default_factory=list)
    batch_count: int = 0


@dataclass
class SessionContext:
    """Aggregated state for one diagnostic session.

    All security modules read/write this context instead of
    maintaining separate module-level mutable globals.
    """

    session_id: str

    # Circuit breaker state
    circuit: CircuitState = field(default_factory=CircuitState)

    # Operation stack for intent chain tracking
    op_stack: SessionStack = field(default_factory=SessionStack)

    # Tool loop guard state
    loop_guard: SessionGuard = field(default_factory=SessionGuard)

    # Pending approval requests (approval_id → request dict)
    pending_approvals: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Approved operations cache (key → approval dict)
    approved_ops: dict[str, dict[str, Any]] = field(default_factory=dict)

    def reset(self) -> None:
        """Reset all session-scoped state (called on /new)."""
        self.circuit = CircuitState()
        self.op_stack = SessionStack()
        self.loop_guard = SessionGuard()
        self.pending_approvals.clear()
        # Note: approved_ops intentionally NOT cleared —
        # approvals persist across /new for the same session

    def cleanup_stale_approvals(self, max_age_seconds: float = 3600.0) -> int:
        """Remove approval entries older than max_age_seconds.

        Returns:
            Number of entries removed.
        """
        now = time.monotonic()
        stale_keys = [
            k for k, v in self.approved_ops.items()
            if now - v.get("_timestamp", 0) > max_age_seconds
        ]
        for k in stale_keys:
            del self.approved_ops[k]
        return len(stale_keys)


# ═══════════════════════════════════════════════════════════════════════
# Session registry
# ═══════════════════════════════════════════════════════════════════════

# Module-level registry of active sessions (keyed by session_id)
# This is the ONLY module-level mutable state in the project
_sessions: dict[str, SessionContext] = {}


def get_session(session_id: str) -> SessionContext:
    """Get or create a SessionContext for the given session ID."""
    if session_id not in _sessions:
        _sessions[session_id] = SessionContext(session_id=session_id)
    return _sessions[session_id]


def remove_session(session_id: str) -> None:
    """Remove a session from the registry (cleanup)."""
    _sessions.pop(session_id, None)


def reset_session(session_id: str) -> SessionContext:
    """Reset a session and return the fresh context."""
    ctx = get_session(session_id)
    ctx.reset()
    return ctx

