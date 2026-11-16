# Brief P1: straight-fin geometry option

Written 2026-11-15 by the orchestrator. Implementer: Opus 5.5. Checker: Haiku.
Branch: `feat/straight-fin-geometry` off `main`. One pull request. Do not merge it.

Read first: `CLAUDE.md`, `docs/decisions.md`, `docs/work-plan.md` (piece P1), `docs/physics.md`
sections B, C and E, `docs/milestone-1-contract.md` ("Evidence and scenario semantics").

## Goal

Add a second channel model to the cold-plate analysis: straight rectangular fins in fully developed
laminar flow, with Shah & London Nu and f·Re as functions of aspect ratio and adiabatic-tip fin
efficiency. The existing model, its defaults and every number it produces today stay unchanged.

The reference implementation is `tools/screen_1d.py` in the sibling repo `thermal-design-loop`
(commit `189f017`), which agrees with conjugate CFD to 1.0% on average for thermal resistance.
Port the physics; do not import that repo or add CoolProp.

## Scope

### Schema (`schemas.py`), additive only

On `Geometry`:

- `channel_model: Literal["full_wetted_area", "straight_fin"] = "full_wetted_area"`.
  `"full_wetted_area"` is today's behaviour under a name.
- `fin_thickness_m: float | None = None`, `gt=0` when given.
- Validation: `straight_fin` requires `fin_thickness_m`; `fin_thickness_m` supplied with
  `full_wetted_area` is rejected, not ignored.

On `AnalyzeColdplateOutput`: `fin_efficiency: float | None = None`, populated only for `straight_fin`.

Fins use `copper_k_w_mk`. No other new fields.

### Physics (`physics.py`), `straight_fin` path only

With `w` channel width, `H` channel height, `t` fin thickness, `N` channel count, `L` length:

- `α = min(w, H) / max(w, H)`
- `Nu_lam(α) = 8.235 (1 − 2.0421α + 3.0853α² − 2.4765α³ + 1.0578α⁴ − 0.1861α⁵)`
- `(f·Re)_Darcy(α) = 96 (1 − 1.3553α + 1.9467α² − 1.7012α³ + 0.9564α⁴ − 0.2537α⁵)`
- `h = Nu · k_f / Dh`; `m = sqrt(2h / (k_s · t))`; `η = tanh(mH) / (mH)`
- `R_conv = 1 / (N · L · h · (w + 2ηH))`: channel floor at `η = 1`, two fin sides at `η`, cover adiabatic
- `ΔP = f · (L / Dh) · (ρv² / 2)`, the existing Darcy-Weisbach form
- `Dh`, `Re`, `R_base` (from `contact_area_m2`), coolant rise, `Tj` and pump power are unchanged

Regime handling. `Re < 2300`: the laminar forms above. `Re ≥ 2300`: keep the existing transition
blend and turbulent closures (Dittus-Boelter, Blasius), with the laminar end of the blend taken
from the forms above and `η` computed from the resulting `h`. That range is outside what was
checked against CFD, so it must carry the warning below. Do not invent a different turbulent model.

### Warnings (`straight_fin` path)

Keep every existing warning except the one beginning "rectangular-channel correlations and
effective heated-area assumption are unvalidated", which this path replaces with:

- always: `"straight-fin model assumes fully developed laminar flow with an adiabatic cover; entrance effects, fin-tip heat transfer and flow maldistribution are not modeled"`
- when `Re ≥ 2300`: `"straight-fin correlations were checked for laminar flow only; this operating point is outside that range"`

The "no measured cold-plate validation" warning stays on both paths. Warning wording is an owner
call in this repo: implement the text above, list it in the pull request, and change nothing else
about warnings. The `full_wetted_area` path's warnings are untouched.

### Docs

- `docs/physics.md`: a new section for the straight-fin model with equations, the boundary-condition
  choice (H1, adiabatic cover), the validity range and what it still omits. Section E gains one line
  pointing to it.
- `docs/assumptions.md`, `docs/mcp.md`, and the `Geometry` docstring: the new fields.
- Cite Shah & London (1978) for the polynomials and the table. If you cannot read the source in
  full text, say so in the pull request and cite what you did read; do not assert constants from memory.

### Figure

`examples/make_figures.py` (matplotlib is already a dev dependency) writes
`docs/img/straight_fin_correlations.png`: Nu and f·Re against aspect ratio, model curve with the four
table points marked, and the legacy constants (4.36 and 64) as flat reference lines. Deterministic,
no network, covered by `tests/test_examples.py` in the same way as the other examples.

