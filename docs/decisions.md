# Decisions — thermal-mcp-server

Durable project decisions that should survive across branches and sessions.
Use this file for choices that future agents and contributors should not need to
re-derive from old PRs or chat logs.

## 2026-11-18 — Package resistance shown as a die-area band, in the examples only

After the package resistance review (`docs/research/package-resistance-review.md`),
the owner decided (brief `docs/briefs/p4b-package-band.md`):

1. Show estimated package resistance as a band, not a point, for the chips whose
   die area is known (H100, and the Blackwell GPU with an order-of-magnitude
   footprint). Keep the generic 60 mK/W (`R_jc` 0.04 + `R_tim` 0.02 K/W) as a
   labelled conservative case.
2. Do it in the examples only. `src/`, the schema, defaults and the `R_jc` /
   `R_tim` defaults are untouched. Area-specific schema fields (`die_area_m2` and
   area-specific `R_jc` / `R_tim`) remain a deferred option, described in the review.
3. MI300X and Gaudi 3 stay on the generic values, labelled "die area not published".
4. Relabel chip sources; keep every limit and TDP value. The 1200 W row becomes
   "Blackwell GPU (GB200 NVL72)", cited to the NVIDIA Blackwell datasheet; 75 °C
   is a design target whose source could not be traced; H100 83 °C is a
   conservative design value, not vendor-published for SXM.
5. Flag the Gaudi 3 liquid-cooled power conflict (Hot Chips 2024: 1200 W; Intel's
   2025 technical paper: 900 W).

Rationale:

- The package term dominates the reference case, no vendor publishes it, and a
  single invented value would hide that; a band with its basis is auditable.

## 2026-11-15 — Model fidelity track runs between Milestone 1 and Milestone 2

The owner accepted the recommendations for decisions D1 to D7 in
[the work plan](work-plan.md). Milestone 1 is accepted as merged.

- Add a straight-fin geometry option (Shah & London laminar Nu and f·Re by aspect
  ratio, adiabatic-tip fin efficiency) without changing the existing geometry,
  defaults or outputs. Nu uses the H1 boundary condition with an adiabatic cover,
  the form checked against conjugate CFD in `thermal-design-loop`.
- Then correct the circular-tube laminar constants on the existing rectangular
  path as its own pull request. This moves the 70.9 °C default headline; the
  hand-calculation tests are updated with independently derived values, not loosened.
- Add temperature-dependent coolant properties, including 25% propylene glycol,
  as fitted tables checked against CoolProp in tests. CoolProp is not a runtime
  dependency.
- Add a reference case at a realistic flow per kW alongside the current default,
  which stays for continuity, and rerun the public chip benchmarks.
- Compare with a measured plate after the benchmark rerun.

Still owner calls, to be settled in the brief for the piece concerned: the flow
per kW of the reference case, the cited source for glycol properties, and the
wording of any applicability warning that is narrowed or removed.

## 2026-09-10 — Milestone 1 uses an explicit v2 screening-report contract

The owner approved implementing one milestone at a time and the breaking report
format described in [the Milestone 1 contract](milestone-1-contract.md).

- Preserve fixed-flow inputs; distinguish point failure, search failure, and
  unavailable evaluation. Never substitute single-plate results for a rack.
- Replace heuristic operating recommendations and risk levels with evaluated
  points, search scope, signed stress scenarios, and input provenance.
- Keep system hydraulic feasibility and overall risk unassessed until the model
  and evidence support them. Equation verification is not hardware validation.
- Preserve numerical equations, physical defaults, and standalone analysis APIs
  in this milestone. MCP exposes the same report as Python.
- Owner review and merge approval precede Milestone 2. This decision does not
  authorize adding hydraulic models, publishing a release, or renaming the project.

The report-schema version is distinct from the package release version. External
report consumers need the migration in [MCP contracts](mcp.md); do not publish the
breaking contract as an undocumented patch.

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
is only a discovery shim for tools that look for `AGENTS.md`; it should point
to `CLAUDE.md` rather than duplicate project rules.

Rationale:

- One authoritative file is better than two that mostly agree.
- Codex and other agents that read `CLAUDE.md` get the full context.
- Keeping `AGENTS.md` minimal avoids instruction drift while preserving Codex
  discovery behavior.

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
