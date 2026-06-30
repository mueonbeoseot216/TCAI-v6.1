"""
TCAI Gateway — AST rule engine (security core).
§1.1 exemption: static security rule tables — 60+ rules across 8 action types.


Rule coverage (8 action types):
  1. File ops (Read/Write/Delete) — 10 rules
  2. Registry ops (Write/Delete) — 18 rules
  3. Service ops — 2 rules
  4. Process ops — 2 rules
  5. Network ops — 2 rules
  6. Disk ops — 1 rule
  7. Diagnostic tools — 3 rules
  8. DLP sensitive reads — delegated to dlp.py

Extension guide:
  - Add rules: append (Action, pattern, Level, reason) tuples to the appropriate list
  - Add actions: add to Action enum and tool_action_map in gateway.py
  - Order matters: more specific patterns first; __ANY__ last
  - Safety principle: when unsure, use BLOCKED
"""
from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import NamedTuple

from . import paths as _paths
from . import logging_setup

logger = logging_setup.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════


class Level(Enum):
    """Security verdict for an operation.

    SAFE    — Execute directly, no approval needed.
    RISKY   — Require operator approval before execution.
    BLOCKED — Hard block, cannot be executed under any circumstances.
    """

    SAFE = "safe"
    RISKY = "risky"
    BLOCKED = "blocked"


class Action(Enum):
    """Tool action types for rule matching.

    Every write tool maps to one Action. Add new values here when adding tools.
    """

    FILE_READ = "FileRead"
    FILE_WRITE = "FileWrite"
    FILE_DELETE = "FileDelete"
    REGISTRY_WRITE = "RegistryWrite"
    REGISTRY_DELETE = "RegistryDelete"
    SERVICE_CONTROL = "ServiceControl"
    PROCESS_TERMINATE = "ProcessTerminate"
    FIREWALL_RULE = "FirewallRule"
    NETWORK_CONFIG = "NetworkConfig"
    DISK_OPERATION = "DiskOperation"
    DISK_CHECK = "DiskCheck"
    SYSTEM_FILE_SCAN = "SystemFileScan"
    DISM_HEALTH = "DismHealth"


# ═══════════════════════════════════════════════════════════════════════
# Rule type
# ═══════════════════════════════════════════════════════════════════════


class Rule(NamedTuple):
    """A single AST security rule."""

    action: Action
    pattern: str
    level: Level
    reason: str


# ═══════════════════════════════════════════════════════════════════════
# Critical system sets (do not modify without careful review)
# ═══════════════════════════════════════════════════════════════════════

CRITICAL_SERVICES: frozenset[str] = frozenset({
    # Core kernel
    "winlogon", "csrss", "smss", "lsass", "services",
    # Service hosts
    "svchost", "rpcss", "dcomlaunch",
    # Security
    "samss", "bfe", "mpssvc", "windefend", "securityhealthservice",
    # Network
    "dhcp", "dnscache", "netlogon", "winrm", "lmhosts",
    # Web / file sharing
    "w3svc", "lanmanserver", "lanmanworkstation",
    # System management
    "eventlog", "plugplay", "power", "schedule",
    "w32time", "winmgmt", "spooler",
    # Auth & session
    "seclogon", "senses", "appinfo", "cryptsvc",
    "termservice", "userManager",
    # Files & drivers
    "wudfsvc", "bam", "bits",
    # Update
    "wuauserv", "winupdate", "wsearch",
    # Notifications
    "wpnservice", "shellhwdetection",
    # Print
    "profsvc",
})

CRITICAL_PROCESSES: frozenset[str] = frozenset({
    "winlogon.exe", "logonui.exe",
    "system", "csrss.exe", "smss.exe",
    "lsass.exe", "services.exe",
    "wininit.exe",
    "svchost.exe",
    "dwm.exe", "sihost.exe", "taskhostw.exe", "explorer.exe",
    "fontdrvhost.exe",
    "spoolsv.exe",
    "searchindexer.exe",
    "registry",
    "memcompress.exe",
    "msmpeng.exe", "securityhealthservice.exe",
    "audiodg.exe",
    "trustedinstaller.exe",
    "applicationframehost.exe",
})

