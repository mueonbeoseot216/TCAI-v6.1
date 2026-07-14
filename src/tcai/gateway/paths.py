"""
TCAI path resolution — single source of truth for all project paths.

All paths are derived from __file__ (zero hardcoded drive letters).
Every module in the project must import paths from here; no bare path strings allowed.

Usage:
    from tcai.gateway.paths import WORK_DIR, PROMPTS_DIR

Architecture note:
    paths.py is at src/tcai/gateway/paths.py
    PROJECT_ROOT = parent of src/
"""
from __future__ import annotations

from pathlib import Path


def _init_project_root() -> Path:
    """Derive project root from this file's location.

    paths.py is at:  src/tcai/gateway/paths.py
    PROJECT_ROOT is:  parent of src/
    """
    return Path(__file__).resolve().parent.parent.parent.parent


# === Project root (the directory containing src/, tests/, home/, etc.) ===
PROJECT_ROOT: Path = _init_project_root()

# === Top-level directories ===
SRC_DIR: Path = PROJECT_ROOT / "src"
TCS_PACKAGE: Path = SRC_DIR / "tcai"
PROMPTS_DIR: Path = TCS_PACKAGE / "prompts"
HOME_DIR: Path = PROJECT_ROOT / "home"
WORK_DIR: Path = PROJECT_ROOT / "work"
RECORDS_DIR: Path = PROJECT_ROOT / "records"
TESTS_DIR: Path = PROJECT_ROOT / "tests"

# === Runtime sub-directories ===
AUDIT_LOG: Path = WORK_DIR / "audit.log"
OP_INDEX: Path = WORK_DIR / "op_index.jsonl"
SNAPSHOT_DIR: Path = WORK_DIR / "snapshots"
TMP_DIR: Path = WORK_DIR / "tmp"
SESSION_DIR: Path = RECORDS_DIR / "sessions"

# === Files ===
ENV_FILE: Path = HOME_DIR / ".env"

# === Ensure runtime directories exist ===
for _d in [HOME_DIR, WORK_DIR, RECORDS_DIR, SNAPSHOT_DIR, TMP_DIR, SESSION_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

