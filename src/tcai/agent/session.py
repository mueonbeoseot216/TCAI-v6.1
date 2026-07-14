"""
TCAI Agent — session management.

Tracks machine ID, session ID, and writes conversation logs to disk.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from ..gateway.paths import RECORDS_DIR, SESSION_DIR


class Session:
    """TCAI diagnostic session — tracks state and writes logs."""

    def __init__(self) -> None:
        RECORDS_DIR.mkdir(parents=True, exist_ok=True)
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

        self.session_id: str = datetime.now().strftime("%m%d-%H%M%S")
        self.machine_id: str = ""
        self.start_time: datetime = datetime.now()
        self.diagnosis_count: int = 0
        self._write_session_start()

    # ── Machine ID ──

    def set_machine(self, machine_id: str) -> None:
        """Set the diagnostic target machine ID."""
        self.machine_id = machine_id

    # ── Diagnosis logging ──

    def write_diagnostics(self, symptom: str, content: str) -> None:
        """Record a correct diagnosis."""
        self.diagnosis_count += 1
        self._append_jsonl(RECORDS_DIR / "diagnostics.jsonl", {
            "time": datetime.now().isoformat(),
            "session": self.session_id,
            "machine": self.machine_id,
            "symptom": symptom,
            "content": content,
        })

    def write_misdiagnosis(self, symptom: str, content: str, failure_reason: str) -> None:
        """Record a misdiagnosis."""
        self.diagnosis_count += 1
        self._append_jsonl(RECORDS_DIR / "misdiagnosis.jsonl", {
            "time": datetime.now().isoformat(),
            "session": self.session_id,
            "machine": self.machine_id,
            "symptom": symptom,
            "content": content,
            "failure_reason": failure_reason,
        })

    def write_unknown(self, symptom: str, content: str) -> None:
        """Record an unresolved issue."""
        self.diagnosis_count += 1
        self._append_jsonl(RECORDS_DIR / "unknowns.jsonl", {
            "time": datetime.now().isoformat(),
            "session": self.session_id,
            "machine": self.machine_id,
            "symptom": symptom,
            "content": content,
        })

    # ── Log reading ──

    def read_log(self, filename: str) -> list[dict]:
        """Read all entries from a JSONL log file."""
        filepath = RECORDS_DIR / filename
        if not filepath.exists():
            return []
        entries: list[dict] = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        logging.getLogger(__name__).warning(
                            "Skipped malformed JSONL line in session log",
                        )
                        continue
        return entries

    def search_log(self, keyword: str, filename: str | None = None) -> list[dict]:
        """Search log entries for a keyword."""
        results: list[dict] = []
        files = [filename] if filename else [
            "diagnostics.jsonl", "misdiagnosis.jsonl", "unknowns.jsonl"
        ]
        kw_lower = keyword.lower()
        for fname in files:
            for entry in self.read_log(fname):
                searchable = " ".join(
                    str(v) for v in entry.values() if isinstance(v, str) and v
                )
                if kw_lower in searchable.lower():
                    results.append(entry)
        return results

    # ── Conversation logging ──

    def log_conversation(self, speaker: str, text: str) -> None:
        """Record a conversation turn in the session log."""
        filepath = SESSION_DIR / f"session_{self.session_id}.txt"
        timestamp = datetime.now().strftime("%H:%M:%S")
        label = "网管" if speaker == "operator" else "TCAI"
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {label}: {text}\n")

    def close(self) -> None:
        """Write session end marker."""
        filepath = SESSION_DIR / f"session_{self.session_id}.txt"
        end_time = datetime.now()
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"{'='*40}\n")
            f.write(f"End: {end_time.strftime('%Y-%m-%d %H:%M:%S')} CST\n")
            f.write(f"Diagnoses: {self.diagnosis_count}\n")

    def reset(self) -> None:
        """Reset session (close old, open new)."""
        self.close()
        self.session_id = datetime.now().strftime("%m%d-%H%M%S")
        self.machine_id = ""
        self.start_time = datetime.now()
        self._write_session_start()

    # ── Internal ──

    def _write_session_start(self) -> None:
        """Write session start header."""
        filepath = SESSION_DIR / f"session_{self.session_id}.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"TCAI v6 Session\n")
            f.write(f"Session ID: {self.session_id}\n")
            f.write(f"Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} CST\n")
            f.write(f"{'='*40}\n")

    @staticmethod
    def _append_jsonl(filepath: Path, entry: dict) -> None:
        """Append a JSON line to a file."""
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

