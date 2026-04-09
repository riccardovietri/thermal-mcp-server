# AGENTS.md — thermal-mcp-server

Cross-agent project memory for Codex, Claude Code, and other coding agents.
Read this file first. Use it as the tool-neutral contract. For deeper project
detail, then read `CLAUDE.md`. For durable design decisions, read `docs/decisions.md`.

## Purpose

This repo is a Python MCP server for first-principles thermal analysis of
liquid-cooled GPU cold plates and simple rack topologies.

Primary audience: thermal engineers and AI infrastructure teams.
Primary portfolio goal: show physics credibility and practical AI tooling for
H100/B200-class cooling analysis.

## Source of truth

Use the memory layers in this order:

1. `AGENTS.md` — stable, cross-agent operating contract
2. `CLAUDE.md` — project-specific workflow and detailed modeling guidance
3. `docs/decisions.md` — durable architectural and modeling decisions
4. Code and tests — final authority on actual implementation

Do not rely on chat/session memory for anything that should survive across
agents or across days. If it matters later, write it into one of the files
above.

## Architecture

Core modules:

- `src/thermal_mcp_server/schemas.py` — Pydantic models, defaults, validation
- `src/thermal_mcp_server/physics.py` — thermal and hydraulic calculations
- `src/thermal_mcp_server/mcp_server.py` — thin FastMCP wrappers
- `tests/test_physics_behavior.py` — numerical and hand-calculation validation

Public Python entrypoints:

- `analyze()`
- `analyze_rack()`
- `optimize_flow()`

MCP tools:

- `analyze_coldplate`
- `compare_coolants`
- `optimize_flow_rate`
- `analyze_rack`

## Working rules

- Keep physics in `physics.py`, not in MCP wrapper code.
- Treat defaults and coolant constants as controlled values.
- Any physics change must update `docs/physics.md` and corresponding tests.
- If a change affects expected numerical output, add or update a hand-calculation
  test in `tests/test_physics_behavior.py`.
- Do not weaken tolerances in hand-calculation tests without explicit approval.
- Surface API-breaking schema changes before making them.

## Memory placement

Put information in the right place:

- `AGENTS.md`: stable instructions all agents should follow
- `CLAUDE.md`: richer workflow notes, guardrails, review protocol
- `docs/decisions.md`: durable decisions that should survive after the current branch dies

## Autonomy and self-verification

Before starting any non-trivial task:
- If requirements are ambiguous, ask clarifying questions before writing code.
- State your plan and the acceptance criteria you will verify against.

While working:
- Run `uv run pytest -v` after every meaningful change.
- If a test fails, fix it before continuing. Do not relax tolerances.
- Surface design decisions rather than guessing.

Before finishing:
- All tests must pass.
- State what changed, what was tested, what passed, and any follow-up needed.

## Current priorities

The original gaps called out during the portfolio push are now merged:

1. Rack-level model
2. MCP tool test completeness
3. Sensitivity / uncertainty output

Current likely next engineering tasks:

1. Keep the release path healthy (`uv build`, publish workflow, installability)
2. Add PR benchmark diff or equivalent reviewer-facing benchmark visibility
3. Keep rack-level model scope disciplined unless manifold losses are modeled properly

Check `docs/decisions.md` for durable context before starting work.
