# Brief P2: correct the laminar constants on the existing rectangular path

Written 2026-11-17 by the orchestrator. Implementer: Opus 5.5. Checker: Haiku.
Branch: `feat/rectangular-laminar-constants` off `main` (after pull requests 55 and 56 are merged).
One pull request. Do not merge it.

Read first: `CLAUDE.md`, `docs/decisions.md` (2026-11-15 entry), `docs/work-plan.md` (piece P2),
`docs/physics.md` sections B, C, E and I, `docs/briefs/p1-straight-fin.md`.

## Goal

On the `full_wetted_area` path, replace the circular-tube laminar constants (Nu = 4.36, f·Re = 64)
with the Shah & London rectangular-duct forms already in `physics.py`
(`_nu_h1_rectangular`, `_f_re_darcy_rectangular`), evaluated at `α = min(w, h) / max(w, h)`.
Owner decision D2 approves this, including the change to published numbers.

Nothing else about the path changes: full wetted perimeter as heated area, no fin efficiency,
the 2300 to 4000 linear blend, Dittus-Boelter and Blasius above it. The H1 four-wall form is the
matching boundary condition for a path that heats the full perimeter.

## Scope

### Physics (`physics.py`)

- `full_wetted_area` branch: `f_re_lam = _f_re_darcy_rectangular(alpha)`,
  `nu, regime = _nusselt(re, pr, _nu_h1_rectangular(alpha))`.
- Remove the `4.36` and `64.0` defaults from `_nusselt` and `_friction_factor` (make the laminar
  value a required argument) so no caller can fall back to tube constants silently. Check every
  call site, including `_flow_quantities` users, sensitivity, rack and optimisation code.
- The `straight_fin` path must be numerically unchanged.

### Warnings

Do not change any warning text. The "rectangular-channel correlations and effective heated-area
assumption are unvalidated for this geometry" warning stays: the heated-area assumption is still
unvalidated. If you think wording should change, put it in the pull request as a question.

### Tests

- `test_hand_calc_validation_default_case` and any test with a literal that moves: update the
  expected values with independently derived numbers written as literals, and keep or tighten the
  tolerance. Never widen one. Rewrite the docstring hand calculations to show the new laminar end
  of the blend.
- `test_hand_calc_validation_700w_water` is fully turbulent (Re 4668) and must pass unedited.
- Add a new laminar hand-calc test on the default geometry at 4 LPM, 700 W, water (Re 1867), in
  the style of the existing ones, at 1e-6 relative.
- Add a test that a non-square channel uses its own aspect ratio (for example w = 0.5 mm,
  h = 2 mm, α = 0.25: laminar Nu within 0.5% of 5.331, Darcy f·Re within 0.5% of 72.932) and that
  swapping w and h gives the same Nu and f.
- Add continuity tests for Nu and f across Re = 2300 and Re = 4000 on this path.
- `tests/test_examples.py` and `tests/test_mcp_tools.py` literals that move are regenerated from
  the corrected model and listed in the pull request.

### Docs and quoted numbers

Every number quoted anywhere that changes must be regenerated from the code, not edited by hand
arithmetic. Known places (grep for others; `docs/fable-handoff.md`, `docs/work-plan.md` and
`docs/briefs/` are dated records and stay as written):

`README.md`, `CLAUDE.md` (key defaults paragraph and the "Does" list line on laminar Nu),
`docs/physics.md` (sections B, C, E; say what changed and why, cite Shah & London as in Section I),
`docs/model_overview.md`, `docs/representative-walkthrough.md`, `docs/mcp.md`,
`docs/milestone-1-contract.md` (example payload only), `docs/assumptions.md`,
`examples/interactive_sizing.ipynb` (re-execute; markdown cells that quote numbers too),
example scripts with hard-coded expectations.

### Figure

Extend `examples/make_figures.py` to write `docs/img/default_plate_tj_vs_flow.png`: junction
temperature against flow (0.5 to 12 LPM) for the default plate at 700 W, water, 25 °C, with the
old constants (dashed) and the corrected ones (solid), the laminar / transition / turbulent bands
shaded, and the 8 LPM default marked. A second panel shows pressure drop the same way. The "old"
curve is computed inside the script from the literal constants 4.36 and 64, not from a code path
kept alive in `physics.py`. Covered by `tests/test_examples.py` like the P1 figure.

## Gates

Tolerances are fixed and not loosened. If a gate fails, stop and report the numbers.

**G1. Expected movement.** Default geometry (square, α = 1, laminar Nu 3.610224, Darcy f·Re
56.9184 from the polynomials), 700 W, water, 25 °C, default `R_jc`, `R_tim`. Within 1e-6 relative:

| Flow (LPM) | Re | Regime | Tj before (°C) | Tj after (°C) | ΔP before (Pa) | ΔP after (Pa) |
|---|---|---|---|---|---|---|
| 8 (default) | 3734.082 | transitional | 70.902310 | 70.913238 | 16800.3473 | 16586.9374 |
| 4 | 1867.041 | laminar | 89.528404 | 93.869983 | 3797.3333 | 3377.1584 |
| 1 | 466.760 | laminar | 93.307685 | 97.649264 | 949.3333 | 844.2896 |

The `test_hand_calc_validation_700w_water` case (10 LPM, R_jc 0.1, R_tim 0.05): Tj 133.084551 °C
and ΔP 26503.0383 Pa, unchanged.

These were produced by the orchestrator by substituting the polynomial values into the current
code. If your implementation disagrees, stop and report; do not adjust either side to match.

**G2. Hand calculations** as described under Tests, literals derived from the definitions.

**G3. Straight-fin path unchanged:** all P1 tests pass unedited, including the 1e-6 `screen_1d`
reproduction and `test_hand_calc_validation_straight_fin_800w_water`.

**G4. Energy balance** closes within 1%.

**G5. No stale numbers.** A grep for the old values (`70.90231`, `16.80 kPa`, `16800`, `4.36`,
`64/Re`, `89.5`, `93.3`, and any other value your before/after table shows moved) finds only
dated records and the figure script's labelled legacy constants. List the grep output in the
pull request.

**G6. Before/after table** in the pull request: junction temperature, pressure drop, pump power
and minimum flow for an 83 °C limit, for the default case, 4 LPM, 1 LPM, and each row of
`examples/real_chip_benchmarks.py` at its current settings. Chip reference data is not edited.

**G7. Full quality gate:** `uv run pytest`, `ruff check .`, `ruff format --check .`, `mypy`,
`uv build`, notebook check in CI.

## Do not touch

- Geometry defaults, `COOLANTS`, chip reference data, temperature limits and targets in examples.
- The `straight_fin` equations and warnings. Decision-report statuses and semantics.
- Warning and notice wording. Package version, publishing, repo name.
- The transition blend and turbulent correlations. No new runtime dependency.
- The sibling repo `thermal-design-loop`: do not read, run or write anything there.

## Environment notes

Work in your own worktree. `uv` and git write commands need the sandbox disabled. Commit with
conventional messages ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
Never push to `main`, never force-push.

## Report back

In the pull request description, using the repo template: the G1 to G7 table with measured values;
both figures; the before/after table; every deviation from this brief and why; questions for the
owner. Then the checker re-derives the hand-calc literals from the equations alone and confirms
quoted numbers match generated output.
