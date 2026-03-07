# CLAUDE.md — thermal-mcp-server

Project context for Claude Code sessions. Read before making changes.

## What this is

A Python MCP server that exposes thermal physics for liquid-cooled GPU cold plates.
Target audience: data center thermal engineers, AI infrastructure teams.
Portfolio goal: demonstrate physics credibility + AI tooling at H100/B200 scale.

## Architecture in 30 seconds

```
schemas.py          ← Pydantic I/O models, validation, defaults
physics.py          ← All math: 1D resistance network, Dittus-Boelter, Darcy-Weisbach
mcp_server.py       ← FastMCP tool wrappers (thin — no physics here)
```

Four MCP tools: `analyze_coldplate`, `compare_coolants`, `optimize_flow_rate`, `analyze_rack`.
Public Python API: `analyze()`, `analyze_rack()`, and `optimize_flow()` in `physics.py`.

## Physics: what the model does and does not do

**Does:**
- Steady-state 1D resistance network: R_jc → R_tim → R_base → R_conv
- Rectangular channel hydraulic diameter: Dh = 2wh/(w+h)
- Dittus-Boelter Nu for turbulent, Nu=4.36 for laminar, linear blend 2300–4000
- Darcy-Weisbach ΔP with Blasius friction, same transition blend
- Pump power = ΔP × Q / 0.50 (50% efficiency assumption, documented inline)
- Binary-search flow optimization
- Rack-level model: N identical GPUs in series or parallel topology
  (see `docs/physics.md` Section G)

**Does not (known limitations, do not paper over):**
- No manifold/header pressure losses (rack model uses cold plate ΔP only)
- No heterogeneous GPU racks (all GPUs assumed identical)
- No transient thermal capacitance
- No 2D spreading resistance
- No temperature-dependent fluid properties
- No flow maldistribution across channels or parallel branches
- No boiling/two-phase

These are documented in `docs/physics.md` sections E and G. Do not add hacks to
simulate them — add them properly or leave them out.

## Physics change protocol

From `CONTRIBUTING.md` — enforced:

1. Document justification in `docs/physics.md`
2. Add a test in `tests/test_physics_behavior.py`
3. If changing defaults or correlation constants, add a hand-calculation
   validation test showing expected numerical output

The `test_hand_calc_validation_700w_water` test is the canonical example.
It derives every intermediate value independently and checks against model output.
Do not weaken this test.

## Test conventions

- `tests/test_physics_behavior.py` — behavioral + numerical. Has hand-calc tests.
  Keep numerical tolerances tight (< 1°C on Tj, < 5 on Re).
- `tests/test_mcp_tools.py` — MCP layer smoke tests. Currently thin; known gap.
  Error paths (ValidationError → `{"error": [...]}`) should be tested here.

Run with: `pytest` (or `pytest -v` for detail).

## Key defaults (do not change without hand-calc update)

```
channel_count  = 40
channel_width  = 1.0 mm
channel_height = 1.0 mm   # → Dh = 1.0 mm for square default
channel_length = 80 mm
base_thickness = 2.0 mm
contact_area   = 0.01 m²
copper_k       = 385 W/m·K
R_jc           = 0.04 K/W
R_tim          = 0.02 K/W
flow_rate      = 8 LPM
inlet_temp     = 25°C
coolant        = water
```

Default case (700W, 8 LPM, water, 25°C) → Tj ≈ 70.9°C, transitional regime.
This number appears in README and is checked in `test_hand_calc_validation_default_case`.

## Coolant table

| Name      | ρ (kg/m³) | cp (J/kg·K) | k (W/m·K) | μ (Pa·s) | Notes |
|-----------|-----------|-------------|-----------|----------|-------|
| water     | 997       | 4180        | 0.60      | 0.00089  | 25°C nominal |
| glycol50  | 1060      | 3400        | 0.40      | 0.00480  | Ethylene glycol 50% by vol, 25°C. Propylene glycol: μ ~60-80% higher |

Adding a coolant requires updating `CoolantName` in `schemas.py` and the `COOLANTS`
dict in `physics.py` with a cited source for property values.

## Chip reference data (in examples/)

`examples/real_chip_benchmarks.py` contains vendor-cited TDP and Tj specs:
- H100 SXM: 700W, 83°C throttle onset (NVIDIA datasheet)
- B200 NVL72: 1200W, 75°C (SemiAnalysis estimate, not NVIDIA-published)
- MI300X: 750W, 85°C proxy (AMD does not publish Tj_max)
- Gaudi 3 OAM: 900W air / 1200W liquid, 85°C proxy (Intel does not publish)

Do not change these without a current source citation.

## Known gaps (prioritized)

See `docs/strategy.md` for full context and `docs/agent-notes.md` for current
status and implementation specs. In order of portfolio impact:

1. ~~**Rack-level model**~~ — **DONE** (PR11). `analyze_rack()` supports series
   and parallel topologies. Hand-calc validated. See `docs/physics.md` Section G.

2. **MCP test completeness** — error paths, `met_target: False` case,
   geometry passthrough, `compare_coolants` depth check, `analyze_rack` smoke test.
   ~20 min effort. Should be done before PR12.

3. **Sensitivity / uncertainty output** — ∂Tj/∂Q, ∂Tj/∂R_tim, ∂Tj/∂T_inlet.
   Results currently look falsely precise. R_jc has ±20% mfg variation;
   TIM resistance doubles over 2–3 years of operation. Add `margin_c` to
   `optimize_flow_rate`. See `docs/agent-notes.md` for implementation options.

## Ask vs. proceed

Stop and surface to the user before proceeding when the change involves:
- Geometry defaults (channel dimensions, contact area, copper_k) — affects hand-calc tests
- Temperature targets or Tj limits in examples/
- Coolant property values or adding a new coolant
- Any model limitation that should be disclosed to the caller
- API-breaking schema changes (renaming or removing fields)

Proceed autonomously for:
- Single-point analysis, bug fixes, test additions
- Documentation and docstring updates
- Adding new examples that don't change existing behavior
- Refactoring that doesn't touch physics equations

## Physics correctness gate

Before marking any physics change as done, verify:
1. Units are consistent — resistance calcs in Kelvin, I/O in Celsius
2. Dimensional analysis passes — check every term in each equation
3. Energy balance closes within 1%: Q_input ≈ m_dot × cp × ΔT_coolant + losses
4. `docs/physics.md` updated with justification
5. Hand-calc test added or updated with new expected values
6. `pytest` passes with no tolerance relaxation

## Branch / PR conventions

- Main branch is the stable baseline. PRs from `claude/` branches.
- Commit style: `fix:`, `feat:`, `docs:`, `examples:`, `test:`
- Physics changes need hand-calc validation before merge (see above).
- See `docs/strategy.md` for roadmap and the ROI calculator decision.
- See `docs/agent-notes.md` for session-by-session work log, queued tasks,
  implementation specs, and automation plans. Read it first in new sessions.
