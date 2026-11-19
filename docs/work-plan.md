# Work plan: model fidelity track

Status: **accepted 2026-11-15**. Riccardo accepted the recommendation for each of D1 to D7 in the
"Owner decisions" table; the durable record is in `docs/decisions.md`. Briefs live in `docs/briefs/`.

Progress (2026-11-18): P1 merged (pull request 56), P2 merged (pull request 57), P4 merged (pull
request 58), P4b (package band) in review on `docs/case-study-page` (pull request 59), P3 deferred by
the owner until after the demo, P5 not started. Area-specific package fields in the schema are a
deferred option (described in `docs/research/package-resistance-review.md` section 3.3).

Sources: `docs/fable-handoff.md` (findings from `thermal-design-loop`), `docs/product-thesis-review.md`
(Milestones 1 to 3), `docs/milestone-1-contract.md`.

## Why this track, and where it sits

Milestone 1 made every result say what is unvalidated. `analyze()` now warns on each call that
"rectangular-channel correlations and effective heated-area assumption are unvalidated" and that
coolant properties are fixed at 25 °C. The product thesis lists both under "matters now". This track
removes the cause of those two warnings with sourced physics, then shows what moved, before
Milestone 2 (constrained rack sizing) builds on the numbers.

Order: Milestone 1 (merged, PR 54) → **this track** → Milestone 2 → Milestone 3.

## Evidence so far

Scratch calculations on 2026-11-15, independently re-derived the same day (see `PROGRESS.md`).
They motivate the plan; none is a repo result yet.

| Observation | Numbers |
|---|---|
| Laminar constants are circular-tube values | `physics.py` uses Nu = 4.36, f·Re = 64 at every aspect ratio. Shah & London for rectangular ducts: Nu 3.61 and f·Re 56.9 for a square channel, Nu 6.79 and f·Re 84.7 at aspect ratio 0.1 |
| No fin efficiency | Full wetted area is treated as base temperature. For 0.39 mm copper fins 3.75 mm tall in water the efficiency is about 0.75 |
| The two errors partly cancel | Design-loop pick (76 channels, 0.39 / 0.39 / 3.75 mm, 60 mm long, 1.5 LPM water): convective resistance 7.15 → 6.37 mK/W (−11%), pressure drop 0.77 → 1.01 kPa (+32%) |
| The default headline depends on a high flow | Default plate at 700 W: 70.9 °C at 8 LPM (Re 3,734, inside the 2,300 to 4,000 blend), 89.5 °C at 4 LPM, 93.3 °C at 1 LPM. 8 LPM is about 11 LPM/kW; loops are commonly sized near 1.5 LPM/kW |
| Package resistance dominates the default case | R_jc + R_tim = 60.0 of 64.7 mK/W (93%). Expect the benchmark rerun to move pressure drop and required flow more than junction temperature |

## Pieces of work

One pull request per piece, from a named branch, merged only with CI green and owner approval
where the table says so. Each piece ships its own figure (see "Figures").

### P1. Straight-fin geometry option (additive)

Status: merged (pull request 56).

- **Scope:** a geometry option with fin thickness, Shah & London laminar Nu (H1) and f·Re as functions
  of aspect ratio, adiabatic-tip fin efficiency. Ported from `thermal-design-loop/tools/screen_1d.py`.
  Existing geometry, defaults and outputs stay byte-for-byte unchanged.
- **Files:** `schemas.py`, `physics.py`, `docs/physics.md` (new section), `docs/assumptions.md`,
  `tests/test_physics_behavior.py`, `tests/test_mcp_tools.py`.
- **Gates:**
  1. Nu and f·Re reproduce the Shah & London tabulated values at the tabulated aspect ratios, tolerance
     fixed in the brief from the source before implementation.
  2. Reproduces `screen_1d` for the 0.39 / 0.39 / 3.75 mm design at identical fluid properties to within rounding.
  3. New hand-calculation test deriving every intermediate value independently.
  4. Energy balance closes within 1%; all existing tests pass untouched, including both hand-calc tests.
- **Owner approval:** schema addition (additive, not breaking) and decision D5.

### P2. Correct the laminar constants on the existing rectangular path

Status: merged (pull request 57).

- **Scope:** replace 4.36 and 64/Re with the aspect-ratio forms for the existing geometry. This changes
  the laminar end of the transition blend, so the 70.9 °C headline moves.
- **Files:** `physics.py`, `docs/physics.md`, `README.md`, `CLAUDE.md` (key defaults), both hand-calc tests
  with new independently derived expected values.
- **Gates:** hand-calc tests updated, not loosened; every number quoted in README and docs regenerated;
  before/after table in the pull request.
- **Owner approval:** required before work starts (D2). Blocked on P1.

### P3. Temperature-dependent coolant properties, including 25% propylene glycol

Status: deferred by the owner until after the demo (2026-11-17).

- **Scope:** ρ, cp, k, μ as functions of temperature for water, 50% ethylene glycol and 25% propylene
  glycol over a stated range; properties evaluated at mean coolant temperature; out-of-range inputs rejected
  or flagged, never extrapolated silently.
