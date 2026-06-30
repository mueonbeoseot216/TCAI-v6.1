"""
TCAI Agent — zero-token security monitor (Observer + Adapter pattern).

Monitors LLM responses for tool call patterns without consuming tokens.
The Observer inspects tool calls; the Adapter enforces limits.
"""
from __future__ import annotations


class ToolAdapter:
    """Counts and limits tool calls per-conversation for the LLM-facing API."""

    def __init__(self) -> None:
        self._web_search_count: int = 0
        self._max_web_search: int = 3

    def record_web_search(self) -> None:
        """Record a web_search tool call."""
        self._web_search_count += 1

    def can_web_search(self) -> bool:
        """Check if web search limit has been reached."""
        return self._web_search_count < self._max_web_search

    def get_web_search_remaining(self) -> int:
        """Get remaining web search quota."""
        return max(0, self._max_web_search - self._web_search_count)

    def reset_counts(self) -> None:
        """Reset all counters for a new diagnosis."""
        self._web_search_count = 0


class PromptGate:
    """Zero-token security monitor for LLM interactions.

    The Observer inspects each tool call before execution.
    The Adapter enforces per-conversation tool call limits.
    """

    def __init__(self) -> None:
        self.adapter = ToolAdapter()
        self._alert_count: int = 0

    def inspect_tool_call(self, tool_name: str, arguments: dict) -> tuple[bool, str]:
        """Inspect a tool call before execution.

        Args:
            tool_name: Name of the tool being called.
            arguments: Tool arguments dict.

        Returns:
            (allowed_bool, warning_message_string)
        """
        # Web search rate limiting
        if tool_name == "web_search":
            if not self.adapter.can_web_search():
                return False, (
                    "Web search limit reached for this diagnosis. "
                    "Use local tools instead."
                )
            self.adapter.record_web_search()

        # Check for suspicious patterns (zero-token inspection)
        warnings: list[str] = []

        args_str = str(arguments).lower()
        suspicious_keywords = [
            "format c:", "del /f", "rm -rf", "drop table",
            "shutdown", "restart",
        ]
        for keyword in suspicious_keywords:
            if keyword in args_str:
                self._alert_count += 1
                warnings.append(f"Suspicious keyword detected: {keyword}")

        warning_msg = "; ".join(warnings) if warnings else ""
        return True, warning_msg

    def reset(self) -> None:
        """Reset state for a new session."""
        self.adapter.reset_counts()
        self._alert_count = 0
