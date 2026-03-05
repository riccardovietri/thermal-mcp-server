# CLAUDE.md — Development Guide for thermal-mcp-server

## Project Overview

Python MCP server exposing GPU liquid cooling thermal analysis tools. Uses a
first-principles steady-state 1D thermal resistance network (not lookup tables).
Domain: datacenter cold plate design for H100, B200 NVL72, MI300X, Gaudi 3.

Key source files:
- `src/thermal_mcp_server/physics.py` — thermal/hydraulic engine
- `src/thermal_mcp_server/schemas.py` — Pydantic I/O models
- `src/thermal_mcp_server/mcp_server.py` — MCP tool definitions
- `docs/physics.md` — derivations, assumptions, limitations
- `tests/test_physics_behavior.py` — behavioral + hand-calc tests
- `tests/test_mcp_tools.py` — MCP output schema tests

---

## Workflow

### 1. Plan First

For any task with 3+ steps or architectural decisions, write a brief plan
before touching code. If the approach goes sideways, stop and re-plan — don't
push through.

### 2. Verify Before Done

Never mark a task complete without proving it works:
- Run `pytest -q` and confirm it passes
- For physics changes: include a hand-calculation that independently confirms
  the result (see `examples/validation_walkthrough.md` for the pattern)
- Diff behavior before and after when changing existing logic

### 3. Subagent Strategy

Offload research, file exploration, and parallel analysis to subagents to keep
the main context clean. One focused task per subagent.

### 4. Autonomous Bug Fixing

When given a bug report: find it, fix it, verify it. No hand-holding needed.
Point at failing tests or bad output, then resolve without asking for guidance.

---

## Physics Correctness Gate

**Before marking any physics change complete:**

1. **Units** — Every quantity must carry correct SI units. Check:
   - Temperatures in K for resistance calcs, °C for I/O
   - Flow in m³/s internally (convert from LPM at boundary)
   - Thermal resistance in K/W, not °C/W (they're equal but be explicit)

2. **Dimensional consistency** — New equations must be dimensionally correct.
   When in doubt, write out the unit chain in a comment.

3. **Energy balance** — Confirm: `Q = ṁ·cp·ΔT_coolant` closes within <1%
   against the resistance-network junction temperature for any new test case.

4. **Document the change** — Update `docs/physics.md` with justification.
   Add a test in `test_physics_behavior.py` with a hand-calculated reference
   value. See the existing `test_hand_calculation_700w_10lpm_water` pattern.

---

## Ask vs. Proceed — Domain Tradeoffs

These scenarios involve genuine design choices or modeling boundaries. Surface
options and tradeoffs rather than silently picking one:

**Ask when:**
- Series vs. parallel cooling loop configuration — affects flow split, ΔP,
  and per-GPU thermal margin differently; not a trivial pick
- Coolant choice beyond water/glycol50 — requires property source citation
  and viscosity/conductivity tradeoffs at operating temperature
- Target junction temp selection — depends on chip throttle threshold, which
  varies by SKU and workload; don't assume 85°C
- Geometry changes to channel count, Dh, or length — these shift Re regime
  and can flip laminar↔turbulent unexpectedly
- Any request that bumps against a known model limitation (no manifold losses,
  no 2D spreading, no transient response, no boiling) — flag the gap and ask
  whether to proceed with the simplification or note it as out of scope

**Proceed without asking:**
- Single-point analysis, flow optimization, coolant comparison within existing
  tools
- Bug fixes with clear root cause
- Test additions, schema changes, documentation updates

---

## Test Harness

Use `pytest` — it's the only test runner.

```bash
pytest -q                  # fast check, matches CI
pytest -v                  # verbose, use when debugging a specific failure
pytest --cov=thermal_mcp_server --cov-report=term-missing  # coverage
```

**Test placement:**
- Physics behavior, monotonicity, regime transitions, hand-calc validation →
  `tests/test_physics_behavior.py`
- MCP tool output schema and field presence → `tests/test_mcp_tools.py`

**Hand-calc test pattern** (required for new physics):
```python
def test_hand_calculation_<description>():
    # Hand calc: Re = ..., Nu = ..., h = ..., Tj = ...
    result = analyze(AnalyzeColdplateInput(...))
    assert abs(result.junction_temp_c - EXPECTED) < 0.5  # °C tolerance
```

CI runs `pytest -q` on Python 3.11 via GitHub Actions.

---

## Commit Convention

Follow conventional commits:
- `feat:` — new tool, new coolant, new physics capability
- `fix:` — bug in physics, schema, or MCP wiring
- `test:` — test additions or corrections
- `docs:` — physics.md, mcp.md, examples
- `refactor:` — restructuring without behavior change

---

## Core Principles

- **Simplicity first** — minimum code for the current task. No speculative
  abstractions, no future-proofing.
- **No temporary fixes** — find the root cause. Don't paper over physics bugs
  with clamping or fudge factors.
- **Minimal impact** — changes touch only what's necessary. A bug fix doesn't
  need surrounding cleanup.
