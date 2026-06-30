# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 6.x     | ✅ Active |
| 5.x     | ❌ Deprecated |

## Reporting a Vulnerability

**DO NOT open a public issue for security vulnerabilities.**

Instead, please report via:
1. GitHub Security Advisory: "Report a vulnerability" in the Security tab
2. Or contact the maintainers directly

## What to Include

- Type of vulnerability
- Steps to reproduce
- Affected versions
- Suggested fix (if any)

## Response Timeline

- Acknowledgment: within 48 hours
- Fix release: within 7 days for critical, 30 days for moderate

## Security Architecture

TCAI v6 uses a 7-layer defense-in-depth security gateway:

1. Scope check (path restrictions)
2. Deobfuscation (anti-bypass)
3. AST rule matching (allowlist/blocklist)
4. Intent chain tracking (cross-session attacks)
5. Circuit breaker (rate/block/reject/score)
6. Dispatch (safe/risky/blocked)
7. Audit logging (JSONL append-only)

All write operations pass through this pipeline independent of the LLM.
