# Decisions — thermal-mcp-server

Durable project decisions that should survive across branches and sessions.
Use this file for choices that future agents and contributors should not need to
re-derive from old PRs or chat logs.

## 2026-03-07 — Cross-agent memory is repo-first

Project memory is split by scope:

- Repo memory is the canonical shared layer: `CLAUDE.md` and this file.
- Local machine memory is for user-specific preferences and cross-project
  habits, not as the source of truth for this repo.

Rationale:

- Remote/cloud agents cannot be assumed to have access to local home-directory
  state.
- Repo memory is reviewable, portable, and available to all agents working on
  the project.

## 2026-04-08 — `CLAUDE.md` is the single agent instruction file

`CLAUDE.md` serves all coding agents (Claude Code, Codex, etc.). `AGENTS.md`
was removed — maintaining two overlapping instruction files caused drift.

Rationale:

- One authoritative file is better than two that mostly agree.
- Codex and other agents that read `CLAUDE.md` get the full context.

## 2026-03-06 — Rack model excludes manifold/header losses

Rack analysis supports only identical GPUs in series or parallel using cold
plate pressure drop. No manifold/header loss model is included.

Rationale:

- This keeps the model honest and interpretable.
- Manifold losses should be modeled explicitly rather than approximated with
  undocumented fudge factors.

Implication:

- Do not claim rack-level hydraulic results are full-system predictions when
  manifold losses are material.

## 2026-03-06 — Hand-calculation validation is mandatory for physics-default changes

If default geometry, coolant constants, or correlation behavior changes, update
the relevant hand-calculation validation in `tests/test_physics_behavior.py`.

Rationale:

- This repo is credibility-sensitive. Numerical drift without an explicit
  independent validation path is unacceptable.

## 2026-03-06 — Thin MCP layer, physics stays in Python API

`mcp_server.py` should remain a validation and transport wrapper, not a second
implementation of the model.

Rationale:

- Prevents duplicated physics logic.
- Keeps MCP behavior aligned with the Python API and tests.

## 2026-03-27 — ROI financial layer is a separate repo

If a cooling-cost / ROI calculator is built, it should live in a separate
package (`thermal-roi-calculator`) or a web app that imports
`thermal_mcp_server.physics` as a dependency, not in this repo.

Rationale:

- ROI inputs such as electricity cost and CDU vendor pricing change on a
  different cadence than the physics model.
- Keeping the financial layer separate preserves narrow scope and fast tests in
  this repo.
- Deployment, cost-data refresh, and business-facing assumptions do not belong
  in the core physics package.
