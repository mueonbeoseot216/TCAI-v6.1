"""
TCAI Gateway — tool registry.

Collects get_schema() from all tool modules and builds the combined
schema list for MCP tools/list responses.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

from . import logging_setup

logger = logging_setup.get_logger(__name__)

# Tool module paths relative to tcai.gateway.tools
_READONLY_MODULES: list[str] = [
    "tcai.gateway.tools.readonly.process_list",
    "tcai.gateway.tools.readonly.service_status",
    "tcai.gateway.tools.readonly.system_info",
    "tcai.gateway.tools.readonly.disk_space",
    "tcai.gateway.tools.readonly.reg_query",
    "tcai.gateway.tools.readonly.web_search",
    "tcai.gateway.tools.readonly.file_read",
    "tcai.gateway.tools.readonly.file_search",
    "tcai.gateway.tools.readonly.event_log",
    "tcai.gateway.tools.readonly.driver_list",
    "tcai.gateway.tools.readonly.bluescreen",
    "tcai.gateway.tools.readonly.anti_cheat_check",
    "tcai.gateway.tools.readonly.gpu_status",
    "tcai.gateway.tools.readonly.disk_io",
    "tcai.gateway.tools.readonly.network_diag",
    "tcai.gateway.tools.readonly.net_adapter_status",
    "tcai.gateway.tools.readonly.perf_counter",
    "tcai.gateway.tools.readonly.runtime_check",
    "tcai.gateway.tools.readonly.service_deps",
    "tcai.gateway.tools.readonly.wmi_query",
    "tcai.gateway.tools.readonly.error_code_lookup",
]

_WRITE_MODULES: list[str] = [
    "tcai.gateway.tools.write.file_write",
    "tcai.gateway.tools.write.file_delete",
    "tcai.gateway.tools.write.process_kill",
    "tcai.gateway.tools.write.reg_write",
    "tcai.gateway.tools.write.reg_delete_value",
    "tcai.gateway.tools.write.service_control",
    "tcai.gateway.tools.write.firewall_rule",
    "tcai.gateway.tools.write.disk_check",
    "tcai.gateway.tools.write.dism_health",
    "tcai.gateway.tools.write.system_file_scan",
]

# Tool name → handler function cache
_readonly_handlers: dict[str, Any] = {}
_write_handlers: dict[str, Any] = {}


def _load_tools() -> None:
    """Lazy-load all tool modules and populate handler dicts."""
    if _readonly_handlers and _write_handlers:
        return  # Already loaded

    for module_path in _READONLY_MODULES:
        try:
            mod = import_module(module_path)
            schema = mod.get_schema()
            _readonly_handlers[schema["name"]] = mod.execute
        except Exception as e:
            logger.error(f"Failed to load tool module {module_path}: {e}")

    for module_path in _WRITE_MODULES:
        try:
            mod = import_module(module_path)
            schema = mod.get_schema()
            _write_handlers[schema["name"]] = mod.execute
        except Exception as e:
            logger.error(f"Failed to load tool module {module_path}: {e}")


def get_tool_schemas() -> list[dict[str, Any]]:
    """Get the combined MCP tool schema list.

    Each tool module exports get_schema() → ToolSchema.
    This function collects them all into a single list.

    Returns:
        List of tool schema dicts for MCP tools/list response.
    """
    _load_tools()

    schemas: list[dict[str, Any]] = []

    for module_path in _READONLY_MODULES + _WRITE_MODULES:
        try:
            mod = import_module(module_path)
            schemas.append(mod.get_schema())
        except Exception as e:
            logger.error(f"Failed to load schema from {module_path}: {e}")

    return schemas


def get_readonly_handler(tool_name: str) -> Any | None:
    """Get the execute function for a read-only tool by name."""
    _load_tools()
    return _readonly_handlers.get(tool_name)


def get_write_handler(tool_name: str) -> Any | None:
    """Get the execute function for a write tool by name."""
    _load_tools()
    return _write_handlers.get(tool_name)


def get_handler(tool_name: str) -> Any | None:
    """Get the execute function for any tool by name."""
    return get_readonly_handler(tool_name) or get_write_handler(tool_name)


def is_readonly(tool_name: str) -> bool:
    """Check if a tool is read-only."""
    _load_tools()
    return tool_name in _readonly_handlers


def is_write(tool_name: str) -> bool:
    """Check if a tool is a write tool (requires security pipeline)."""
    _load_tools()
    return tool_name in _write_handlers

