"""
TCAI Agent — 5-layer chained prompt engine.

Loads L1-L5 prompt files from src/tcai/prompts/.
Stable layers (L1+L2) injected once at session start.
Dynamic layers (L3+L4+L5) injected based on conversation stage.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..gateway.paths import PROMPTS_DIR


class PromptEngine:
    """5-layer chained prompt engine."""

    LAYERS: list[str] = [
        "L1_constitution.txt",
        "L2_persona.txt",
        "L3_protocol.txt",
        "L4_matrix_header.txt",
        "L5_output_format.txt",
    ]

    STABLE_BOUNDARY: int = 2  # L1=0, L2=1 are stable

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._prompts_dir = prompts_dir or PROMPTS_DIR
        self._cache: dict[str, str] = {}
        self._injected: set[str] = set()
        self._conversation_started: bool = False

        # Preload all layers
        for filename in self.LAYERS:
            self._load_layer(filename)

    def _load_layer(self, filename: str) -> str:
        """Load a single prompt layer from disk."""
        if filename in self._cache:
            return self._cache[filename]

        filepath = self._prompts_dir / filename
        if not filepath.exists():
            self._cache[filename] = f"[{filename} not found]"
            return self._cache[filename]

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self._cache[filename] = f.read().strip()
        except OSError:
            self._cache[filename] = f"[{filename} read error]"

        return self._cache[filename]

    def get_current(self, session: object, messages: list[dict]) -> str:
        """Return the full system prompt for the current conversation stage.

        Args:
            session: Session object with machine_id and session_id attributes.
            messages: Current conversation messages list.

        Returns:
            Complete system prompt string.
        """
        if not self._conversation_started:
            self._conversation_started = True
            return self._build_stable(session)

        return self._build_dynamic(session, messages)

    def _build_stable(self, session: object) -> str:
        """Build stable prompt: L1 + L2."""
        l1 = self._load_layer(self.LAYERS[0])
        l2 = self._load_layer(self.LAYERS[1])
        self._injected.update({"L1", "L2"})

        mid = getattr(session, "machine_id", "") or "unspecified"
        sid = getattr(session, "session_id", "unknown")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return "\n".join([
            "=" * 50,
            "[System Rules — Stable Layer]",
            "These rules are active for the entire session.",
            "=" * 50,
            "",
            l1,
            "",
            "---",
            "",
            l2,
            "",
            "---",
            "",
            f"Machine: {mid} | Session: {sid} | Time: {now}",
        ])

    def _build_dynamic(self, session: object, messages: list[dict]) -> str:
        """Build dynamic prompt: L3+L4+L5 based on stage."""
        l1 = self._load_layer(self.LAYERS[0])
        l2 = self._load_layer(self.LAYERS[1])
        l3 = self._load_layer(self.LAYERS[2])
        l4 = self._load_layer(self.LAYERS[3])
        l5 = self._load_layer(self.LAYERS[4])

        stage = self._detect_stage(messages)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        parts = [
            "=" * 50,
            "[System Rules — Stable Layer]",
            "",
            l1,
            "",
            "---",
            "",
            l2,
            "",
            "=" * 50,
            "",
            f"Time: {now}",
        ]

        if stage in ("diagnosing", "answering"):
            if "L3" not in self._injected:
                self._injected.add("L3")
            parts.extend(["[Diagnostic Protocol]", l3, ""])

        if stage in ("diagnosing", "answering"):
            parts.extend(["[Knowledge Matrix]", l4, ""])

        if stage == "answering":
            parts.extend(["[Output Format]", l5])

        return "\n".join(parts)

    @staticmethod
    def _detect_stage(messages: list[dict]) -> str:
        """Detect conversation stage: idle, diagnosing, or answering."""
        user_messages = [m for m in messages if m.get("role") == "user"]
        tool_messages = [m for m in messages if m.get("role") == "tool"]

        if not user_messages:
            return "idle"
        if not tool_messages:
            return "diagnosing"
        if len(tool_messages) >= 2:
            return "answering"
        return "diagnosing"

    def reset(self) -> None:
        """Reset injection state for a new session."""
        self._injected.clear()
        self._conversation_started = False
