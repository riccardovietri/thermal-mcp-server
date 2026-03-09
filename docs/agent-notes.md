# Agent Notes — thermal-mcp-server

Living document for AI coding agents. Updated each session. Summarizes work done,
decisions made, and queued tasks so future agents can orient quickly.

*Last updated: 2026-03-09*

---

## Current branch

`claude/mcp-tests-and-ci-ODSRh` (PR10)

---

## Status

PR10 (MCP test completeness + daily regression CI) is **implemented (34/34 tests), ready to push**.
Branch `claude/mcp-tests-and-ci-ODSRh` targets main.

PR11 (rack-level model) is **merged**.
Branch `claude/review-project-strategy-ODSRh` is ready for PR creation and merge.
CLAUDE.md has been updated to reflect the new `analyze_rack` tool and revised gap list.

Repo memory now has a cross-agent structure:
- `AGENTS.md` added as the tool-neutral entrypoint
- `docs/decisions.md` added for durable architectural/modeling decisions
- `docs/local-agent-bootstrap.md` added with a reusable prompt for local agent setup

---

## Work completed (this session)

### PR10: MCP test completeness + daily regression CI

Added comprehensive tests to `tests/test_mcp_tools.py` (3 → 21 tests, 34 total):

**Error paths tested:**
- `analyze_coldplate_impl(heat_load_w=-1)` → `{"error": [...]}`
- Invalid coolant name → `{"error": [...]}`
- Zero flow → `{"error": [...]}`
- Invalid geometry extra key (extra="forbid") → `{"error": [...]}`
- `compare_coolants_impl(heat_load_w=-1)` → `{"error": [...]}`
- `optimize_flow_rate_impl(flow_min=10, flow_max=5)` → `{"error": [...]}`
- `analyze_rack_impl(topology="diagonal")` → `{"error": [...]}`
- `analyze_rack_impl(gpu_count=0)` → `{"error": [...]}`

**Depth and behavior checks:**
- `compare_coolants`: both coolant results have actual float fields (not just keys); glycol Tj > water Tj
- `optimize_flow_rate`: feasible target → `met_target=True`, result ≤ target; infeasible (Tj=25°C) → `met_target=False, analysis=None`
- `analyze_rack` parallel: all GPUs identical Tj
- Geometry passthrough: `channel_count=20` produces different Re/Tj than default 40 channels

**GitHub Actions:**
- Added `.github/workflows/daily-regression.yml`
  - Runs at 6 AM UTC daily and on `workflow_dispatch`
  - Runs `test_physics_behavior.py` (hand-calc validation) + all 3 example scripts
  - On failure: opens a GitHub issue with `regression` + `physics` labels and run URL

---

### PR11: Rack-level model

Added `analyze_rack()` — the highest-priority portfolio gap identified in
`docs/strategy.md`. A thermal engineer's real question is rack-scale, not
per-cold-plate.

**What was added:**
- `AnalyzeRackInput` and `AnalyzeRackOutput` schemas in `schemas.py`
- `analyze_rack()` function in `physics.py` (~65 lines)
- `analyze_rack` MCP tool in `mcp_server.py`
- Two hand-calc validation tests in `tests/test_physics_behavior.py`
- Section G in `docs/physics.md`

**Physics summary:**
- Series: each GPU's inlet = previous GPU's outlet. ΔP_total = N × ΔP_single.
  In series with constant-property fluid, Tj increases by exactly `coolant_rise`
  per GPU. Hottest GPU is always the last one.
- Parallel: all GPUs share CDU supply temperature. Flow splits equally.
  ΔP_total = ΔP_single (branch ΔP, not cumulative). CDU outlet from energy balance.
- Assumed: uniform flow distribution, no manifold/header losses, identical GPUs.
  These are documented in `docs/physics.md` Section G and as limitations.

---

## Queue: next tasks (prioritized)

### PR10 — MCP test completeness ✓ DONE (this session)

All items completed. 21 MCP tests + 34 total passing. Branch: `claude/mcp-tests-and-ci-ODSRh`.
Also added `.github/workflows/daily-regression.yml` (runs hand-calc + examples daily at 6 AM UTC).

### PR12 — Sensitivity / uncertainty output (medium, ~half day)

Results currently look falsely precise. R_jc has ±20% manufacturing variation;
TIM resistance doubles over 2–3 years. A real deployment engineer wants to know
the worst case, not just the nominal.

Options (pick one per discussion with Riccardo):

**Option A — Sensitivity coefficients (simpler)**
Add optional `sensitivity=True` param to `analyze()`. Returns additional dict:
```python
sensitivity: {
    "dtj_dq":      float,  # °C/W  — impact of heat load uncertainty
    "dtj_drtim":   float,  # °C/(K/W) — TIM aging impact
    "dtj_dtinlet": float,  # °C/°C — inlet temperature impact (≈1.0 by construction)
    "dtj_dflow":   float,  # °C/(L/min)
}
```
Computed via finite difference (±1% perturbation). Fast, no new dependencies.

