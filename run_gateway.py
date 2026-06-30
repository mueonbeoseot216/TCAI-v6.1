"""
TCAI Gateway — stdio entry point.

Spawned by the Agent as a subprocess; communicates via stdin/stdout JSON-RPC.
"""
from __future__ import annotations

import sys
from pathlib import Path

# HACK: Subprocess entry-point path setup — PYTHONPATH not reliably
# propagated through subprocess.Popen on all Windows configurations.
# This is one of only TWO files in the project with sys.path manipulation
# (the other is launcher.py). See CODING_STANDARDS.md §3.3.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tcai.gateway.server import mcp_main

if __name__ == "__main__":
    mcp_main()
