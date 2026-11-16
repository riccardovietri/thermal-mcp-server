# PROGRESS

## Resume here
The model fidelity track (`docs/work-plan.md`) is accepted; decisions D1 to D7 are recorded in
`docs/decisions.md`. Pull request 55 (branch `docs/fidelity-work-plan`) carries the plan, the decisions
and the first brief. No physics, schema or default has changed yet.
Next: (1) merge pull request 55; (2) hand `docs/briefs/p1-straight-fin.md` to the implementer on
`feat/straight-fin-geometry`; (3) checker pass, orchestrator review, then Riccardo.

## Open questions for Riccardo
- P1: the brief computes Re ≥ 2300 on the straight-fin path with the existing blend and turbulent
  closures plus a warning, instead of rejecting the input. Accept, or reject non-laminar inputs?
- P1: wording of the two straight-fin warnings that replace the "rectangular-channel correlations
  are unvalidated" notice on that path.
- P4: flow per kW for the reference case (1.5 LPM/kW proposed). P3: cited source for glycol properties.

## Done
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
