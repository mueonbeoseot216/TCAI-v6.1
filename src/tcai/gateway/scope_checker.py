"""
TCAI Gateway — scope checker.

Validates that file paths are within allowed scopes.
Blocks writes to C: drive and UNC paths; allows writes to non-system drives.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import logging_setup

logger = logging_setup.get_logger(__name__)

# C: drive block patterns — any write to these paths is blocked
C_DRIVE_BLOCK_PATTERNS: list[str] = [
    r"C:\\Windows\\.*",
    r"C:\\Program Files\\.*",
    r"C:\\Program Files \(x86\)\\.*",
    r"C:\\ProgramData\\.*",
    r"C:\\Users\\.*\\AppData\\.*",
    r"C:\\System Volume Information\\.*",
]

# C: drive allowed paths — exceptions to the block (project root only)
C_DRIVE_ALLOWED: list[str] = []  # Populated dynamically from project root


def _get_allowed_patterns() -> list[str]:
    """Build allowlist patterns from project root."""
    if C_DRIVE_ALLOWED:
        return C_DRIVE_ALLOWED

    from .paths import PROJECT_ROOT

    root_str = str(PROJECT_ROOT.resolve())
    C_DRIVE_ALLOWED.append(re.escape(root_str) + "\\\\.*")
    return C_DRIVE_ALLOWED


def check_scope(path: str) -> tuple[bool, str]:
    """Check if a file path is within allowed write scope.

    Rules:
      - UNC paths (\\...) → BLOCKED
      - C: drive paths → BLOCKED (except project root)
      - Other drives → ALLOWED
      - Project root → ALLOWED

    Args:
        path: Absolute or relative file path.

    Returns:
        (allowed_bool, reason_string)
    """
    normalized = path.replace("/", "\\")

    # UNC paths
    if normalized.startswith("\\\\"):
        return False, "UNC network paths are blocked"

    # Project root — always allowed
    allowed_patterns = _get_allowed_patterns()
    for pattern in allowed_patterns:
        if re.match(pattern, normalized, re.IGNORECASE):
            return True, "Path is within project root"

    # C: drive block
    if normalized.upper().startswith("C:\\"):
        for pattern in C_DRIVE_BLOCK_PATTERNS:
            if re.match(pattern, normalized, re.IGNORECASE):
                return False, f"System path blocked: {path}"
        # If it's on C: but not matching any block pattern, still block
        return False, f"C: drive writes are blocked (path: {path})"

    # Other drives — allowed
    return True, "Non-system drive"


def normalize_path(path: str) -> str:
    """Normalize a path for consistency.

    - Resolves relative paths against project root
    - Converts forward slashes to backslashes
    - Returns absolute path string
    """
    p = Path(path)
    if not p.is_absolute():
        from .paths import PROJECT_ROOT
        p = PROJECT_ROOT / p
    return str(p.resolve()).replace("/", "\\")
