# Agent Notes — thermal-mcp-server

Living document for AI coding agents. Updated as major repo state changes land.
Use this file for current status and short-horizon next steps, not for durable
decisions that should outlive the branch.

*Last updated: 2026-04-08*

---

## Current state

Main now includes the core portfolio milestones and release workflow fixes:

| PR | Content |
|----|---------|
| PR13 | Rack-level model (`analyze_rack`, series + parallel, hand-calc validated) |
| PR14 | MCP tool test expansion + daily regression CI |
| PR15 | Sensitivity output + `margin_c` for `optimize_flow_rate` |
| PR17 | Portfolio examples (`real_chip_benchmarks.py`, rack tradeoffs, AI factory budget) |
| PR19 / PR20 | Workflow and review-response hardening |
| PR23 / PR24 | PyPI publish workflow fixed (`uv build`, API-token publish path) |

Current published package version: `0.3.0`.

Repo status at this update:
- Public README leads with NVL72/B200 rack sizing and H100 baseline validation
- `examples/interactive_sizing.ipynb` is the Colab-facing demo surface
- Test suite has 44 passing tests across physics behavior and MCP wrappers
- `uv build` succeeds for sdist and wheel

---

## Immediate next steps

### 1. PR benchmark diff in CI

Highest-signal repo improvement still missing.

Goal:
- Run `examples/real_chip_benchmarks.py` on pull requests
- Surface output in CI logs or a PR comment so reviewers can see whether a
  change moved real chip-level results

Why it matters:
- Makes physics regressions legible in reviewer language, not just unit-test language
- Creates a lightweight release note for every PR touching model behavior

### 2. Interactive demo polish

Keep the notebook path polished and externally usable.

Checklist:
- Verify `examples/interactive_sizing.ipynb` runs end-to-end in Colab
- Make sensitivity outputs visible in the notebook flow
- Keep README and notebook screenshots aligned with current outputs

### 3. Personal site / case-study packaging

Highest ROI outside the repo itself.

Narrative:
> Liquid cooling is mandatory at B200 scale. This repo shows an AI-callable,
> first-principles thermal model that sizes CDUs from single cold plates up to
> rack-level specs.

Suggested packaging:
- one-page project case study
- links to PyPI, GitHub, and Colab demo
- one short validation section with H100 default case and B200 rack example

### 4. Keep rack-scope discipline

Do not casually expand rack claims beyond current model scope.

Still excluded:
- manifold/header losses
- heterogeneous racks
- temperature-dependent fluid properties
- flow maldistribution

Any expansion here should be deliberate, documented in `docs/physics.md`, and
backed by hand-calc or analytical tests.

---

## Review lessons worth reusing

Recent merged PRs surfaced recurring engineering lessons:

1. Workflow failure-mode engineering matters.
   Add file-existence guards, dependency bootstrap, null-event handling, and
   deterministic failure messages to every GitHub Actions workflow.

2. Permissions and secret contracts should be explicit per workflow trigger.
   Review `pull_request`, `pull_request_review`, and comment-triggered workflows
   for least-privilege permissions and clearly named required secrets.

3. Signature changes need compatibility checks.
   For public Python APIs and MCP wrappers, check positional-call safety and
   wrapper parity before merging argument-order changes.

4. MCP tools should preserve one error envelope.
   Nested validation failures should return the same `{"error": [...]}` shape as
   top-level validation failures.

5. New physics features should get analytical or hand-calc tests.
   Every model extension should land with both docs and an independently
   explainable validation path.

---

## Physics change protocol

Before marking any physics change done:
1. Units consistent (resistance calcs in Kelvin, I/O in Celsius)
2. Dimensional analysis passes
3. Energy balance closes: `Q_input ≈ m_dot × cp × ΔT_coolant`
4. `docs/physics.md` updated with justification
5. Hand-calc or analytical validation added in `tests/test_physics_behavior.py`
6. `uv run pytest -v` passes with no tolerance relaxation

---

## Files locked against casual change

- `tests/test_physics_behavior.py` — do not weaken numerical tolerances
- `src/thermal_mcp_server/physics.py` constants (COOLANTS dict, pump efficiency = 0.50)
- Key defaults in `schemas.py` (channel geometry, contact_area, copper_k)

Canonical default:
- 700 W
- 8 LPM
- water
- 25°C inlet
- `Tj ≈ 70.9°C`

This baseline appears in the README and is checked in
`test_hand_calc_validation_default_case`.
