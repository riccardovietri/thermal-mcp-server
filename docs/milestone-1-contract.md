# Milestone 1: result contract for owner review

Status: approved by the owner on 2026-09-10; implementation complete and awaiting
owner review. Branch: `feat/decision-engine-foundation`.
This implements the first milestone of [the product review](product-thesis-review.md),
not the constrained hydraulic sizing planned for Milestone 2.

## Approved decision

Implement a versioned **report schema v2** with explicit evaluated points, search
scope, unknown results, and evidence limitations. Keep the Python function and
MCP tool names. Their report output changes deliberately; migrate the repository's
examples and document external consumer changes together. Do not retain misleading
numeric placeholders as compatibility aliases.

The underlying single-plate/rack equations, geometry defaults, coolant constants,
temperature limits, and standalone analysis/optimizer APIs remain unchanged.

## Implemented report behavior

| Request/result | Status | What the report may conclude |
|---|---|---|
| Fixed flow meets target minus caller guardband | `meets_target` | This modeled operating point meets the thermal criterion. |
| Fixed flow misses that criterion | `fails_at_evaluated_flow` | This point fails; another flow may work. |
| Single plate or identical parallel rack thermal search succeeds | `meets_target` | A minimum thermal flow was found within the declared search interval under this model. |
| That same supported search fails | `no_feasible_flow_in_search_range` | No modeled point in this interval meets the thermal criterion; no recommendation exists. |
| Automatic series candidate fails | `undetermined` | Candidate fails, but no rack-wide search was performed. |
| Evaluation exceeds a supported input boundary | `undetermined` | Temperature and margin are unavailable; do not substitute single-plate values. |

An automatic series candidate that meets the target can establish a passing point,
but cannot establish a minimum rack flow. Its search scope must say
`single_plate_candidate_for_series`; the minimum rack flow stays `null`.

All verdicts are conditional model results. Every report explicitly says hydraulic
feasibility and overall engineering risk are **not assessed**, because system head,
loss budgets, and validated risk criteria are absent.

## Concrete output shape

Illustrative fixed-flow request: `DecisionScenario(flow_rate_lpm=8.0)` with other
defaults. The implemented response includes this excerpt:

```json
{
  "report_schema_version": 2,
  "status": "meets_target",
  "evaluation_mode": "fixed_flow",
  "attempted_flow_lpm_per_gpu": 8.0,
  "evaluated_point": {
    "role": "fixed_input",
    "flow_lpm_per_gpu": 8.0,
    "supply_temp_c": 25.0,
    "junction_temp_c": 70.90,
    "margin_to_limit_c": 12.10,
    "margin_to_criterion_c": 7.10,
    "meets_thermal_target": true
  },
  "flow_search": null,
  "system_hydraulic_feasibility": "not_assessed",
  "risk_assessment": "not_assessed"
}
```

The supplied 8 LPM remains 8 LPM. The report does not change it to 9.2 LPM or
claim that 8 LPM is the minimum. Temperature rounding is presentation precision,
not a claim of measured accuracy.

`margin_to_limit_c` is the hard temperature limit minus junction temperature;
`margin_to_criterion_c` additionally subtracts the caller guardband. Only the
guarded criterion determines target passage. Point roles are `fixed_input`,
`thermal_search_result`, `series_candidate`, or `search_bound_diagnostic`.
System hydraulic feasibility is distinct from available component pressure
estimates; those lower-level calculations remain available through existing APIs.

For `heat_load_w=1200, target_junction_temp_c=75`, the default thermal search
would report this excerpt:

```json
{
  "status": "no_feasible_flow_in_search_range",
  "flow_search": {
    "scope": "single_plate",
    "min_lpm_per_gpu": 0.5,
    "max_lpm_per_gpu": 60.0,
    "minimum_feasible_lpm_per_gpu": null
  }
}
```

If the upper-bound point can be evaluated, retain it under `evaluated_point` as
a failed diagnostic point. It is not a recommendation. Never emit a 60/69/90 LPM
band. On successful searches, evaluate the returned feasible flow itself; remove
the arbitrary 15% and 50% multipliers. Record whether the minimum is limited by
the lower search bound. Preserve enough precision that serialization cannot
turn a passing flow into a failing point.

For a fixed 256-GPU series case at 8 LPM that exceeds the downstream inlet bound:

```json
{
  "status": "undetermined",
  "attempted_flow_lpm_per_gpu": 8.0,
  "evaluated_point": null,
  "flow_search": null,
  "warnings": ["Rack evaluation unavailable: downstream inlet exceeds the supported input bound."]
}
```

