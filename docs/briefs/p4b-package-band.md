# Brief P4b: package-resistance band in the reference case

Written 2026-11-18 by the orchestrator. Implementer: Opus 5.5.
Branch: `docs/case-study-page` (pull request 59), after merging in
`origin/docs/package-resistance-review`. Do not merge the pull request.

Read first: `CLAUDE.md`, `docs/research/package-resistance-review.md` (sections 1, Q1, Q2, 3 and 4),
`docs/fidelity-results.md`, `examples/reference_case.py`, `examples/make_figures.py`, `docs/index.html`.

## Owner decisions (2026-11-18)

1. Show estimated package resistance as a **band**, not a point, for the chips whose die area is
   known. Keep the generic 60 mK/W as a labelled conservative case.
2. Do it in the **examples only**. `src/`, schema, defaults and `R_jc` / `R_tim` defaults are untouched.
3. MI300X and Gaudi 3 stay on the generic values, labelled "die area not published".
4. Relabel sources; keep every limit and TDP value.
5. Flag the Gaudi 3 power conflict.

## Scope

### Chip data (`examples/real_chip_benchmarks.py`)

Values unchanged. Labels and source strings only:

- `"B200 (NVL72)"` becomes `"Blackwell GPU (GB200 NVL72)"`. 1200 W is cited to the NVIDIA Blackwell
  datasheet ("configurable up to 1,200 W" per GPU in GB200 NVL72), no longer to SemiAnalysis.
- 75 °C is kept and described as a design target whose source could not be traced, not a vendor limit.
- H100 83 °C is kept and described as a conservative design value: not vendor-published for SXM;
  the H100 PCIe product brief gives 87 °C.
- Gaudi 3 liquid 1200 W is kept with a note that Intel's 2025 technical paper states 900 W
  liquid-cooled while its Hot Chips 2024 material states 1200 W.
- Use the citations in the review's source list; do not add sources you have not got from it.

This changes that script's printed labels. Update test literals that assert on the old label or
source strings, label text only, and list each edit in the report. No numeric literal may change.
Other examples that say "B200" in prose may keep it (it is the correct GPU name); fix only places
that attribute the 1200 W figure to SemiAnalysis.

### Package band (`examples/reference_case.py`)

Add named, commented constants (area-specific, with the review's source tags) and a function that
turns a die area and a build into `r_jc_k_per_w` and `r_tim_k_per_w`:

| Term | Low | High | Basis |
|---|---|---|---|
| Die conduction | 0.5 mm / 122 W/m·K | 0.8 mm / 122 W/m·K | thickness is an assumption; k from the review |
| TIM1, reflowed indium (lidded only) | 0.023 K·cm²/W | 0.05 K·cm²/W | review Q1 |
| Copper lid (lidded only) | 1.5 mm / 385 W/m·K | 3 mm / 385 W/m·K | thickness is an assumption |
| TIM2 | 0.04 K·cm²/W | 0.12 K·cm²/W | phase-change pad to optimized grease |

Bare die: `R_jc` = die, `R_tim` = TIM2. Lidded: `R_jc` = die + TIM1 + lid, `R_tim` = TIM2.
Die areas: H100 8.14 cm² (NVIDIA); Blackwell GPU 15.6 cm², labelled in code and output as an
order-of-magnitude footprint from a published test-vehicle paper, not a measured die area.
1D conduction over the die area, uniform power, no hotspot factor: say so in the output.

Apply the band to configuration C (straight-fin plate, 1.5 LPM/kW, 35 °C inlet) for H100 and the
Blackwell GPU. Print a table with the four builds (bare-die low and high, lidded low and high) and
the generic case, giving `R_jc`, `R_tim`, their sum, junction temperature and margin. Expose the
data through the existing dictionary-returning function. The existing A, B, C rows stay as they
are, with C now labelled as the generic 60 mK/W conservative case.

### Figure (`docs/img/chip_reference_case.png`)

Keep the three panels. In the junction-temperature panel add, for H100 and the Blackwell GPU, a
horizontal range bar for configuration C with the estimated package (bare-die low to lidded high),
visually distinct from the generic markers and named in the legend. In the resistance-stack panel
add two bars for H100 configuration C at the band's low and high ends. Open the PNG and check it:
no overlaps, nothing clipped, the limit ticks still visible.

### Docs

- `docs/fidelity-results.md`: add the band table and rewrite the findings so the page's conclusion
  is accurate: with the generic package no chip passes at 1.5 LPM/kW; with package values estimated
  from die area and published interface data, H100 and the Blackwell GPU plausibly pass on the
  straight-fin plate; the estimate is low confidence on values because no vendor publishes
  junction-to-case resistance, it is not known whether the parts are lidded, and hotspots are not
  included. Link the review.
- `docs/index.html` (case study, first person as the owner): same change. Update the three-number
  strip, the reference-case section, "What is still not validated" and the figure caption. Keep the
  page's style rules: no em or en dashes, plain direct sentences, every number from generated output.
- `README.md` blurb, `docs/public_specs.md`, `CLAUDE.md` "Chip reference data" list: labels and
  sources to match.
- `docs/decisions.md`: a dated entry recording the five owner decisions above.
- `PROGRESS.md` and `docs/work-plan.md`: state updated; record that area-specific schema fields
  are a deferred option, described in the review.

## Gates

**G1. Band values**, produced by the orchestrator with the model on configuration C. Match at the
printed precision:

| Chip | Build | R_jc (mK/W) | R_tim (mK/W) | Sum (mK/W) | Tj (°C) |
|---|---|---|---|---|---|
| H100 | bare die, low | 5.035 | 4.914 | 9.949 | 52.25 |
| H100 | bare die, high | 8.056 | 14.742 | 22.798 | 61.24 |
| H100 | lidded, low | 12.647 | 4.914 | 17.561 | 57.58 |
| H100 | lidded, high | 23.771 | 14.742 | 38.513 | 72.24 |
| Blackwell GPU | bare die, low | 2.627 | 2.564 | 5.191 | 55.43 |
| Blackwell GPU | bare die, high | 4.203 | 7.692 | 11.896 | 63.48 |
| Blackwell GPU | lidded, low | 6.599 | 2.564 | 9.163 | 60.20 |
| Blackwell GPU | lidded, high | 12.404 | 7.692 | 20.096 | 73.32 |

**G2. Existing numbers do not move.** Every A, B, C value, minimum flow and resistance-stack value
from P4 is unchanged; `src/` is untouched; no numeric test literal changes.

**G3. Tests.** New assertions pin the G1 values and the die areas; the figure stays deterministic.

**G4. Wording.** Nowhere do the docs say a chip "passes" without the words estimate or plausibly
and the confidence caveat nearby. No vendor junction-to-case value is claimed.

**G5. Full quality gate:** `uv run pytest`, `ruff check .`, `ruff format --check .`, `mypy`,
`uv build`, notebook check.

## Do not touch

`src/`, defaults, limit and TDP values, coolant data, warning wording, the review document, the
sibling repo. No new dependency. No web access is needed; use only the review's sources.

## Report back

Under 400 words: commits; G1 to G5 with measured values; the list of label-only test edits; the
new band table; deviations and why; questions for the owner; anything not verified.
