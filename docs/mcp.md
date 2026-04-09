# MCP Tool Contracts

This server exports four tools.

## 1) `analyze_coldplate`
Purpose: single-point thermal + hydraulic analysis.

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
- `total_flow_lpm`
- `total_pressure_drop_pa`
- `total_pump_power_w`
- `cdu_outlet_temp_c`
- `total_heat_load_w`

## How Claude uses this
Claude asks clarifying questions (load, coolant, target temp), then calls one of the four tools and explains:
1. Junction temperature result
2. Dominant resistance(s)
3. Pump/pressure impact and trade-offs
4. Any warnings or model limitations