No rack temperature or thermal margin is implied. Retain the attempted input so
the engineer can reproduce the failure.

## Evidence and scenario semantics

Include the complete resolved scenario, model/package version, nominal coolant
property reference temperature, and explicit limitations in the report. Label
inputs as supplied or defaulted; neither means measured or vendor-verified.
Optional caller source notes are assertions of provenance, not automatic validation.
Track nested geometry defaults accurately and preserve provenance through MCP.
Use `input_provenance` keyed by resolved field path (for example,
`geometry.channel_count`), with `origin: supplied | defaulted` and a nullable
caller source note. An explicit value equal to the default is still supplied.
Transport defaults must not erase that distinction before scenario construction;
include Python/MCP parity tests for omitted and explicitly supplied values.

Replace the current uncertainty dictionary with named, signed stress scenarios:
package resistance variation, TIM resistance multiplier, heat-load increase, and
supply-temperature increase. Let callers set their magnitudes, with current
numeric perturbations retained only as clearly labeled illustrative defaults.
Specifically: package-resistance variation fraction `0.20` produces separate
−20% and +20% cases; TIM multiplier defaults to `2.0`; additive heat-load change
defaults to `+10 W`; additive supply-temperature change defaults to `+1°C`.
Each result records the changed parameter, its base and perturbed values with
units, and the signed junction-temperature delta from the evaluated baseline.
Do not imply a probability distribution, population tolerance, or service life.
Evaluate each stress on the selected architecture at the same flow, including
series coolant heating. Unsupported stressed cases remain unavailable. Do not
invent a combined worst case or LOW risk judgment from these separate scenarios.

The report carries a model-validation state of `unvalidated` and specific
applicability notices: transition blending, rectangular-channel correlations,
effective heated area, fixed properties, and absent hardware calibration. Numeric
input acceptance must never imply correlation validity. Existing lower-level
analysis APIs receive compatible warnings/documentation where needed; their
numeric values do not change in this milestone.

## Migration and scope

| Existing report field | v2 replacement |
|---|---|
| `feasible` | `status` plus `evaluated_point.meets_thermal_target`; no overall feasibility claim |
| `recommended_flow` | `evaluated_point` and nullable `flow_search.minimum_feasible_lpm_per_gpu` |
| `recommended_supply_temp_c` | `evaluated_point.supply_temp_c`, explicitly an input |
| `junction_temp_at_recommended_c` | Nullable `evaluated_point.junction_temp_c` |
| `margin_remaining_c` | `evaluated_point.margin_to_limit_c` |
| `risk_level` | `risk_assessment: not_assessed` |
| `uncertainty_section` | Signed, explicitly scoped stress scenarios |
| `topology_recommendation` | `topology_assessment`, labeled comparison rather than selected design |

Retain scenario label, warnings, blind spots, and rendered memo. Update typed
schemas, report synthesis, thin MCP wiring, contract tests, and affected examples
together. The memo must explain the same status as its structured response.

This is an explicit breaking report-contract change, not an additive patch.
Approval includes the provenance and configurable stress-scenario work above,
as well as the core status/flow fixes; these are substantive Milestone 1 scope.
Document migration and release implications before merge; do not publish a release
or rename the project as part of this work. No rack-wide optimizer, manifold model,
pump curve, new correlation, or measured-accuracy claim is included.

## Acceptance and review

- Fixed flow is preserved exactly; failed searches yield no invented flow band.
- Passing/failing/unknown statuses cannot contradict the actual evaluated point.
- Series candidate failure does not claim that the architecture is infeasible.
- Unsupported rack/stress results contain no fabricated temperatures or margins.
- Selected-point physics warnings survive into the structured report and memo.
- Memo values use readable display precision while structured values retain calculation precision.
- Input provenance distinguishes defaults from supplied values through Python and MCP.
- Stress scenarios use signed changes and the actual topology, with no lifetime claims.
- Independent thermal/hydraulic equation checks pass; tests do not imply hardware validation.
- Existing behavioral protections remain covered; intended contract changes receive
  replacement assertions rather than weakened tests.
- Full tests, notebook, lint, format, typing, build, and examples pass before owner review.

Luna/high produced focused report, equation-test, and documentation audits. Astra
owns the final contract, integration, and reproduction of the failure cases before
asking the owner to run the ready examples and approve any merge.
