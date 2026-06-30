"""
TCAI v6 — launcher script.

Handles sys.path setup so Start.bat can invoke this directly
without relying on PYTHONPATH environment variable.
"""
from __future__ import annotations

import sys
from pathlib import Path

# HACK: Entry-point path setup — PYTHONPATH may not propagate
# through all execution contexts (batch → subprocess chains).
# This is the ONLY file in the project with sys.path manipulation.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tcai.agent.main import main

if __name__ == "__main__":
    main()
