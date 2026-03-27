# Agent Notes — thermal-mcp-server

Living document for AI coding agents. Updated each session. Summarizes work done,
decisions made, and queued tasks so future agents can orient quickly.

*Last updated: 2026-03-23*

---

## Current branch

`claude/review-project-strategy-ODSRh` — strategy session, README update, interactive notebook

---

## Status

**Merged to main:**
- PR13: Rack-level model (`analyze_rack`, series + parallel, hand-calc validated)
- PR14: MCP test completeness (34 tests) + daily regression CI

**Open branches (all pushed, ready for PR creation):**

| Branch | Content | Merge order |
|--------|---------|-------------|
| `claude/fix-regression-workflow-ODSRh` | Workflow fixes + auto-review-response + AGENTS.md self-verification | 1st |
| `claude/portfolio-examples-ODSRh` | 3 example scripts + README rack-demo lead | 2nd |
| `claude/sensitivity-and-margin-ODSRh` | Sensitivity output + `margin_c` for `optimize_flow_rate` | 3rd |

**This session (2026-03-23):**
- Strategy review: project is portfolio-presentable now; bottleneck is visibility, not features
- Updated README to lead with NVL72 rack demo (also done in portfolio-examples branch)
- Added `analyze_rack` to Tools section; updated Scope with known limitations
- Created `examples/interactive_sizing.ipynb` — 6-section Colab-ready notebook
- Identified personal site + notebook as highest ROI next steps

Repo memory now has a cross-agent structure:
- `AGENTS.md` added as the tool-neutral entrypoint
- `docs/decisions.md` added for durable architectural/modeling decisions
- `docs/local-agent-bootstrap.md` added with a reusable prompt for local agent setup

Interactive demo scaffold is now part of the repo plan:
- `examples/interactive_rack_demo.ipynb` is the notebook surface
- `examples/demo_helpers.py` is the stable presentation/adapter layer
- future demo features should plug into helper extension seams rather than pushing logic into notebook cells

---

## Work completed (this session)

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

### 1. Merge open branches (ready now, in order)

```
claude/fix-regression-workflow-ODSRh  →  PR first
claude/portfolio-examples-ODSRh       →  PR second
claude/sensitivity-and-margin-ODSRh   →  PR third
```

All branches are pushed. No GITHUB_TOKEN available in current env — create PRs from browser:
- https://github.com/riccardovietri/thermal-mcp-server/pull/new/claude/fix-regression-workflow-ODSRh
- https://github.com/riccardovietri/thermal-mcp-server/pull/new/claude/portfolio-examples-ODSRh
- https://github.com/riccardovietri/thermal-mcp-server/pull/new/claude/sensitivity-and-margin-ODSRh

### 2. Personal site (highest visibility ROI, ~1–2 weeks)

Goal: make the project discoverable and give visitors a way to experience it.

**Tech choice (recommended):** Astro + Tailwind, deployed on Netlify or Vercel.
- One-page structure: bio / featured project / contact
- Featured project: this tool, framed as a case study (problem → physics → tool → outcome)
- Link to `examples/interactive_sizing.ipynb` as the interactive demo ("Open in Colab")

**The narrative that works:**
> "Liquid cooling is mandatory at B200 scale. I built an AI-native tool that lets engineers
> and AI agents size CDUs from first principles — from single cold plate hydraulics to
> full NVL72 rack specs. It works via Claude's MCP protocol."

### 3. Interactive notebook polishing (unblocks after PRs merge)

`examples/interactive_sizing.ipynb` is created and has the core sections. After portfolio-examples
and sensitivity branches merge:
- Add sensitivity section using the actual `sensitivity=True` param from PR12
- Test full notebook run end-to-end in Colab (verify imports, output cells render)
- Add "Open in Colab" badge to README once it's on main

### 4. PR12 — Sensitivity / uncertainty output (ready to merge, in sensitivity branch)

Already implemented on `claude/sensitivity-and-margin-ODSRh`:
- `sensitivity=True` param for `analyze()` → finite-difference coefficients
- `margin_c` param for `optimize_flow_rate` (default 3°C)

### 5. ROI calculator — separate repo (after PRs 1–4 merged)

See `docs/strategy.md` for full spec. Target user: VP of Infrastructure or CTO making a
"should we buy the CDU?" decision.
- Inputs: gpu_count, rack_count, electricity_$/kWh, baseline_PUE, liquid_PUE, CDU capex
- Outputs: annual savings, payback months, NPV, per-GPU cooling tax
- Separate repo (`thermal-roi-calculator`), depends on this package as a library

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
