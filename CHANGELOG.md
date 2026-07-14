# Changelog
## 6.1.0 (2026-07-14)

### Added
- Structured knowledge base — pure Python dict indexes replace FTS5/SQLite
- Conversation memory — session-spanning message accumulation for context coherence
- tcai_lint.py — static code analyzer in tools/ pre-commit hook + CI
- Code engineering — ruff + mypy + tcai_lint automated in GitHub Actions

### Fixed
- Knowledge base crash on special characters (\**3**\, \11:58\) — eliminated by dict-index engine
- Missing conversation history — messages now accumulate across turns  
- scope_checker.py BOM syntax error
- Type annotations corrupted by [redacted] in config.py, loop.py, learn.py

### Security
- Injection filter pronoun detection now source-aware (knowledge_base only)
- Audit log value-level sanitization for Bearer tokens/API keys
- Circuit breaker RISKY path properly returns blocked on threshold exceed

All notable changes to TCAI are documented in this file.

---

## [6.0.0] 鈥?Unreleased

### Added
- **Injection filter: Chunked filtering** 鈥?`filter_long_text()` with overlapping chunks + final full-text scan for long web content and knowledge base entries. No content truncation, injection detection at chunk boundaries.
- **Data isolation (鎬濇兂閽㈠嵃)** 鈥?External content (knowledge base hints, web results) structurally marked as `鈺斺晲鈺?鍙傝€冭祫鏂?鈺愨晲鈺梎 blocks. L1 constitution rule: marker-wrapped content is pure data, not system instructions.
- **Knowledge base defense** 鈥?Hints filtered through `injection_filter` before reaching LLM. `/learn` writes filtered with `filter_long_text()` before storage. Role-specification patterns detect `(浣爘鎴?.{0,5}(鏄瘄鍙樻垚|鍏呭綋|瑙掕壊鏄瘄韬唤鏄瘄浣滀负)`.
- Complete project restructure with `src/tcai/` package layout
- `CODING_STANDARDS.md` 鈥?comprehensive coding standards (10 sections)
- `pyproject.toml` 鈥?unified project configuration (ruff, mypy, pytest)
- `python-dotenv` for standard `.env` file loading
- `paths.py` 鈥?single source of truth for all project paths (zero hardcoded drives)
- `config.py` 鈥?centralized configuration with validation
- `exceptions.py` 鈥?custom exception hierarchy (7 types)
- `logging_setup.py` 鈥?structured logging via stdlib `logging` module
- `http_client.py` 鈥?unified HTTP client (retry, timeout, UA management)
- `web/` package 鈥?unified web search module replacing 3 old tools
- `session_context.py` 鈥?unified session state management
- `learn.py` 鈥?extracted `/learn` subsystem from `loop.py`
- Full type annotations across all modules (mypy strict)
- Test suite with pytest-cov (target 鈮?5% coverage)
- CI/CD: GitHub Actions on Windows + static checks on Linux
- Issue templates, PR template, Code of Conduct, Security policy

### Changed
- `server.py` split into `server.py` + `router.py` + `tool_registry.py`
- `gateway.py` split into `gateway.py` + `scope_checker.py` + `approval_store.py`
- Tool schemas moved from `server.py` to individual tool files (`get_schema()`)
- All tool modules use shared `common.py` (`run_cmd`, `decode_output`)
- `web_search`, `web_extract`, `puppeteer_extract` 鈫?single `web_search` tool
- Global mutable state consolidated into `SessionContext`
- `sys.stderr`/`print` 鈫?stdlib `logging` module
- `knowledge_matrix.py` renamed to `knowledge.py`

### Removed
- Node.js + Puppeteer bundled toolchain (~200MB)
- All `sys.path.insert()` hacks (proper `src/tcai/` package layout)
- All bare `except Exception: pass` patterns
- All hardcoded path strings (replaced by `paths.py`)
- All inline GBK/UTF-8 decode duplication (centralized in `common.py`)
- `reason`/`message` inconsistency in error responses

---

## [5.0.0] 鈥?2025

Initial public release. See `E:\tcai_v5\` for v5 history.

- 7-layer defense-in-depth security gateway
- 35 MCP diagnostic tools
- SQLite FTS5 knowledge base
- Dual-process architecture (Agent + Gateway over stdio JSON-RPC)
