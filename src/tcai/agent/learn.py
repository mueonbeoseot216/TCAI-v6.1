"""
TCAI Agent — /learn knowledge extraction subsystem.

Extracts structured diagnostic knowledge from session logs
and writes new Markdown entries to the knowledge base.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from ..gateway.config import config
from ..gateway.http_client import http_client
from ..gateway.paths import PROJECT_ROOT
from ..gateway import injection_filter


class LearnExtractor:
    """Extracts structured knowledge from session logs via LLM."""

    # Branch map: leaf directory keywords → knowledge category
    BRANCH_MAP: dict[str, str] = {
        "game": "game_issues",
        "游戏": "game_issues",
        "system": "system_issues",
        "系统": "system_issues",
        "network": "network_issues",
        "网络": "network_issues",
        "peripheral": "peripheral_issues",
        "外设": "peripheral_issues",
        "software": "software_platforms",
        "软件": "software_platforms",
        "platform": "software_platforms",
        "error": "reference_knowledge",
        "错误": "reference_knowledge",
    }

    def __init__(self) -> None:
        self.api_key: str = config.deepseek_api_key
        self.api_base: str = config.deepseek_api_base
        self.model: str = config.model

    def handle_learn(self, filepath: str) -> str:
        """Process a /learn command.

        Args:
            filepath: Path to a session log file.

        Returns:
            Result message string.
        """
        path = Path(filepath)
        if not path.exists():
            return f"File not found: {filepath}"

        # Read session log
        log_text = path.read_text(encoding="utf-8")

        # Extract knowledge via LLM
        result = self._extract_knowledge(log_text)
        if result is None:
            return "Knowledge extraction failed. Check API key and network."

        # Security: filter extracted content before writing to knowledge base
        filter_result = injection_filter.filter_long_text(result, source="learn_extraction")
        if filter_result["blocked"]:
            return (
                f"Knowledge extraction blocked by injection filter. "
                f"Flags: {filter_result['flags']}"
            )
        result = filter_result["filtered_text"]

        # Determine best output path
        best_leaf = self._find_best_leaf(result)
        output_path = self._resolve_output_path(best_leaf, path.stem)

        # Write result
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")

        return f"Knowledge extracted → {output_path}"

    def _extract_knowledge(self, log_text: str) -> str | None:
        """Call LLM to extract structured knowledge from log text."""
        prompt = (
            "Extract structured diagnostic knowledge from the following session log. "
            "Return Markdown with YAML frontmatter:\n\n"
            "---\n"
            "title: <diagnostic title>\n"
            "game: <game name or 'system'>\n"
            "category: <category>\n"
            "tags: [tag1, tag2]\n"
            "---\n\n"
            "# <title>\n\n"
            "## Symptom\n...\n\n"
            "## Root Cause\n...\n\n"
            "## Solution\n...\n\n"
            "## Verification\n...\n\n"
            f"Session log:\n{log_text[:8000]}"
        )

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.llm_learn_temperature,
            "max_tokens": config.llm_learn_max_tokens,
        }

        try:
            response = http_client.post_json(
                f"{self.api_base}/chat/completions",
                data=payload,
                timeout=config.llm_learn_timeout,
                auth_bearer=self.api_key,
            )
            data = response.json
            if data and "choices" in data:
                return data["choices"][0]["message"]["content"]
        except (OSError, ValueError, KeyError, TypeError):
            import logging
            logging.getLogger(__name__).warning("LLM learn extraction failed", exc_info=True)

        return None

    def _find_best_leaf(self, content: str) -> str:
        """Find the best knowledge category leaf directory."""
        # Try to extract game name from frontmatter
        gm_match = re.search(r"game:\s*(.+)", content)
        if gm_match:
            game_name = gm_match.group(1).strip()
            leaf_dirs = self._discover_leaf_dirs()
            for leaf in leaf_dirs:
                if game_name.lower() in leaf.lower():
                    return leaf

        # Fall back to branch mapping
        content_lower = content.lower()
        for keyword, branch in self.BRANCH_MAP.items():
            if keyword.lower() in content_lower:
                return branch

        return "reference_knowledge"

    def _resolve_output_path(self, best_leaf: str, stem: str) -> Path:
        """Resolve the output path for a new knowledge entry."""
        base = config.knowledge_path / best_leaf
        return base / f"{stem}.md"

    @staticmethod
    def _discover_leaf_dirs() -> list[str]:
        """Discover leaf directories in the knowledge base."""
        kb_path = config.knowledge_path
        if not kb_path.exists():
            return []
        leaves: list[str] = []
        for root, dirs, _ in os.walk(kb_path):
            if not dirs:  # Leaf directory
                leaves.append(str(Path(root).relative_to(kb_path)))
        return leaves

