"""
TCAI Gateway — Data Leak Prevention (DLP) module (security core).

Sensitive path detection + content sanitization.
Read-only tools pass through DLP review to prevent data exfiltration.

This module is the single entry point for DLP checks.
"""
from __future__ import annotations

import re
from typing import NamedTuple

from .ast_rules import Level, SENSITIVE_PATHS
from . import logging_setup

logger = logging_setup.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Sensitive path classification
# ═══════════════════════════════════════════════════════════════════════


class SensitivePath(NamedTuple):
    """A sensitive path pattern with human-readable description."""

    pattern: str
    description: str


def _classify_pattern(pattern: str) -> str:
    """Infer a human-readable category from a regex pattern."""
    mapping = {
        "ssh": "SSH private key",
        "id_rsa": "SSH private key",
        "id_ed25519": "SSH private key",
        "aws": "AWS credentials",
        "Chrome": "Browser password",
        "Edge": "Browser password",
        "Firefox": "Browser password",
        "SAM": "Windows security account",
        "SECURITY": "Windows security account",
        "Credential": "Windows credentials",
        "WebCache": "Browser cache (contains tokens)",
        "Wlansvc": "WiFi password",
        "rdp": "Remote desktop config",
        "OpenVPN": "VPN config",
        "WireGuard": "VPN config",
        "ConsoleHost": "PowerShell history",
        "minecraft": "Game data",
        "网吧": "Internet cafe management data",
        "计费": "Internet cafe billing data",
        ".env": "Credential file",
        ".pem": "Credential file",
        ".key": "Credential file",
    }
    for keyword, description in mapping.items():
        if keyword in pattern:
            return description
    return "Sensitive file"


SENSITIVE_PATH_PATTERNS: list[SensitivePath] = [
    SensitivePath(pattern=pat, description=_classify_pattern(pat))
    for pat in SENSITIVE_PATHS
]


# ═══════════════════════════════════════════════════════════════════════
# Path checking
# ═══════════════════════════════════════════════════════════════════════


def check_sensitive(path: str) -> tuple[Level, str, bool]:
    """Check if a path matches any sensitive path pattern.

    Args:
        path: File path to check.

    Returns:
        (Level, reason_string, is_sensitive_bool)
    """
    normalized = path.replace("/", "\\")

    for entry in SENSITIVE_PATH_PATTERNS:
        if re.match(entry.pattern, normalized, re.IGNORECASE):
            reason = f"Sensitive path: {entry.description} ({path})"
            logger.debug(f"DLP match: {reason}")
            return Level.RISKY, reason, True

    return Level.SAFE, "", False


def get_sensitive_description(path: str) -> str | None:
    """Get the human-readable description for a sensitive path, if matched.

    Args:
        path: File path to check.

    Returns:
        Description string, or None if not sensitive.
    """
    normalized = path.replace("/", "\\")
    for entry in SENSITIVE_PATH_PATTERNS:
        if re.match(entry.pattern, normalized, re.IGNORECASE):
            return entry.description
    return None


# ═══════════════════════════════════════════════════════════════════════
# Content sanitization
# ═══════════════════════════════════════════════════════════════════════

_IP_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)

_JWT_PATTERN: re.Pattern[str] = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
)

_API_KEY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:api[_-]?key|apikey|access[_-]?key|secret[_-]?key)"
        r'\s*[:=]\s*["\']?[A-Za-z0-9+/=_-]{20,}["\']?',
        re.IGNORECASE,
    ),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style
    re.compile(r"AKIA[A-Z0-9]{16}"),      # AWS Access Key
]

_PASSWORD_PATTERN: re.Pattern[str] = re.compile(
    r"""(?:password|passwd|pwd)\s*[:=]\s*["'][^"']+["']""",
    re.IGNORECASE,
)


def sanitize(content: str) -> str:
    """Sanitize content by redacting sensitive data.

    Replaces IP addresses, JWT tokens, API keys, and password fields.

    Args:
        content: Raw text content.

    Returns:
        Sanitized text with sensitive data replaced by placeholders.
    """
    if not content:
        return content

    sanitized = content

    # JWT tokens
    sanitized = _JWT_PATTERN.sub("[JWT-TOKEN-REDACTED]", sanitized)

    # API keys
    for pattern in _API_KEY_PATTERNS:
        sanitized = pattern.sub("[API-KEY-REDACTED]", sanitized)

    # Password fields
    sanitized = _PASSWORD_PATTERN.sub("[PASSWORD-REDACTED]", sanitized)

    # IP addresses
    sanitized = _IP_PATTERN.sub("[IP-REDACTED]", sanitized)

    return sanitized


def sanitize_path_results(path: str, content: str, is_sensitive: bool) -> str:
    """Conditionally sanitize content based on path sensitivity.

    Args:
        path: File path (for logging context).
        content: Raw file content.
        is_sensitive: Whether the path is classified as sensitive.

    Returns:
        Sanitized content if path is sensitive, otherwise original content.
    """
    if is_sensitive:
        logger.debug(f"Sanitizing content from sensitive path: {path}")
        return sanitize(content)
    return content
