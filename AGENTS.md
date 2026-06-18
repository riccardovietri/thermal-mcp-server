# AGENTS.md — thermal-mcp-server

AI agent instructions for Codex, Claude Code, and other coding agents.

## Primary instruction files

Read these before making changes:

- **`CLAUDE.md`** — project workflow, physics modeling rules, test conventions, and agent instructions
- **`docs/decisions.md`** — durable architectural decisions (ROI separation, physics-change protocol, etc.)
- **`docs/physics.md`** — full physics derivation, assumptions, and documented limitations

CLAUDE.md is the authoritative source for this repo. This file exists to ensure
Codex discovers it via the AGENTS.md search path.

## Architecture in 30 seconds

```
schemas.py          ← Pydantic I/O models
physics.py          ← All math (no business logic)
decision_report.py  ← Synthesis layer (composes physics APIs, no new math)
mcp_server.py       ← FastMCP tool wrappers (thin — no physics or synthesis here)
```

Five MCP tools: `analyze_coldplate`, `compare_coolants`, `optimize_flow_rate`,
`analyze_rack`, `generate_decision_report`.

## Physics change protocol (enforced)

1. Document justification in `docs/physics.md`
2. Add a test in `tests/test_physics_behavior.py`
3. If changing defaults or correlation constants, add a hand-calculation validation test

## Test conventions

```
pytest          # run all tests
pytest -v       # verbose
```

- `tests/test_physics_behavior.py` — behavioral + numerical; keep tolerances tight
- `tests/test_mcp_tools.py` — MCP layer contract tests
- `tests/test_decision_report.py` — decision synthesis tests

## What NOT to do

- Do not add physics to `mcp_server.py` or `decision_report.py`
- Do not add ROI/financial calculations to this repo (see `docs/decisions.md`)
- Do not weaken hand-calculation validation tests
- Do not change geometry defaults or coolant properties without a hand-calc update