# ═══════════════════════════════════════════════════════════════════════
# DLP sensitive paths (single source of truth — also imported by dlp.py)
# ═══════════════════════════════════════════════════════════════════════

SENSITIVE_PATHS: list[str] = [
    r".*\.ssh\\.*",
    r".*\.aws\\.*",
    r".*id_rsa.*",
    r".*id_ed25519.*",
    r".*\.pem$",
    r".*\.key$",
    r".*\\Chrome\\User Data\\.*\\Login Data",
    r".*\\Edge\\User Data\\.*\\Login Data",
    r".*\\Firefox\\Profiles\\.*\\logins\.json",
    r"HKLM\\SAM.*",
    r"HKLM\\SECURITY.*",
    r"C:\\Windows\\System32\\config\\SAM.*",
    r".*\\Microsoft\\Credentials\\.*",
    r".*\\Microsoft\\Protect\\.*",
    r".*\\CredentialManager\\.*",
    r".*\\WebCache\\.*",
    r".*\\Wlansvc\\Profiles\\.*",
    r".*\.rdp$",
    r".*\\OpenVPN\\.*",
    r".*\\WireGuard\\.*",
    r".*ConsoleHost_history\.txt",
    r".*\.env$",
    r".*\\.minecraft\\.*",
    r".*网吧.*",
    r".*计费.*",
]


# ═══════════════════════════════════════════════════════════════════════
# Dynamic path helper
# ═══════════════════════════════════════════════════════════════════════

def _escape_root() -> str:
    """Return a regex-escaped version of the project root for rule matching."""
    return re.escape(str(_paths.PROJECT_ROOT))


_ROOT_REGEX: str = _escape_root()


# ═══════════════════════════════════════════════════════════════════════
# 1. File operation rules (10 rules)
# ═══════════════════════════════════════════════════════════════════════

_FILE_RULES: list[Rule] = [
    # FileRead
    Rule(Action.FILE_READ, _ROOT_REGEX + "\\\\.*", Level.SAFE, "TCAI own files"),
    Rule(Action.FILE_READ, "__ANY__", Level.SAFE, "General file read"),
    # FileWrite
    Rule(Action.FILE_WRITE, _ROOT_REGEX + "\\\\.*", Level.SAFE, "TCAI own directory"),
    Rule(Action.FILE_WRITE, r"C:\\.*", Level.BLOCKED, "C: drive write blocked"),
    Rule(Action.FILE_WRITE, r"\\\\" + r".*", Level.BLOCKED, "UNC network path write blocked"),
    Rule(Action.FILE_WRITE, "__ANY__", Level.SAFE, "Non-system drive write"),
    # FileDelete
    Rule(Action.FILE_DELETE, _ROOT_REGEX + "\\\\.*", Level.BLOCKED, "TCAI self-deletion blocked"),
    Rule(Action.FILE_DELETE, r"C:\\.*", Level.BLOCKED, "C: drive delete blocked"),
    Rule(Action.FILE_DELETE, r"\\\\" + r".*", Level.BLOCKED, "UNC network path delete blocked"),
    Rule(Action.FILE_DELETE, "__ANY__", Level.SAFE, "Non-system drive delete"),
]

# ═══════════════════════════════════════════════════════════════════════
# 2. Registry operation rules (18 rules)
# ═══════════════════════════════════════════════════════════════════════

