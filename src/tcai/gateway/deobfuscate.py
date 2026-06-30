"""
TCAI Gateway — deobfuscation pipeline (security core).

4-stage pipeline executed in fixed order:
  1. Base64-encoded command rejection
  2. PowerShell alias resolution
  3. Static variable evaluation
  4. String encoding detection

Any stage can block the operation; blocked results stop the pipeline immediately.
"""
from __future__ import annotations

import os
import re
from typing import Any

from . import logging_setup
from .exceptions import SecurityBlockedError

logger = logging_setup.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Stage 1: Base64-encoded command rejection
# ═══════════════════════════════════════════════════════════════════════

BASE64_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"-EncodedCommand\s+\S+", re.IGNORECASE),
    re.compile(r"-enc\s+\S+", re.IGNORECASE),
    re.compile(r"-e\s+[A-Za-z0-9+/=]{20,}", re.IGNORECASE),
    re.compile(r"-Enc\s+\S+", re.IGNORECASE),
]


def reject_base64(params: dict[str, Any]) -> str:
    """Check params for Base64-encoded PowerShell commands.

    Args:
        params: Tool parameter dictionary.

    Returns:
        Empty string if OK.

    Raises:
        SecurityBlockedError: If Base64 encoding is detected.
    """
    all_text = " ".join(str(v) for v in params.values())
    for pattern in BASE64_PATTERNS:
        match = pattern.search(all_text)
        if match:
            raise SecurityBlockedError(
                f"Base64-encoded command detected: '{match.group()[:80]}'. "
                f"Cannot perform AST analysis on encoded commands.",
                rule="deobfuscate_base64",
            )
    return ""


# ═══════════════════════════════════════════════════════════════════════
# Stage 2: PowerShell alias resolution
# ═══════════════════════════════════════════════════════════════════════

ALIAS_MAP: dict[str, str] = {
    "rm": "Remove-Item",
    "del": "Remove-Item",
    "ri": "Remove-Item",
    "rd": "Remove-Item",
    "rmdir": "Remove-Item",
    "md": "mkdir",
    "ni": "New-Item",
    "%": "ForEach-Object",
    "?": "Where-Object",
    "ft": "Format-Table",
    "fl": "Format-List",
    "gwmi": "Get-WmiObject",
    "iwr": "Invoke-WebRequest",
    "iex": "Invoke-Expression",
    "icm": "Invoke-Command",
    "gl": "Get-Location",
    "sl": "Set-Location",
    "gc": "Get-Content",
    "sc": "Set-Content",
    "ac": "Add-Content",
    "cat": "Get-Content",
    "cd": "Set-Location",
    "cp": "Copy-Item",
    "mv": "Move-Item",
    "ls": "Get-ChildItem",
    "dir": "Get-ChildItem",
    "gci": "Get-ChildItem",
    "echo": "Write-Output",
    "type": "Get-Content",
    "cls": "Clear-Host",
    "sleep": "Start-Sleep",
    "gps": "Get-Process",
    "spps": "Stop-Process",
    "kill": "Stop-Process",
    "gsv": "Get-Service",
    "sasv": "Start-Service",
    "spsv": "Stop-Service",
    "ipconfig": "Get-NetIPConfiguration",
    "ping": "Test-Connection",
    "nslookup": "Resolve-DnsName",
    "tracert": "Test-NetConnection -TraceRoute",
}

# Sort by length descending: match longer aliases first to avoid partial conflicts
_SORTED_ALIASES: list[tuple[str, str]] = sorted(
    ALIAS_MAP.items(), key=lambda x: len(x[0]), reverse=True
)


def resolve_aliases(text: str) -> str:
    """Expand PowerShell aliases to their full cmdlet names.

    Only matches whole-word boundaries to avoid false positives
    (e.g., "rm" in "Remove-Item" should not match).

    Args:
        text: Raw command text potentially containing aliases.

    Returns:
        Text with aliases expanded.
    """
    if not text:
        return text

    # Split on whitespace and shell metacharacters, preserving delimiters
    parts = re.split(r"(\s+|[,;|&(){}[\]])", text)
    result: list[str] = []

    for part in parts:
        lower = part.strip().lower()
        if lower in ALIAS_MAP:
            result.append(ALIAS_MAP[lower])
        else:
            result.append(part)

    return "".join(result)


