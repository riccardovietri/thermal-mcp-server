# Brief P4: reference case and chip benchmark rerun

Written 2026-11-17 by the orchestrator. Implementer: Opus 5.5. Checker: Haiku.
Branch: `feat/reference-case-benchmarks` off `main` (P1 and P2 merged). One pull request. Do not merge it.

Read first: `CLAUDE.md`, `docs/decisions.md`, `docs/work-plan.md` (piece P4), `docs/physics.md`
sections E and I, `examples/real_chip_benchmarks.py`, `examples/make_figures.py`.

Owner decisions for this piece (2026-11-17): the reference flow is **1.5 LPM per kW**; the hero
figure uses a **straight-fin reference plate** with the default plate shown alongside. P3
(temperature-dependent coolants) is deferred, so this piece runs on today's fixed 25 °C properties
and says so.

## Goal

Show, for the four public chips, what the model predicts at a realistic flow per kW, on the
default plate and on a straight-fin plate, next to the legacy 8 LPM default. Produce the repo's
hero figure and a short results page. No physics, schema, default or chip-data change.

## Definitions

- **Chips:** `ALL_CHIPS` in `examples/real_chip_benchmarks.py`, unchanged (five rows; Gaudi 3 has
  an air and a liquid power level).
- **Conditions:** water, inlet 35 °C (the value the existing studies use), default `R_jc` and `R_tim`.
- **Three configurations per chip:**
  - A: default plate, 8 LPM (the repo's historical default operating point).
  - B: default plate, `1.5 × TDP_kW` LPM.
  - C: reference straight-fin plate, `1.5 × TDP_kW` LPM.
- **Reference straight-fin plate:** `channel_model="straight_fin"`, 76 channels, width 0.39 mm,
  fin thickness 0.39 mm, height 3.75 mm, length 60 mm, base 2 mm, copper 385 W/m·K,
  `contact_area_m2 = 76 × 0.78e-3 × 0.06 = 3.5568e-3`. Dimensions are the screened design from the
  companion `thermal-design-loop` study; cite it by name only. Do not read, run or write anything
  in that repo. Define the plate once as a named constant in the example code, not as a new
  default in `schemas.py`.
- **Minimum flow:** `optimize_flow` with `max_junction_temp_c` = the chip's limit, `margin_c = 0`,
  search range 0.2 to 30 LPM, on each plate.

## Scope

### Example (`examples/reference_case.py`, new)

Deterministic, no network, prints one table of the three configurations per chip (junction
temperature, margin to the chip's limit, pressure drop, pump power, Reynolds number, regime) and
one table of minimum flow per chip on each plate with the pressure drop at that flow, or "no
passing point in 0.2 to 30 LPM". It exposes a function returning the same data as plain
dictionaries so the figure script and tests do not parse text. `examples/real_chip_benchmarks.py`
and its output stay unchanged.

### Figure (`examples/make_figures.py` → `docs/img/chip_reference_case.png`)

Three panels, readable at README width, generated from the function above:

1. Junction temperature per chip for A, B and C (three markers on one row per chip, joined), with
   each chip's limit as a tick on its row.
2. Pressure drop per chip for A, B and C, log axis.
3. Resistance stack for the H100 row in A, B and C: `R_jc`, `R_tim`, base, convection, in mK/W.

Colour-blind-safe palette, direct labels where they fit, no chart junk. Covered by
`tests/test_examples.py` like the other figures.

### Results page (`docs/fidelity-results.md`, new) and links

Short and factual. Sections: what was wrong (tube constants, no fin efficiency) with the P1 and P2
figures; the reference case with the hero figure and both tables, generated numbers only; what did
not move and why; what is still unvalidated (transition blend, fixed 25 °C properties, generic
package resistances, no measured plate); next steps (P3, P5, Milestone 2). It must state these
findings in plain words if the numbers below hold:

- At 1.5 LPM/kW the default plate is on its laminar plateau and every chip is far over its limit.
- The straight-fin plate at the same flow recovers most of that at under 1.5 kPa, but no chip
  meets its limit at 35 °C inlet, because `R_jc + R_tim` = 60 mK/W is about 88% of the stack.
- The 1200 W rows cannot pass on any plate with the generic package resistances (72 K rise from
  the package alone), which says the generic resistances do not describe those parts, not that
  the parts cannot be cooled.
- The default plate reaches H100's limit at a lower flow than the straight-fin plate only by
  entering the unvalidated transition blend.

Also: `README.md` gets the hero figure and a link to the results page near the top, without
removing existing content; `docs/public_specs.md` notes the reference flow; `docs/work-plan.md`
and `PROGRESS.md` are updated (P1 and P2 merged as pull requests 56 and 57, P4 in review, P3
deferred by the owner until after the demo).

## Gates

Tolerances are fixed. If a gate fails, stop and report the numbers.

**G1. Expected values**, produced by the orchestrator on `main` at `092b622`. Match at the printed
precision (junction temperature 0.1 °C, pressure drop 0.01 kPa, Reynolds 1):

| Chip (limit) | A: Tj, ΔP, Re | B: Tj, ΔP, Re | C: Tj, ΔP, Re |
|---|---|---|---|
| H100 SXM (83) | 80.9, 16.59, 3734 | 107.4, 0.89, 490 | 87.3, 0.71, 125 |
| B200 NVL72 (75) | 113.7, 16.59, 3734 | 155.7, 1.52, 840 | 121.2, 1.22, 214 |
| MI300X (85) | 84.2, 16.59, 3734 | 112.2, 0.95, 525 | 90.7, 0.76, 134 |
| Gaudi 3 air (85) | 94.0, 16.59, 3734 | 126.7, 1.14, 630 | 100.9, 0.91, 160 |
| Gaudi 3 liquid (85) | 113.7, 16.59, 3734 | 155.7, 1.52, 840 | 121.2, 1.22, 214 |

Convection resistance: default plate 4.171 mK/W at 8 LPM and 36.067 mK/W laminar; reference plate
6.374 mK/W laminar. Minimum flow (LPM): H100 6.607 default, 9.772 reference; MI300X 7.331 default,
20.789 reference; B200 and both Gaudi 3 rows have no passing point on either plate.

**G2. Nothing existing moves.** `git diff main -- tests/` shows additions only; `src/` is
untouched; `examples/real_chip_benchmarks.py` output is byte-identical; chip data unchanged.

**G3. Tests.** `tests/test_examples.py` covers the new example (key values from G1 as literals)
and the figure (file written, deterministic across two runs).

**G4. Every number on the results page and in the README addition** comes from generated output.
The checker confirms this against a fresh run.

**G5. Full quality gate:** `uv run pytest`, `ruff check .`, `ruff format --check .`, `mypy`,
`uv build`, notebook check.

## Do not touch

`src/`, geometry defaults, `COOLANTS`, chip reference data and limits, existing tests and example
outputs, warning and notice wording, package version, the sibling repo. No new dependency.

## Environment notes

`uv` and git write commands need the sandbox disabled. Conventional commits ending
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never push to `main`, never force-push.

## Report back

Final report under 500 words: commits; G1 to G5 with measured values; both generated tables;
deviations and why; questions for the owner; anything not verified. Do not open the pull request.
