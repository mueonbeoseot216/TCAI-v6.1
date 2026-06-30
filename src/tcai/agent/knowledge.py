"""
TCAI Agent — SQLite FTS5 knowledge base.

Parses Markdown + YAML frontmatter files and builds a full-text search index.
The index is rebuilt from scratch on every startup (ephemeral, in-memory).
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import yaml

from ..gateway.paths import PROJECT_ROOT
from ..gateway.config import config


class KnowledgeBase:
    """FTS5 full-text search knowledge base."""

    def __init__(self, knowledge_path: Path | None = None) -> None:
        self._knowledge_path = knowledge_path or config.knowledge_path
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._create_index()

    def _create_index(self) -> None:
        """Create FTS5 table and populate from Markdown files."""
        self._conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS kb "
            "USING fts5(title, game, category, content, "
            "tokenize='unicode61 remove_diacritics 1')"
        )

        if not self._knowledge_path.exists():
            return

        for md_file in self._knowledge_path.rglob("*.md"):
            try:
                title, game, category, content = self._parse_md(md_file)
                if content:
                    self._conn.execute(
                        "INSERT INTO kb (title, game, category, content) "
                        "VALUES (?, ?, ?, ?)",
                        (title, game, category, content),
                    )
            except (UnicodeDecodeError, OSError, sqlite3.Error):
                continue  # Skip malformed or unreadable files

        self._conn.commit()

    @staticmethod
    def _parse_md(filepath: Path) -> tuple[str, str, str, str]:
        """Parse a Markdown file with YAML frontmatter.

        Returns:
            (title, game, category, content)
        """
        text = filepath.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        frontmatter: dict = {}
        content = text

        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if fm_match:
            try:
                frontmatter = yaml.safe_load(fm_match.group(1)) or {}
            except yaml.YAMLError:
                import logging
                logging.getLogger(__name__).warning(f"YAML parse failed in {filepath}", exc_info=True)
            content = text[fm_match.end():]

        title = str(frontmatter.get("title", filepath.stem))
        game = str(frontmatter.get("game", ""))
        category = str(frontmatter.get("category", ""))

        return title, game, category, content.strip()

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search the knowledge base using FTS5.

        Args:
            query: Search query string.
            limit: Maximum results.

        Returns:
            List of result dicts with title, game, content, etc.
        """
        if not query.strip():
            return []

        try:
            cursor = self._conn.execute(
                "SELECT title, game, category, "
                "snippet(kb, 0, '<mark>', '</mark>', '...', 40) AS snippet "
                "FROM kb WHERE kb MATCH ? "
                "ORDER BY rank LIMIT ?",
                (query, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            import logging
            logging.getLogger(__name__).warning(f"FTS5 query failed: {query[:100]}", exc_info=True)
            return []