# ═══════════════════════════════════════════════════════════════════════
# Stage 3: Static variable evaluation
# ═══════════════════════════════════════════════════════════════════════

# Known environment variables that can be safely expanded in a static context
KNOWN_STATIC_VARS: dict[str, str] = {
    "%TEMP%": os.environ.get("TEMP", "C:\\Windows\\Temp"),
    "%USERPROFILE%": os.environ.get("USERPROFILE", ""),
    "%WINDIR%": os.environ.get("WINDIR", "C:\\Windows"),
    "%SYSTEMROOT%": os.environ.get("SYSTEMROOT", "C:\\Windows"),
    "%PROGRAMFILES%": os.environ.get("PROGRAMFILES", "C:\\Program Files"),
    "%PROGRAMFILES(X86)%": os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
    "%APPDATA%": os.environ.get("APPDATA", ""),
    "%LOCALAPPDATA%": os.environ.get("LOCALAPPDATA", ""),
    "%HOMEDRIVE%": os.environ.get("HOMEDRIVE", "C:"),
    "%HOMEPATH%": os.environ.get("HOMEPATH", ""),
    "%PUBLIC%": os.environ.get("PUBLIC", "C:\\Users\\Public"),
    "%ALLUSERSPROFILE%": os.environ.get("ALLUSERSPROFILE", "C:\\ProgramData"),
    "$env:TEMP": os.environ.get("TEMP", "C:\\Windows\\Temp"),
    "$env:USERPROFILE": os.environ.get("USERPROFILE", ""),
    "$env:WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
    "$env:SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
}

# Sort by length descending: longer variables expanded first
_SORTED_STATIC_VARS: list[tuple[str, str]] = sorted(
    KNOWN_STATIC_VARS.items(), key=lambda x: len(x[0]), reverse=True
)

# Patterns that indicate unresolved runtime variables (dangerous)
_RUNTIME_VAR_PATTERNS: list[str] = [
    r"\$env:[A-Z_]+",          # Unresolved $env:VAR
    r"\$\(.*?\)",              # $() subexpression
    r"\$\w+",                  # Bare $varName
    r"%[A-Z_]+%(?!\\)",        # Unresolved %VAR%
    r"\[System\.",             # .NET class invocation
    r"::\w+",                  # Static method call
    r"-join",                  # Join operator
    r"-split",                 # Split operator
    r"-replace",               # Replace operator
    r"-f\s",                   # Format operator
]

# Compiled runtime patterns (built at import)
_RUNTIME_RE: list[re.Pattern[str]] = [
    re.compile(pat, re.IGNORECASE) for pat in _RUNTIME_VAR_PATTERNS
]

# Simple string concatenation: "a" + "b"
_CONCAT_RE: re.Pattern[str] = re.compile(
    r"""["']([^"']*)["']\s*\+\s*["']([^"']*)["']"""
)


def static_eval(value: str) -> str:
    """Statically evaluate a string value for the deobfuscation pipeline.

    Steps:
      1. Expand known static environment variables
      2. Detect unresolved runtime variables → blocked
      3. Evaluate simple string concatenation

    Args:
        value: String value to evaluate.

    Returns:
        Evaluated string.

    Raises:
        SecurityBlockedError: If unresolved runtime variables are detected.
    """
    if not value:
        return value

    original = value

    # Expand known static variables
    for var, replacement in _SORTED_STATIC_VARS:
        value = value.replace(var, replacement)

    # Detect unresolved runtime variables
    for pattern in _RUNTIME_RE:
        match = pattern.search(value)
        if match:
            raise SecurityBlockedError(
                f"Runtime variable/expression detected in parameter: "
                f"'{original[:100]}' contains '{match.group()[:80]}'. "
                f"Cannot statically evaluate — blocked on Fail-Secure principle.",
                rule="deobfuscate_runtime_var",
            )

    # Simple string concatenation
    concat_match = _CONCAT_RE.search(value)
    if concat_match:
        value = _CONCAT_RE.sub(
            lambda m: f'"{m.group(1)}{m.group(2)}"', value
        )

    return value