_REGISTRY_RULES: list[Rule] = [
    # RegistryWrite — BLOCKED
    Rule(Action.REGISTRY_WRITE, r".*\\Windows NT\\CurrentVersion\\Winlogon.*", Level.BLOCKED, "Winlogon hijack prevention"),
    Rule(Action.REGISTRY_WRITE, r".*\\Control\\Lsa.*", Level.BLOCKED, "LSA security config"),
    Rule(Action.REGISTRY_WRITE, r".*\\CurrentControlSet\\Services\\.*", Level.BLOCKED, "Service registration via registry"),
    Rule(Action.REGISTRY_WRITE, r".*\\Session Manager\\.*", Level.BLOCKED, "Session manager hijack prevention"),
    Rule(Action.REGISTRY_WRITE, r"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run.*", Level.BLOCKED, "Global autorun"),
    Rule(Action.REGISTRY_WRITE, r"HKLM\\SOFTWARE\\Policies.*", Level.BLOCKED, "Group policy"),
    Rule(Action.REGISTRY_WRITE, r"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies.*", Level.BLOCKED, "System policy"),
    Rule(Action.REGISTRY_WRITE, r"HKLM\\SYSTEM\\.*", Level.BLOCKED, "Critical system config"),
    Rule(Action.REGISTRY_WRITE, r"HKLM\\SAM\\.*", Level.BLOCKED, "Security account manager"),
    Rule(Action.REGISTRY_WRITE, r"HKLM\\SECURITY\\.*", Level.BLOCKED, "Security policy"),
    # RegistryWrite — RISKY
    Rule(Action.REGISTRY_WRITE, r".*\\Windows\\CurrentVersion\\Run.*", Level.RISKY, "Autorun entry"),
    Rule(Action.REGISTRY_WRITE, r"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies.*", Level.RISKY, "User policy modification"),
    Rule(Action.REGISTRY_WRITE, r"HKLM\\SOFTWARE\\.*", Level.RISKY, "Global software config"),
    # RegistryWrite — SAFE
    Rule(Action.REGISTRY_WRITE, r"HKCU\\Software\\.*", Level.SAFE, "Current user software config"),
    # RegistryDelete — BLOCKED
    Rule(Action.REGISTRY_DELETE, r".*\\CurrentControlSet\\Services\\.*", Level.BLOCKED, "Service deletion via registry"),
    Rule(Action.REGISTRY_DELETE, r"HKLM\\.*", Level.BLOCKED, "Global registry deletion"),
    # RegistryDelete — RISKY
    Rule(Action.REGISTRY_DELETE, r"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies.*", Level.RISKY, "User policy deletion"),
    Rule(Action.REGISTRY_DELETE, r"HKCU\\Software\\.*", Level.RISKY, "User config deletion"),
]

# ═══════════════════════════════════════════════════════════════════════
# 3-7. Remaining rules
# ═══════════════════════════════════════════════════════════════════════

_SERVICE_RULES: list[Rule] = [
    Rule(Action.SERVICE_CONTROL, "__CRITICAL__", Level.BLOCKED, "Critical service operation blocked"),
    Rule(Action.SERVICE_CONTROL, "__ANY__", Level.SAFE, "Service operation"),
]

_PROCESS_RULES: list[Rule] = [
    Rule(Action.PROCESS_TERMINATE, "__CRITICAL__", Level.BLOCKED, "Critical process termination blocked"),
    Rule(Action.PROCESS_TERMINATE, "__ANY__", Level.SAFE, "Process termination"),
]

_NETWORK_RULES: list[Rule] = [
    Rule(Action.FIREWALL_RULE, "__ANY__", Level.RISKY, "Firewall rule requires approval"),
    Rule(Action.NETWORK_CONFIG, "__ANY__", Level.RISKY, "Network config requires approval"),
]

_DISK_RULES: list[Rule] = [
    Rule(Action.DISK_OPERATION, "__ANY__", Level.BLOCKED, "Disk partition/format is irreversible"),
]

_DIAG_RULES: list[Rule] = [
    Rule(Action.DISK_CHECK, "__ANY__", Level.SAFE, "Read-only disk check"),
    Rule(Action.SYSTEM_FILE_SCAN, "__ANY__", Level.SAFE, "Read-only system file scan"),
    Rule(Action.DISM_HEALTH, "__ANY__", Level.SAFE, "Read-only DISM health check"),
]

