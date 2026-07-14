"""
TCAI exception hierarchy — structured, typed error handling.

All TCAI-specific exceptions inherit from TCAIError.
This replaces the inconsistent {"status": "error", "reason"/"message": str} pattern.

Usage:
    from tcai.gateway.exceptions import SecurityBlockedError
    raise SecurityBlockedError("system_path_write", path="C:\\Windows\\System32\\hosts")
"""
from __future__ import annotations


class TCAIError(Exception):
    """Base exception for all TCAI errors."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(TCAIError):
    """Invalid or missing configuration.

    Raised when required env vars are missing or config values are invalid.
    This is fatal — the application cannot start.
    """


class SecurityBlockedError(TCAIError):
    """Operation blocked by security gateway.

    Raised when the 6-step security pipeline rejects an operation.
    Includes details about which rule/step triggered the block.

    Attributes:
        rule: The name of the security rule that triggered the block.
        path: The file path that was blocked (if applicable).
        level: The AST level (safe/risky/blocked).
    """

    def __init__(
        self,
        message: str = "",
        *,
        rule: str = "",
        path: str = "",
        level: str = "blocked",
    ) -> None:
        super().__init__(message)
        self.rule = rule
        self.path = path
        self.level = level

    def to_result(self) -> dict[str, str]:
        """Convert to the standard MCP error result dict."""
        return {
            "status": "blocked",
            "verdict": self.level,
            "message": self.message,
            "rule": self.rule,
        }


class CircuitBreakerOpenError(TCAIError):
    """Circuit breaker has opened for the session.

    Raised when the session has exceeded rate limits, block limits,
    or score thresholds. The session must be reset or expire.
    """

    def __init__(self, message: str = "", *, reason: str = "") -> None:
        super().__init__(message)
        self.reason = reason


class ToolExecutionError(TCAIError):
    """A diagnostic tool failed during execution.

    This is the base for tool-related failures; it covers
    command failures, network errors, and resource unavailability.

    Attributes:
        tool_name: The name of the tool that failed.
        original_error: The underlying exception (if any).
    """

    def __init__(
        self,
        message: str = "",
        *,
        tool_name: str = "",
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.tool_name = tool_name
        self.original_error = original_error

    def to_result(self) -> dict[str, str]:
        """Convert to standard MCP tool error result."""
        return {
            "status": "error",
            "message": self.message,
        }


class ToolTimeoutError(ToolExecutionError):
    """Tool execution timed out."""


class ToolNotFoundError(ToolExecutionError):
    """The requested tool does not exist."""


class ValidationError(TCAIError):
    """Input validation failed.

    Raised when user input or LLM output fails validation checks
    (e.g., invalid path format, disallowed characters).
    """

    def __init__(
        self,
        message: str = "",
        *,
        field: str = "",
        value: str = "",
    ) -> None:
        super().__init__(message)
        self.field = field
        self.value = value


def error_result(message: str, *, status: str = "error") -> dict[str, str]:
    """Create a standardized error result dict.

    This is the canonical way to return errors from tool functions.
    All error results use "message" (not "reason") for consistency.

    Args:
        message: Human-readable error description.
        status: Result status ("error" or "blocked").

    Returns:
        Dict with "status" and "message" keys.
    """
    return {"status": status, "message": message}