# ═══════════════════════════════════════════════════════════════════════
# Stage 4: String encoding detection
# ═══════════════════════════════════════════════════════════════════════

ENCODING_PATTERNS: list[re.Pattern[str]] = [
    # PowerShell encoding
    re.compile(r"\[char\]\s*0x[0-9A-Fa-f]+", re.IGNORECASE),
    re.compile(r"\[System\.Text\.Encoding\]::\w+\.GetString\(", re.IGNORECASE),
    re.compile(r"ConvertFrom-Base64", re.IGNORECASE),
    re.compile(r"-bxor", re.IGNORECASE),
    re.compile(r"-(band|bor)\s", re.IGNORECASE),
    re.compile(r"\[Convert\]::FromBase64String", re.IGNORECASE),
    re.compile(r"\[System\.Convert\]::", re.IGNORECASE),
    re.compile(r"FromBase64Char(Array|String)", re.IGNORECASE),
    re.compile(r"`[0nrta'\"]"),
    re.compile(r"\\u[0-9A-Fa-f]{4}"),
    # Python execution/obfuscation
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\bexec\s*\(", re.IGNORECASE),
    re.compile(r"\b__import__\s*\(", re.IGNORECASE),
    re.compile(r"\bgetattr\s*\([^,]+,\s*['\"]__", re.IGNORECASE),
    re.compile(r"\bcompile\s*\(", re.IGNORECASE),
    re.compile(r"base64\.b64decode", re.IGNORECASE),
    re.compile(r"codecs\.decode", re.IGNORECASE),
    re.compile(r"(__builtins__|__builtin__)", re.IGNORECASE),
    re.compile(r"\\x[0-9A-Fa-f]{2}"),
    re.compile(r"\\[0-7]{3}"),
    # CMD obfuscation
    re.compile(r"%COMSPEC%", re.IGNORECASE),
    re.compile(r"cmd\s*/[cCkK]\s+", re.IGNORECASE),
    re.compile(r"\^[&|><]"),
    # Generic encoding / high entropy
    re.compile(r"(rot13|atob|btoa)\b", re.IGNORECASE),
    re.compile(r"data:text/\w+;base64", re.IGNORECASE),
    re.compile(r"%[0-9A-Fa-f]{2}"),
    re.compile(r"(chr|ord|hex)\s*\(", re.IGNORECASE),
]


def detect_encoding(value: str) -> str:
    """Check a string for encoding/obfuscation patterns.

    Args:
        value: String to check.

    Returns:
        Empty string if no encoding detected.

    Raises:
        SecurityBlockedError: If encoding/obfuscation is detected.
    """
    for pattern in ENCODING_PATTERNS:
        match = pattern.search(value)
        if match:
            raise SecurityBlockedError(
                f"String encoding/obfuscation detected: '{match.group()[:80]}'. "
                f"Cannot perform AST analysis on obfuscated content.",
                rule="deobfuscate_encoding",
            )
    return ""


# ═══════════════════════════════════════════════════════════════════════
# Unified entry point
# ═══════════════════════════════════════════════════════════════════════


def normalize(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Deobfuscation pipeline main entry point.

    Executes the 4-stage pipeline in order. Any stage that detects
    obfuscation will raise SecurityBlockedError.

    Args:
        tool_name: Name of the tool being called.
        params: Tool parameter dictionary.

    Returns:
        Normalized (deobfuscated) parameter dictionary.

    Raises:
        SecurityBlockedError: If any stage blocks the operation.
    """
    # Stage 1: Base64 rejection
    reject_base64(params)
    logger.debug("Stage 1 passed: no Base64 encoding detected")

    # Stage 2: Alias resolution
    normalized_params: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str):
            normalized_params[key] = resolve_aliases(value)
        else:
            normalized_params[key] = value
    logger.debug("Stage 2 passed: aliases resolved")

    # Stage 3: Static evaluation
    for key, value in normalized_params.items():
        if isinstance(value, str):
            normalized_params[key] = static_eval(value)
    logger.debug("Stage 3 passed: static evaluation complete")

    # Stage 4: Encoding detection
    for key, value in normalized_params.items():
        if isinstance(value, str):
            detect_encoding(value)
    logger.debug("Stage 4 passed: no encoding detected")

    return normalized_params