# ═══════════════════════════════════════════════════════════════════════
# All rules (order: file → registry → service → process → network → disk → diag)
# ═══════════════════════════════════════════════════════════════════════

ALL_RULES: list[Rule] = (
    _FILE_RULES
    + _REGISTRY_RULES
    + _SERVICE_RULES
    + _PROCESS_RULES
    + _NETWORK_RULES
    + _DISK_RULES
    + _DIAG_RULES
)


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


def _match_any_pattern(target: str, patterns: list[str]) -> bool:
    """Check if target matches any regex pattern (case-insensitive).

    Args:
        target: Normalized path string (backslash-separated).
        patterns: List of regex pattern strings.

    Returns:
        True if target matches at least one pattern.
    """
    normalized = target.replace("/", "\\").lower()
    for pattern in patterns:
        if re.match(pattern.lower(), normalized):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════
# Main matching function
# ═══════════════════════════════════════════════════════════════════════


def match(
    action: str,
    target: str = "",
    sub_action: str = "",
    target_name: str = "",
) -> tuple[Level, str]:
    """AST rule matching engine — the security gateway's decision core.

    Flow:
      1. Parse action string to Action enum (unknown → BLOCKED)
      2. Special pre-checks: service/process/disk
      3. Iterate ALL_RULES in order; first match wins
      4. Fail-Secure: no match → BLOCKED

    Args:
        action: Action type string (e.g. "FileWrite", "RegistryWrite").
        target: Operation target path (file/registry key/service name).
        sub_action: Sub-action for service_control ("start"/"stop"/"delete").
        target_name: Target name for critical process/service lists.

    Returns:
        (Level, reason_string)
    """
    # Parse action
    try:
        action_enum = Action(action)
    except ValueError:
        return Level.BLOCKED, f"Unknown action type: {action}"

    # Special: service operations
    if action_enum == Action.SERVICE_CONTROL:
        if sub_action in ("delete", "config"):
            return Level.BLOCKED, "Service delete/config is irreversible"
        if target_name.lower() in CRITICAL_SERVICES:
            return Level.BLOCKED, (
                f"Critical service {target_name} blocked from {sub_action} "
                f"— would crash the system"
            )

    # Special: process operations
    if action_enum == Action.PROCESS_TERMINATE:
        if target_name.lower() in CRITICAL_PROCESSES:
            return Level.BLOCKED, (
                f"Critical process {target_name} cannot be terminated "
                f"— would crash the system"
            )

    # Special: disk operations
    if action_enum == Action.DISK_OPERATION:
        return Level.BLOCKED, "Disk partition/format is irreversible"

    # Traverse rule table
    normalized_target = target.replace("/", "\\")

    for rule in ALL_RULES:
        if rule.action != action_enum:
            continue

        if rule.pattern == "__ANY__":
            return rule.level, rule.reason

        if rule.pattern == "__CRITICAL__":
            continue  # Handled by pre-checks above

        if _match_any_pattern(normalized_target, [rule.pattern]):
            return rule.level, rule.reason

    # Fail-Secure: unknown operations default to BLOCKED
    return Level.BLOCKED, f"No matching security rule: {action} → {target}"


# ═══════════════════════════════════════════════════════════════════════
# Query helpers
# ═══════════════════════════════════════════════════════════════════════


def get_rules_by_action(action: str) -> list[tuple[str, Level, str]]:
    """Get all rules for a specific action type (for debugging/auditing).

    Args:
        action: Action enum value string, e.g. "FileWrite".

    Returns:
        List of (pattern, level, reason) tuples.
    """
    try:
        action_enum = Action(action)
    except ValueError:
        return []
    return [
        (rule.pattern, rule.level, rule.reason)
        for rule in ALL_RULES
        if rule.action == action_enum
    ]


def is_critical_process(name: str) -> bool:
    """Check if a process name is in the critical protection list."""
    return name.lower() in CRITICAL_PROCESSES


def is_critical_service(name: str) -> bool:
    """Check if a service name is in the critical protection list."""
    return name.lower() in CRITICAL_SERVICES
