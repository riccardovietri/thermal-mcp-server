# PROGRESS

## Resume here
P1 (pull request 56) and P2 (pull request 57) are merged. P4, the reference case and chip benchmark
rerun, is in review on `feat/reference-case-benchmarks` (brief `docs/briefs/p4-reference-case.md`):
`examples/reference_case.py`, the hero figure `docs/img/chip_reference_case.png` and
`docs/fidelity-results.md`. P3 (temperature-dependent coolants) is deferred by the owner until after
the demo, so P4 runs on fixed 25 °C properties and says so.
Next: (1) checker re-runs the P4 numbers against the results page; (2) Riccardo reviews and merges the
P4 pull request; (3) P5 or Milestone 2.

## Open questions for Riccardo
- P3: cited source for glycol properties (when P3 resumes).

## Done
- 2026-11-17: P4 implemented on `feat/reference-case-benchmarks`; owner set the reference flow to
  1.5 LPM/kW and the hero figure to a straight-fin reference plate beside the default plate.
- 2026-11-17: P1 and P2 merged as pull requests 56 and 57.
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
