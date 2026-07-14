# TCAI v6.1

**AI Agent Security Execution Framework for Windows Diagnostics**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)

> ⚠️ **Windows only.** There is no Linux version.
> Linux developers: you can read the code and run static checks (ruff/mypy).

---

## What is TCAI?

TCAI (ThinCore AI) is a self-contained AI agent for Windows PC diagnostics in
internet cafe / diskless environments. ~10,000 lines of pure Python with only
2 core dependencies (pyyaml + python-dotenv).

**Security architecture:** A 7-layer defense-in-depth gateway decoupled from
the LLM — injection filtering, scope checks, deobfuscation, AST rule matching,
circuit breaker, and audit logging. Zero tokens spent on security prompting.

## Architecture

```
User Input → Agent Loop (LLM) → MCP Gateway (stdio JSON-RPC) → Windows Tools
                  │                        │
                  │              ┌─────────┼──────────┐
                  │              │  7-Layer Security  │
                  │              │  Pipeline:         │
                  │              │  0. Injection Filter│
                  │              │     (chunked+marker)│
                  │              │  1. Scope Check    │
                  │              │  2. Deobfuscation  │
                  │              │  3. AST Rules      │
                  │              │  4. Intent Chain   │
                  │              │  5. Circuit Breaker│
                  │              │  6. Dispatch       │
                  │              └─────────┼──────────┘
                  │                        │
          Knowledge Base (structured dict index)    31 Tools (21 RO + 10 RW)
           ↗ filtered + marker
```

## Features

- **7-layer security** — injection filter (chunked), scope check, deobfuscation, AST rules, intent chain, circuit breaker, dispatch
- **Data isolation** — external content structurally marked as non-instruction; LLM cannot treat data as commands
- **Knowledge base defense** — `/learn` writes filtered before storage; KB hints filtered + marker-wrapped before LLM
- **31 diagnostic tools** — process, registry, file, services, web, WMI, GPU, runtime, blue screen, anti-cheat
- **Structured knowledge base** — pure Python dict indexes, no FTS5/SQLite, zero query-injection surface
- **Zero-framework Agent** — no LangChain, no AutoGPT, no Hermes; pure Python stdlib
- **Conversation memory** — session-spanning context with sliding window for coherent multi-turn diagnostics
- **CI-ready** — ruff + mypy + tcai_lint in pre-commit and GitHub Actions
- **Portable** — zero hardcoded drive letters; works from any disk (removable/mobile)
- **Audit logging** — JSONL append-only log of every security decision

## Quick Start

### Prerequisites
- Windows 10 or 11
- Python 3.11+
- DeepSeek API key ([get one here](https://platform.deepseek.com))

### Install

```batch
git clone <repo-url>
cd TCAI-v6.1
install.bat
```

### Configure

Copy the environment template and add your API key:
```batch
copy .env.example home\.env
notepad home\.env
```

### Run

```batch
Start.bat
```

You'll see the TCAI banner, then type your diagnostic question:
```
  网管: 英雄联盟崩溃报错 3A 怎么解决？
```

### Commands

| Command | Description |
|---------|-------------|
| `/help` | 显示帮助 |
| `/new` | 开始新会话 |
| `/machine <id>` | 设置机器编号 |
| `/learn <path>` | 从会话日志提取知识 |
| `/exit` | 退出 |

## Documentation

| Document | Content |
|----------|---------|
| [USER_GUIDE.md](USER_GUIDE.md) | 使用教程、文件说明、命令参考、知识库格式 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full system architecture |
| [CODING_STANDARDS.md](CODING_STANDARDS.md) | Coding standards (10 sections) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community standards |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting |

## License

GNU AGPL v3. Copyright co-held by all contributors. See [LICENSE](LICENSE) and [AUTHORS](AUTHORS).

---

*Built for internet cafe diskless environments. 7 layers of defense. Zero-token security overhead.*