**Option B — Monte Carlo (more impressive, heavier)**
Add `analyze_uncertainty(inp, n_samples=1000)` returning `(tj_mean, tj_p95, tj_p99)`.
Samples R_jc ~ N(mean, 20%), R_tim ~ LogNormal (ages), flow ~ N(nominal, 5%).
Needs numpy. Worth it if targeting senior thermal engineers or academic audience.

**Add `margin_c` to `optimize_flow_rate`:**
Target `max_junction_temp_c - margin_c` instead of bare limit. Default 3°C.
This makes optimization results deployable, not just theoretical.

### ROI calculator — separate repo decision (open)

See `docs/strategy.md` for full context.
- `analyze_rack` (this session) is the prerequisite.
- Financial layer belongs in a separate package (`thermal-roi-calculator`).
- Only start after PR10 and PR12 are merged and the physics story is complete.
- Key question: target user is engineer (CLI/Python) or business stakeholder (web)?
  Answer determines whether to build a CLI tool or a web app.

---

## Automations to set up (GitHub Actions)

These can be wired up in `.github/workflows/` as time permits.
All use the existing `claude.yml` / Claude Code GitHub Action pattern.

### 1. Daily physics regression canary (HIGH value)

```yaml
# .github/workflows/daily-regression.yml
on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC daily
```

Runs `pytest tests/test_physics_behavior.py -v`. Posts a comment to main branch
if the hand-calc tests drift (catches silent pydantic/fastmcp breaking changes).
Failure notification via GitHub email → you notice before a demo breaks.

### 2. PR benchmark diff (MEDIUM value)

On every PR opened against main:
- Run `python examples/real_chip_benchmarks.py`
- Post the output as a PR comment
- Shows what changed in real terms (H100 Tj, B200 flow requirement) not just test pass/fail
- Forces every PR author to answer "did my change affect an H100?"

Implementation: add a step to `ci.yml` that captures stdout and uses
`gh pr comment` to post it.

### 3. Weekly sensitivity report (LOW value, unblock after PR12)

After PR12 lands: on Monday morning, run sensitivity sweep for all four chips
(H100, B200, MI300X, Gaudi 3) and upload results as a workflow artifact. Lets you
watch how sensitivity landscape changes as geometry or defaults evolve.

### 4. Issue auto-answer for `physics-question` label (NICE TO HAVE)

Repurpose `claude-code-review.yml` pattern: when an issue is labeled
`physics-question`, Claude Code reads `docs/physics.md`, runs the relevant
`analyze()` call if parameters are given, and drafts a reply comment.
Useful for building a public-facing demo of the tool's conversational capability.

---

## Decisions and rationale log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-07 | CLAUDE.md updated: rack model done, gaps re-prioritized | Future agents see current state immediately |
| 2026-03-06 | Rack model before MCP tests (PR11 before PR10) | Highest portfolio impact; MCP tests are a quick follow-on |
| 2026-03-06 | Series/parallel as Literal, not Enum | Consistent with existing `CoolantName` pattern in codebase |
| 2026-03-06 | `per_gpu_junction_temps_c: list[float]` not full per-GPU results | Full results = N× data volume; Tj list is sufficient for rack-level decisions |
| 2026-03-06 | No manifold losses in rack model | Explicitly documented as a limitation; add properly or not at all (per CLAUDE.md) |
| 2026-03-06 | ROI calculator → separate repo | Different update cadence, different target user (CFO vs. engineer) |
| 2026-03-05 | Strategy doc written (docs/strategy.md) | Audit of portfolio gaps; highest-impact items ranked |

---

## Physics change protocol reminder

Before marking any physics change done:
1. Units consistent (resistance calcs in Kelvin, I/O in Celsius) ✓
2. Dimensional analysis passes ✓
3. Energy balance closes: `Q_input ≈ m_dot × cp × ΔT_coolant` ✓ (tested via CDU outlet check)
4. `docs/physics.md` updated ✓
5. Hand-calc test added ✓
6. `pytest` passes ✓

---

## Files to not touch without hand-calc update

- `tests/test_physics_behavior.py` — do not weaken tolerance on hand-calc tests
- `src/thermal_mcp_server/physics.py` constants (COOLANTS dict, efficiency = 0.50)
- Key defaults in `schemas.py` (channel geometry, contact_area, copper_k)

These are locked per `CLAUDE.md`. The canonical default case (700W, 8 LPM, water)
→ Tj ≈ 70.9°C appears in README and must remain correct.