- **Files:** `physics.py`, `schemas.py` (`CoolantName`), `docs/physics.md`, `docs/assumptions.md`, tests.
- **Gates:** every property within a stated tolerance of its cited source across the range; at 25 °C the
  water and glycol50 values either reproduce today's constants or the difference is documented and the
  hand-calc tests updated; the fixed-property warning is removed only for the covered range.
- **Owner approval:** required (D4). Coolant values are on the ask-first list in `CLAUDE.md`.

### P4. Reference case and benchmark rerun

Status: merged (pull request 58; brief `docs/briefs/p4-reference-case.md`). Follow-up P4b (brief
`docs/briefs/p4b-package-band.md`) adds a package band estimated from die area for H100 and the
Blackwell GPU in configuration C, in the examples only, and relabels chip sources; limit and TDP
values unchanged. Run on P1 and P2 only, with fixed
25 °C properties, because P3 is deferred. The reference flow is 1.5 LPM/kW and the reference plate is
the straight-fin design; results in `docs/fidelity-results.md` from the new
`examples/reference_case.py`, with `examples/real_chip_benchmarks.py` left unchanged.

- **Scope:** add a reference operating point at a realistic flow per kW next to the current default,
  then rerun H100, B200 / GB200 NVL72, MI300X and Gaudi 3 with P1 to P3 and report what moved.
- **Files:** `examples/real_chip_benchmarks.py`, `docs/public_specs.md`, `README.md`, a short results page.
- **Gates:** every chip has a before and after row for junction temperature, pressure drop and minimum
  flow; chip reference data unchanged; the write-up states what did not move and why.
- **Owner approval:** required (D3). Blocked on P1 and P3.

### P5. Comparison with a measured plate

- **Scope:** compare the P1 model with the skived plate in Ortega et al. (ASME InterPACK 2022), read in
  full text, with every number tagged as text, figure or inferred. Acceptable error declared before the
  comparison is run.
- **Gates:** residuals reported as found; if the comparison needs an assumed dimension, the result is
  labelled indicative and the "no measured validation" notice stays.
- **Owner approval:** required (D6). This is the first step of thesis Milestone 3 and can wait until
  after Milestone 2 if preferred.

## Figures

The repo has no images today. Each piece adds one figure, generated by a deterministic script
(`examples/make_figures.py`, smoke-tested in CI) so a figure can never drift from the code.

| Piece | Figure |
|---|---|
| P1 | Nu and f·Re against aspect ratio (model against the Shah & London table); parity plot against `screen_1d` |
| P2 | Junction temperature against flow for the default plate, before and after |
| P3 | Viscosity against temperature for the three coolants, with source points |
| P4 | Before → after dumbbell per chip (junction temperature, pressure drop, minimum flow); resistance stack per chip. Candidate README hero figure |
| P5 | Predicted against measured thermal resistance and pressure drop |

After P4, a single case-study page (GitHub Pages, as in `thermal-design-loop`) is worth considering;
it is not in scope until the results exist.

## Owner decisions

All seven recommendations were accepted on 2026-11-15. Three details stay open and are settled in
the brief for their piece: the flow per kW of the reference case (D3), the cited glycol property
source (D4), and the wording of any narrowed applicability warning (P1, P2).

| ID | Decision | Blocks | Recommendation (accepted) |
|---|---|---|---|
| D1 | Is Milestone 1 accepted as merged? `CLAUDE.md` still says "complete and review Milestone 1" | Updating next steps in `CLAUDE.md` | Confirm, then point "Current next steps" at this plan |
| D2 | Correct the existing rectangular path, moving the 70.9 °C headline? | P2 | Yes, as its own pull request after P1 |
| D3 | Add a realistic reference case, and at what flow per kW? | P4 | Yes; keep the current default for continuity |
| D4 | Property basis: fitted tables checked against CoolProp in tests, or CoolProp at runtime? Which glycol source? | P3 | Fitted tables; keep the install light |
| D5 | Heated-wall boundary condition for Nu: keep the design-loop's H1 with adiabatic cover? | P1 | Yes; it is the form checked against CFD there |
| D6 | Run the measured comparison now or after Milestone 2? | P5 | After P4, before Milestone 2 if the paper's geometry is complete |
| D7 | Keep `docs/fable-handoff.md` in the repo? | Nothing | Commit it once, as the dated source for this plan |

## How the work is run

- **Orchestrator (Fable):** writes each brief (scope, files, gates, what not to touch, what to report),
  reviews the pull request and the figure, and brings physics-judgment calls to Riccardo.
- **Implementer (Opus 5.5):** one pull request at a time, on a branch, from the written brief.
- **Checker (Haiku):** re-derives hand-calculation numbers independently and checks that numbers quoted
  in docs match generated output.
- Gates are never loosened. If one fails, work stops and the numbers are reported.
- State lives in `PROGRESS.md` ("Resume here") and this file, not in chat.
