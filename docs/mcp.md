# MCP Tool Contracts

This server exports five tools.

For a runnable, no-network example that calls these tools through the MCP layer
and prints the payloads below, see [`examples/mcp_client_demo.py`](../examples/mcp_client_demo.py).
For a complete calculation that can be explained in an interview or design review,
see the [representative eight-GPU walkthrough](representative-walkthrough.md).

## 1) `analyze_coldplate`
Purpose: single-point thermal + hydraulic analysis.

Example request / response (canonical 700 W / 8 LPM water default case):

```jsonc
// request
{"heat_load_w": 700.0, "flow_rate_lpm": 8.0, "inlet_temp_c": 25.0, "coolant": "water"}

// response (abridged)
{
  "coolant": "water",
  "regime": "transitional",
  "reynolds": 3734.08,
  "junction_temp_c": 70.90,
  "pressure_drop_pa": 16800.35,
  "pump_power_w": 4.48,
  "resistances_k_per_w": {"junction_to_case": 0.04, "tim": 0.02, "base_conduction": 0.00052, "convection": 0.00416, "total": 0.06467}
}
```

Inputs (stable):
- `heat_load_w` (float > 0)
- `flow_rate_lpm` (float > 0)
- `inlet_temp_c`, `ambient_temp_c`
- `coolant`: `"water" | "glycol50"`
- `r_jc_k_per_w`, `r_tim_k_per_w`
- `geometry` object

Output shape:
- `junction_temp_c`
- `resistances_k_per_w` (includes `junction_to_case`, `tim`, `base_conduction`, `convection`, `total`)
- `pressure_drop_pa`, `pump_power_w`
- `reynolds`, `regime`, `nusselt`, `heat_transfer_coeff_w_m2k`
- `coolant_rise_c`, `warnings`

## 2) `compare_coolants`
Purpose: compare water vs 50/50 glycol under identical load and geometry.

Inputs: same as `analyze_coldplate` except coolant omitted.

Output shape:
- `inputs`
- `results.water` (full analyze output)
- `results.glycol50` (full analyze output)

## 3) `optimize_flow_rate`
Purpose: minimum flow meeting a max junction temperature.

Inputs:
- `heat_load_w`
- `max_junction_temp_c`
- `coolant`
- `flow_min_lpm`, `flow_max_lpm`
- `margin_c` (default 0°C)
- shared thermal/geometry params

Output shape:
- `target_max_junction_temp_c`
- `minimum_flow_rate_lpm`
- `met_target`
- `analysis_at_minimum_flow`

## 4) `analyze_rack`
Purpose: rack-level model for N identical GPUs in series or parallel topology.

Inputs:
- `gpu_count` (int > 0)
- `topology`: `"series" | "parallel"`
- `heat_load_per_gpu_w` (float > 0)
- `total_flow_lpm` (float > 0)
- `cdu_supply_temp_c`
- `coolant`: `"water" | "glycol50"`
- `r_jc_k_per_w`, `r_tim_k_per_w`
- `geometry` object

Output shape:
- `max_junction_temp_c`
- `per_gpu_junction_temps_c` (list)
- `total_pressure_drop_pa`
- `total_pump_power_w`
- `cdu_outlet_temp_c`
- `total_heat_load_w`

## 5) `generate_decision_report` — report schema v2

Purpose: thermal screening with explicit evaluated points and limited search
claims. This is not a complete system/CDU feasibility assessment.

Existing input names remain available: `chip_label`, `heat_load_w`, `gpu_count`,
`topology`, `target_junction_temp_c`, `margin_c`, `coolant`, `inlet_temp_c`,
`flow_rate_lpm`, `geometry`, `r_jc_k_per_w`, and `r_tim_k_per_w`.
Omitted or null tool arguments use the domain defaults. Explicit numeric values,
including values equal to defaults, retain supplied provenance. A fixed flow is
in LPM **per GPU** and is evaluated unchanged; a null/omitted flow requests a
thermal search over 0.5–60 LPM per GPU.

