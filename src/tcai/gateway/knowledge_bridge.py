"""
TCAI Gateway — knowledge base bridge.

Bridges the Gateway layer to the knowledge base (FTS5 search).
This module resolves the cross-layer dependency — the Gateway does not
import from Agent; instead, Agent initializes the knowledge base and
this bridge module provides the search interface.
"""
from __future__ import annotations

from typing import Any

from . import logging_setup

logger = logging_setup.get_logger(__name__)

# Knowledge base instance (set by Agent at startup)
_kb_instance: Any = None


def init_knowledge(kb: Any) -> None:
    """Register the knowledge base instance.

    Called by Agent at startup after initializing KnowledgeBase.

    Args:
        kb: KnowledgeBase instance with a search(query, limit) method.
    """
    global _kb_instance
    _kb_instance = kb
    logger.info("Knowledge base bridge initialized")


def search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search the FTS5 knowledge base.

    Args:
        query: Search query string.
        limit: Maximum results to return.

    Returns:
        List of result dicts with title, game, content, etc.
        Empty list if knowledge base is not initialized.
    """
    if _kb_instance is None:
        logger.warning("Knowledge base not initialized — returning empty results")
        return []

    try:
        return _kb_instance.search(query, limit=limit)
    except (AttributeError, TypeError) as e:
        logger.error(f"Knowledge search failed: {e}")
        return []
