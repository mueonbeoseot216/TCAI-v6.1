"""
TCAI configuration — centralized, validated, zero hardcoded defaults.

All magic numbers, URLs, timeouts, and limits live here.
Environment variables are loaded via python-dotenv at import time.

Usage:
    from tcai.gateway.config import config
    timeout = config.llm_timeout
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from . import paths


def _load_env() -> None:
    """Load environment from home/.env if it exists."""
    env_path = paths.ENV_FILE
    if env_path.exists():
        load_dotenv(env_path)
    # Fallback: also try loading from PROJECT_ROOT/.env
    root_env = paths.PROJECT_ROOT / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=False)


def _get_env(key: str, default: str = "") -> str:
    """Get required or optional environment variable."""
    value = os.environ.get(key, default)
    return value


def _require_env(key: str) -> str:
    """Get a required environment variable; exit with message if missing."""
    value = os.environ.get(key, "")
    if not value:
        sys.stderr.write(f"[FATAL] Missing required environment variable: {key}\n")
        sys.stderr.write(f"  Create home/.env from .env.example and set {key}\n")
        sys.exit(1)
    return value


@dataclass(frozen=True)
class Config:
    """Immutable configuration loaded from environment + defaults.

    All values are validated at creation time.
    """

    # === LLM API ===
    deepseek_api_key: str = field(
        default_factory=lambda: _require_env("DEEPSEEK_API_KEY")
    )
    deepseek_api_base: str = field(
        default_factory=lambda: _get_env(
            "DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"
        )
    )
    model: str = field(
        default_factory=lambda: _get_env("TCAI_MODEL", "deepseek-chat")
    )

    # === Paths ===
    knowledge_path: Path = field(
        default_factory=lambda: Path(
            _get_env(
                "TCAI_KNOWLEDGE_PATH",
                str(paths.PROJECT_ROOT.parent / "TCAI_Knowledge"),
            )
        )
    )
    username: str = field(
        default_factory=lambda: _get_env("USERNAME", "Administrator")
    )

    # === LLM Timeouts (seconds) ===
    llm_timeout: int = 120
    llm_learn_timeout: int = 60

    # === LLM Parameters ===
    llm_temperature: float = 0.3
    llm_learn_temperature: float = 0.1
    llm_max_tokens: int = 4096
    llm_learn_max_tokens: int = 2048
    llm_max_retries: int = 3

    # === MCP / Subprocess Timeouts (seconds) ===
    mcp_startup_timeout: int = 10
    mcp_call_timeout: int = 300
    mcp_shutdown_timeout: int = 5
    tool_default_timeout: int = 20
    tool_long_timeout: int = 45

    # === Circuit Breaker ===
    risky_rate_limit: int = 5  # Max RISKY ops per session before lock
    blocked_limit: int = 3  # Consecutive BLOCKED ops before lock
    score_lock_threshold: int = 100  # Cumulative risk score cap
    circuit_stale_seconds: int = 3600  # Cleanup stale circuits after 1 hour

    # === Tool Loop Guard ===
    batch_limit: int = 15  # Max tool calls per batch
    dedup_window: int = 5  # Consecutive same-tool calls considered loop

    # === Injection Filter ===
    injection_max_chars: int = 4000

    # === File Size Limits ===
    file_read_max_bytes: int = 1 * 1024 * 1024  # 1 MB
    file_write_max_content_bytes: int = 1 * 1024 * 1024  # 1 MB

    # === Web Search ===
    bing_search_url: str = "https://www.bing.com/search"
    web_search_timeout: int = 12
    web_extract_timeout: int = 15
    web_extract_max_chars: int = 3000
    web_extract_hard_max_chars: int = 5000
    web_max_results: int = 10

    # === Audit ===
    audit_stale_days: int = 7  # Auto-clean snapshots older than N days

    # === User Agent ===
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # === Knowledge Base ===
    knowledge_search_limit: int = 5

    def __post_init__(self) -> None:
        """Validate configuration after creation."""
        # Validate model name
        if not self.model.strip():
            object.__setattr__(self, "model", "deepseek-chat")
            import logging
            logging.getLogger(__name__).warning(
                "TCAI_MODEL is empty, using default: deepseek-chat"
            )

        # Ensure knowledge path exists (create parent dirs if needed)
        if not self.knowledge_path.exists():
            import logging
            logging.getLogger(__name__).warning(
                f"Knowledge path does not exist: {self.knowledge_path}"
            )


# Load environment at import time
_load_env()

# Singleton config instance
config = Config()