Optional inputs:

- `stress_scenarios`: settings object with `r_jc_variation_fraction` (default 0.2,
  producing separate positive/negative cases), `r_tim_multiplier` (2.0),
  `heat_load_delta_w` (+10 W), and `supply_temp_delta_c` (+1°C).
  Each perturbation is evaluated independently at the same flow and topology.
  These are illustrative scenarios, not probability or service-life models.
- `input_source_notes`: caller-provided notes keyed by resolved field path, such
  as `heat_load_w` or `geometry.channel_count`. A note is not verified evidence.

Read `report_schema_version` (2) and `status` first:

| Status | Interpretation |
|---|---|
| `meets_target` | The evaluated point meets the temperature limit minus caller guardband under this model. |
| `fails_at_evaluated_flow` | The supplied fixed-flow point fails; another point might work. |
| `no_feasible_flow_in_search_range` | The supported single-plate/identical-parallel search found no passing point in its interval. |
| `undetermined` | An automatic series candidate failed without a rack-wide search, or evaluation was unavailable. |

`evaluated_point` is nullable. When present it identifies its role, per-GPU flow,
input supply temperature, junction temperature, both thermal margins, and whether
the guarded criterion was met. `margin_to_limit_c` is the limit minus temperature;
`margin_to_criterion_c` additionally subtracts the requested guardband.

`flow_search` is null for fixed flow. For automatic flow, it records search
scope, bounds, and nullable `minimum_feasible_lpm_per_gpu`. A diagnostic upper
bound or a series candidate is not a proven minimum. Search outputs retain
calculation precision so rounding does not reverse target passage.

Every report also includes `system_hydraulic_feasibility: "not_assessed"`,
`risk_assessment: "not_assessed"`, resolved inputs, leaf-field `input_provenance`,
model metadata with `validation_state: "unvalidated"`, signed `stress_scenarios`,
`topology_assessment`, warnings, blind spots, and `rendered_memo`.

### Migration from the previous report

This report is intentionally breaking. It does not change the numerical
single-plate/rack equations, the other four tool names/contracts, or standalone
`analyze()`, `analyze_rack()`, and `optimize_flow()` return types. Applicability
warnings have been expanded. The package release version is separate from the
report schema version; publishing requires an explicit release and migration
notice rather than silently updating existing installations.

| Removed report field | Use instead |
|---|---|
| `feasible` | `status` and nullable `evaluated_point.meets_thermal_target` |
| `recommended_flow` | `evaluated_point.flow_lpm_per_gpu` and scoped `flow_search` |
| `recommended_supply_temp_c` | `evaluated_point.supply_temp_c` (an input) |
| `junction_temp_at_recommended_c` | `evaluated_point.junction_temp_c` |
| `margin_remaining_c` | `evaluated_point.margin_to_limit_c` and `margin_to_criterion_c` |
| `risk_level` | `risk_assessment`; no LOW/MEDIUM/HIGH claim is made |
| `uncertainty_section` | Signed, separately evaluated `stress_scenarios` |
| `topology_recommendation` | `topology_assessment` |

For example, replace `report["recommended_flow"]["recommended_lpm"]` with a
null-checked read of `report["evaluated_point"]["flow_lpm_per_gpu"]`. Inspect the
point's role and report status: a diagnostic point is not a recommended setting.
Do not turn an unavailable point or failed search into a zero-valued result.

Invalid requests retain the `{ "error": [...] }` envelope. A valid request that
cannot be evaluated in the model returns an `undetermined` report instead of
inventing temperature or margin values. See the runnable
[client](../examples/mcp_client_demo.py) and
[reference reports](../examples/decision_memo_examples.py).

## How an MCP client uses this
The client should gather load, coolant, target temperature, and rack topology,
then call the narrowest tool that answers the question:

1. Junction temperature result
2. Dominant resistance(s)
3. Pump/pressure impact and trade-offs
4. Any warnings or model limitations
