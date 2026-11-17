# PROGRESS

## Resume here
The model fidelity track (`docs/work-plan.md`) is accepted; decisions D1 to D7 are recorded in
`docs/decisions.md`. Pull request 55 (branch `docs/fidelity-work-plan`) carries the plan, the decisions
and the first brief. Pull request 56 (branch `feat/straight-fin-geometry`) carries P1, the additive
straight-fin model; the existing model and its numbers are unchanged.
Next: (1) Riccardo merges pull requests 55 and 56; (2) write the P2 brief (correct the laminar
constants on the existing path, which moves the 70.9 °C headline) for owner approval before work starts.

## Open questions for Riccardo
- P4: flow per kW for the reference case (1.5 LPM/kW proposed). P3: cited source for glycol properties.

## Done
- 2026-11-16: Riccardo settled the four P1 questions on pull request 56: the two straight-fin
  warnings are accepted as written; Re ≥ 2300 on that path is computed with a warning, not rejected;
  decision-report applicability notices follow `channel_model`; MCP docstrings and `CLAUDE.md`
  describe the new geometry keys and matplotlib joins the dev group so the figure test runs in CI.
- 2026-11-15: P1 implemented on `feat/straight-fin-geometry` (pull request 56); gates G1 to G7 pass.
- 2026-11-15: Riccardo accepted the recommendations for D1 to D7. P1 brief written, with reference
  numbers generated from `thermal-design-loop` `screen_1d` at commit `189f017`.
- 2026-11-15: Reviewed `docs/fable-handoff.md` against the code. Its physics findings hold on `main`.
  It was written from a checkout 20 commits behind `main` and did not account for Milestone 1 or the
  product thesis; the work plan reconciles the two.
- 2026-11-15: Scratch calculations behind the work plan's "Evidence so far" table, then re-derived
  independently by a second model from the equations alone.

## Notes for a fresh session
- Read `CLAUDE.md`, `docs/decisions.md`, `docs/work-plan.md`, `docs/physics.md`, then this file.
- In Claude Code's sandbox, `uv` cannot open its cache and `git switch` cannot move `HEAD`; run those
  with the sandbox disabled, or use `.venv/bin/python` with `PYTHONPATH=src` for read-only runs.
- The straight-fin reference implementation is `tools/screen_1d.py` in the sibling repo
  `thermal-design-loop` (properties from CoolProp in `tools/fluids.py`).
- Work goes on named branches and merges by pull request; never push to `main`.
