# PROGRESS

## Resume here
Branch `docs/fidelity-work-plan` (off `main` at PR 54) holds a draft plan for the model fidelity track:
`docs/work-plan.md`. It is a proposal awaiting Riccardo's review; no physics, schema or default has changed.
Next: (1) Riccardo answers decisions D1 to D7 in the work plan; (2) record accepted ones in
`docs/decisions.md` and update "Current next steps" in `CLAUDE.md`; (3) write the brief for P1
(straight-fin geometry option) and hand it to the implementer.

## Open questions for Riccardo
See the "Owner decisions" table in `docs/work-plan.md`. D2 (moving the 70.9 °C headline), D3 (reference
case) and D4 (coolant property basis) are on this repo's ask-first list.

## Done
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
