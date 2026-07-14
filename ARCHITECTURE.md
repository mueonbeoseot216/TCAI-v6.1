# TCAI v6.1 鈥?Architecture

> This document will be updated as modules are migrated from v5.
> For the v5 architecture, see `E:\tcai_v5\ARCHITECTURE.md`.

## High-Level Architecture

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?                  TCAI v6.1                           鈹?鈹?                                                    鈹?鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?    stdio JSON-RPC    鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?鈹? 鈹? Agent Layer 鈹?鈼勨攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈻?鈹?Gateway 鈹?鈹?鈹? 鈹?             鈹?                     鈹? Layer  鈹?鈹?鈹? 鈹? main.py     鈹?                     鈹?server  鈹?鈹?鈹? 鈹? loop.py     鈹?                     鈹?gateway 鈹?鈹?鈹? 鈹? learn.py    鈹?                     鈹?router  鈹?鈹?鈹? 鈹? mcp_client  鈹?                     鈹?tools/  鈹?鈹?鈹? 鈹? prompt_*    鈹?                     鈹?web/    鈹?鈹?鈹? 鈹? knowledge   鈹?                     鈹?audit   鈹?鈹?鈹? 鈹? session     鈹?                     鈹?...     鈹?鈹?鈹? 鈹? ui          鈹?                     鈹?        鈹?鈹?鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                     鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?鈹?                                                    鈹?鈹? Dependencies: pyyaml, python-dotenv (core)         鈹?鈹? Optional: httpx, beautifulsoup4, rich              鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

## Package Layout

```
src/tcai/
鈹溾攢鈹€ agent/          # Agent 鈥?LLM interaction, user interface
鈹?  鈹溾攢鈹€ main.py         Entry point, command routing
鈹?  鈹溾攢鈹€ loop.py         LLM call loop, tool orchestration
鈹?  鈹溾攢鈹€ learn.py        /learn knowledge extraction
鈹?  鈹溾攢鈹€ mcp_client.py   stdio JSON-RPC client
鈹?  鈹溾攢鈹€ prompt_engine.py 5-layer chained prompts
鈹?  鈹溾攢鈹€ prompt_gate.py  Zero-token security monitor
鈹?  鈹溾攢鈹€ knowledge.py    SQLite FTS5 knowledge base
鈹?  鈹溾攢鈹€ session.py      Session recording
鈹?  鈹斺攢鈹€ ui.py           Terminal UI
鈹?鈹溾攢鈹€ gateway/        # Gateway 鈥?security pipeline + tools
鈹?  鈹溾攢鈹€ paths.py            All project paths (from __file__)
鈹?  鈹溾攢鈹€ config.py           Centralized configuration
鈹?  鈹溾攢鈹€ exceptions.py       Custom exception hierarchy
鈹?  鈹溾攢鈹€ logging_setup.py    Structured logging
鈹?  鈹溾攢鈹€ http_client.py      Unified HTTP client
鈹?  鈹溾攢鈹€ server.py           MCP JSON-RPC main loop + routing
鈹?  鈹溾攢鈹€ tool_registry.py    Schema collection from tools
鈹?  鈹溾攢鈹€ gateway.py          6-step security pipeline orchestrator
鈹?  鈹溾攢鈹€ scope_checker.py    Path scope validation
鈹?  鈹溾攢鈹€ session_context.py  Unified session state + approvals
鈹?  鈹溾攢鈹€ ast_rules.py        AST rule engine
鈹?  鈹溾攢鈹€ deobfuscate.py      4-stage deobfuscation
鈹?  鈹溾攢鈹€ injection_filter.py Injection detection + chunked filtering
鈹?  鈹溾攢鈹€ dlp.py              Data leak prevention
鈹?  鈹溾攢鈹€ circuit_breaker.py  4D circuit breaker
鈹?  鈹溾攢鈹€ audit.py            JSONL audit logging
鈹?  鈹溾攢鈹€ knowledge_bridge.py Cross-layer knowledge access
鈹?  鈹溾攢鈹€ web/                Web search module
鈹?  鈹?  鈹溾攢鈹€ search_engine.py
鈹?  鈹?  鈹斺攢鈹€ content_extractor.py
鈹?  鈹斺攢鈹€ tools/              Diagnostic tools (31)
鈹?      鈹溾攢鈹€ common.py       Shared run_cmd / decode_output
鈹?      鈹溾攢鈹€ readonly/       21 read-only tools
鈹?      鈹斺攢鈹€ write/          10 write tools
鈹?鈹斺攢鈹€ prompts/         # 5-layer chained prompt texts
```

## Data Flow

```
User Input
    鈹?    鈻?AgentLoop.run()
    鈹?    鈹溾攢鈹€ knowledge.search()        # structured dict index (in-memory)
    鈹?    鈹溾攢鈹€ _call_llm()               # DeepSeek API
    鈹?      鈹?    鈹?      鈻?    鈹?  LLM Response (may include tool_calls)
    鈹?      鈹?    鈹?      鈹溾攢鈹€ Tool Call 鈫?mcp_client.call_tool()
    鈹?      鈹?      鈹?    鈹?      鈹?      鈻?    鈹?      鈹?  Gateway.handle_tool_call()
    鈹?      鈹?      鈹?    鈹?      鈹?      鈹溾攢鈹€ tool_loop_guard.check()
    鈹?      鈹?      鈹溾攢鈹€ [readonly] 鈫?dlp.check() 鈫?execute
    鈹?      鈹?      鈹斺攢鈹€ [write] 鈫?6-step pipeline 鈫?execute
    鈹?      鈹?    鈹?      鈹斺攢鈹€ Final Text 鈫?session.record() 鈫?UI.response()
    鈹?    鈹斺攢鈹€ repeat until no more tool_calls
```

## Security Pipeline (write tools)

```
handle_write()
    鈹?    鈹溾攢鈹€ 1. Scope Check      鈫?path in allowed scope?
    鈹溾攢鈹€ 2. Deobfuscation     鈫?4-stage normalization
    鈹溾攢鈹€ 3. AST Rules         鈫?allowlist/blocklist match
    鈹溾攢鈹€ 4. Intent Chain      鈫?cross-session attack pattern?
    鈹溾攢鈹€ 5. Circuit Breaker   鈫?rate/block/reject/score check
    鈹斺攢鈹€ 6. Dispatch          鈫?SAFE execute / RISKY approve / BLOCKED reject
            鈹?            鈻?        audit.log (JSONL append-only)
```