## Gates

Tolerances are fixed here and are not loosened. If a gate fails, stop and report the numbers.

**G1. Shah & London table.** At each aspect ratio, within 0.5% relative:

| α | (f·Re) Fanning | (f·Re) Darcy | Nu (H1) |
|---|---|---|---|
| 1.0 | 14.227 | 56.908 | 3.608 |
| 0.5 | 15.548 | 62.192 | 4.123 |
| 0.25 | 18.233 | 72.932 | 5.331 |
| 0.125 | 20.585 | 82.340 | 6.490 |

**G2. Reproduce `screen_1d`.** Geometry: `N = 76`, `w = t = 0.39 mm`, `H = 3.75 mm`, `L = 60 mm`,
base 2 mm, `copper_k_w_mk = 385`, `contact_area_m2 = N × (w + t) × L = 76 × 0.78e-3 × 0.06 = 3.5568e-3`
(the area `screen_1d` uses for base conduction). Operating
point: 1000 W, 1.5 LPM, inlet 25 °C, default `R_jc` and `R_tim`. Within 1e-6 relative:

| Quantity | water | glycol50 |
|---|---|---|
| Reynolds | 178.016895 | 35.093016 |
| Nusselt | 6.738931 | 6.738931 |
| Fin efficiency | 0.749545 | 0.814606 |
| Pressure drop (Pa) | 1014.389176 | 5470.862974 |
| R_conv (K/W) | 0.00637425442 | 0.00884355568 |
| R_base (K/W) | 0.00146052778 | 0.00146052778 |
| Coolant rise (°C) | 9.598173 | 11.098779 |
| Tj (°C) | 97.633868 | 100.853473 |

These come from running `analyze_1d` at commit `189f017` with this repo's coolant constants.

**G3. Hand calculation.** A new test in `tests/test_physics_behavior.py`, in the style of
`test_hand_calc_validation_700w_water`, on a geometry different from G2. It derives every
intermediate value from the definitions, with expected numbers written as literals, not computed by
calling the functions under test. Tolerances: under 1 °C on Tj and under 5 on Re are the repo
maximum; aim for 1e-6 relative.

**G4. Behaviour.** `0 < η ≤ 1`; `η` falls as fins get taller and rises with fin conductivity;
`R_conv` under `straight_fin` approaches `1 / (N L h (w + 2H))` as conductivity grows large;
`ΔP` does not depend on fin thickness at fixed `N`; `Nu` and `f·Re` are symmetric under swapping
`w` and `H`; both validation errors fire. G2 and G3 are laminar, so also cover the other branch:
`Nu` and `f` are continuous across `Re = 2300` and `Re = 4000` on the `straight_fin` path, and the
out-of-range warning appears at `Re ≥ 2300` and not below.

**G5. Nothing existing moves.** `git diff main -- tests/` shows additions only. Both existing
hand-calc tests pass unedited. Default `analyze()` output is identical apart from the new
`fin_efficiency: None` field.

**G6. Energy balance** closes within 1% on the `straight_fin` path.

**G7. Contracts.** `tests/test_mcp_tools.py`: the new fields pass through the `geometry` dict on
every tool that takes one, and the validation errors surface as tool errors. Decision-report input
provenance lists `geometry.channel_model` and `geometry.fin_thickness_m` with the correct
supplied or defaulted origin through both Python and MCP.

**G8. Full quality gate:** `uv run pytest`, `ruff check .`, `ruff format --check .`, `mypy`,
`uv build`, and the notebook check in CI.

## Do not touch

- Geometry defaults, `COOLANTS`, chip reference data, temperature limits.
- The `full_wetted_area` equations, constants and warnings. Correcting them is piece P2.
- Existing tests, other than adding new ones. README headline numbers.
- Decision-report statuses and semantics. Package version, publishing, repo name.
- No new runtime dependency. No footprint or manufacturability validation of the fin geometry;
  if you think one is needed, say so in the report.

## Report back

In the pull request description, using the repo template:

1. A table of G1 to G8 with the measured values and pass or fail.
2. The figure.
3. Every deviation from this brief and why.
4. Questions for the owner, including the warning wording.

Then the checker re-derives the G3 literals from the equations alone and confirms that numbers
quoted in the docs match generated output. The orchestrator reviews the pull request and figure
before anything goes to Riccardo.
