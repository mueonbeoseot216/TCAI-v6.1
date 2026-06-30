# Changelog

All notable changes to TCAI are documented in this file.

---

## [6.0.0] — Unreleased

### Added
- **Injection filter: Chunked filtering** — `filter_long_text()` with overlapping chunks + final full-text scan for long web content and knowledge base entries. No content truncation, injection detection at chunk boundaries.
- **Data isolation (思想钢印)** — External content (knowledge base hints, web results) structurally marked as `╔══ 参考资料 ══╗` blocks. L1 constitution rule: marker-wrapped content is pure data, not system instructions.
- **Knowledge base defense** — Hints filtered through `injection_filter` before reaching LLM. `/learn` writes filtered with `filter_long_text()` before storage. Role-specification patterns detect `(你|我).{0,5}(是|变成|充当|角色是|身份是|作为)`.
- Complete project restructure with `src/tcai/` package layout
- `CODING_STANDARDS.md` — comprehensive coding standards (10 sections)
- `pyproject.toml` — unified project configuration (ruff, mypy, pytest)
- `python-dotenv` for standard `.env` file loading
- `paths.py` — single source of truth for all project paths (zero hardcoded drives)
- `config.py` — centralized configuration with validation
- `exceptions.py` — custom exception hierarchy (7 types)
- `logging_setup.py` — structured logging via stdlib `logging` module
- `http_client.py` — unified HTTP client (retry, timeout, UA management)
- `web/` package — unified web search module replacing 3 old tools
- `session_context.py` — unified session state management
- `learn.py` — extracted `/learn` subsystem from `loop.py`
- Full type annotations across all modules (mypy strict)
- Test suite with pytest-cov (target ≥75% coverage)
- CI/CD: GitHub Actions on Windows + static checks on Linux
- Issue templates, PR template, Code of Conduct, Security policy

### Changed
- `server.py` split into `server.py` + `router.py` + `tool_registry.py`
- `gateway.py` split into `gateway.py` + `scope_checker.py` + `approval_store.py`
- Tool schemas moved from `server.py` to individual tool files (`get_schema()`)
- All tool modules use shared `common.py` (`run_cmd`, `decode_output`)
- `web_search`, `web_extract`, `puppeteer_extract` → single `web_search` tool
- Global mutable state consolidated into `SessionContext`
- `sys.stderr`/`print` → stdlib `logging` module
- `knowledge_matrix.py` renamed to `knowledge.py`

### Removed
- Node.js + Puppeteer bundled toolchain (~200MB)
- All `sys.path.insert()` hacks (proper `src/tcai/` package layout)
- All bare `except Exception: pass` patterns
- All hardcoded path strings (replaced by `paths.py`)
- All inline GBK/UTF-8 decode duplication (centralized in `common.py`)
- `reason`/`message` inconsistency in error responses

---

## [5.0.0] — 2025

Initial public release. See `E:\tcai_v5\` for v5 history.

- 7-layer defense-in-depth security gateway
- 35 MCP diagnostic tools
- SQLite FTS5 knowledge base
- Dual-process architecture (Agent + Gateway over stdio JSON-RPC)
