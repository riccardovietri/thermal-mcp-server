# Physics Model and Assumptions

## A) Overview
The model is a steady-state, 1D thermal resistance network for rapid, first-pass
design analysis. It combines conservation relationships with reduced-order
internal-flow correlations and caller-supplied package/interface resistances.
The equations and software behavior have hand-calculation and regression tests,
but the repository does not contain measured cold-plate or rack data. Those tests
verify implementation and aggregation; they do not establish predictive accuracy
for a particular hardware design.

Thermal path:
`Junction -> Case -> TIM -> Base conduction -> Convection to coolant`

The coolant carries the heat downstream through its bulk temperature rise.
`ambient_temp_c` is a legacy reserved input, not a heat-rejection term in these
equations. The model does not solve heat transfer from coolant to room air.

## B) Equations used
- Reynolds number:
  - `Re = rho * v * Dh / mu`
- Prandtl number:
  - `Pr = cp * mu / k`
- Nusselt number:
  - Laminar (`Re < 2300`): `Nu = 4.36` (fully developed, constant heat flux)
  - Turbulent (`Re > 4000`): `Nu = 0.023 * Re^0.8 * Pr^0.4` (Dittus–Boelter)
  - Transitional: linear blend between laminar and turbulent endpoints for numerical continuity during optimization; this blend is not an experimentally validated transition correlation.
- Convection coefficient:
  - `h = Nu * k / Dh`
- Convection resistance:
  - `R_conv = 1 / (h * A_wetted)`
- Base conduction resistance:
  - `R_base = t_base / (k_cu * A_contact)`
- Total thermal resistance:
  - `R_total = R_jc + R_tim + R_base + R_conv`
- Coolant bulk rise:
  - `deltaT_coolant = Q / (m_dot * cp)`
- Junction temperature:
  - `Tj = Tin + 0.5*deltaT_coolant + Q*R_total`
- Pressure drop (Darcy–Weisbach):
  - `deltaP = f * (L/Dh) * (rho * v^2 / 2)`
  - Laminar `f = 64/Re`, turbulent `f = 0.3164*Re^-0.25` (Blasius smooth-pipe)

## C) Correlations and regime logic
- Reynolds number determines regime:
  - `<2300`: laminar
  - `2300-4000`: transitional (explicit blend for numerical smoothness)
  - `>4000`: turbulent
- Both Nusselt number and friction factor are linearly blended in the transition regime (Re 2300–4000) to avoid discontinuities. The friction factor blends between the laminar value at Re=2300 (`64/2300 ≈ 0.0278`) and the Blasius turbulent value at Re=4000 (`0.3164 × 4000^−0.25 ≈ 0.0398`), matching the Nusselt number treatment. The blend provides numerical continuity only; it is not evidence that transition behavior is accurate for the specified channel.
- The laminar constant `Nu=4.36` and turbulent Dittus–Boelter expression are first-pass approximations. They do not by themselves establish accuracy for arbitrary rectangular channels, aspect ratios, heating boundaries, entrance lengths, or developing flow. The [F-Chart/EES rectangular-duct reference](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1122.htm) illustrates why those factors affect rectangular-channel correlations. The current implementation does not model those corrections or enforce a correlation-specific validity range.
- The official [EES rectangular-duct documentation](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1120.htm) requires aspect ratio, length/hydraulic-diameter ratio, relative roughness, wall boundary condition, and developing-flow treatment. Its [laminar duct documentation](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1122.htm) expects `Re < 2300` and bulk-average properties. The [turbulent pipe documentation](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1022.htm) likewise includes length/diameter, roughness, and developing-flow effects. These pages provide validity context for the named closures; they do not validate this implementation for arbitrary cold-plate geometry, roughness, entrance effects, or manifolds.
- Pump power is computed as `ΔP × Q / η` with η = 0.50. This is a fixed illustrative assumption, not a pump curve or system operating-point calculation.

## D) Parameters and defaults
- Heat load: `700 W`
- Flow: `8 L/min`
- Inlet temp: `25 C`
- Ambient reference: `25 C`
- `R_jc = 0.04 K/W`, `R_tim = 0.02 K/W`
- Geometry defaults:
  - `channel_count=40`
  - `Dh=1.0 mm`
  - `L=80 mm`
  - `channel_width=1.0 mm`
  - `base_thickness=2.0 mm`
  - `contact_area=0.01 m^2`
  - `k_copper=385 W/m-K`

Coolant table (fixed nominal properties at a 25°C reference point):
- Water: `rho=997 kg/m3`, `cp=4180 J/kg-K`, `k=0.60 W/m-K`, `mu=0.00089 Pa*s`
- Ethylene glycol 50% (by volume): `rho=1060 kg/m3`, `cp=3400 J/kg-K`, `k=0.40 W/m-K`, `mu=0.0048 Pa*s`.

These values are held constant during a run. They are not a temperature lookup,
and the model does not infer whether they remain suitable at the caller's inlet,
bulk, or outlet temperature. A result outside the nominal property point must be
treated as a scenario with unquantified property error.

## E) Limitations and validity boundary
- No manifold/header loss model, channel maldistribution, or branch-to-branch flow tolerance.
- No boiling/two-phase behavior.
- No transient thermal capacitance.
- No explicit 2D/3D spreading resistance in the substrate, base, package, or die.
- Constant properties (no temperature-dependent fluid properties).
- `A_wetted` is the full channel wetted perimeter times channel length. It is an
  effective heated-area assumption, not a claim that every wetted wall is heated
  uniformly. Fin efficiency, conjugate conduction, entrance effects, and the
  actual heat-source footprint are not modeled.
- Geometry fields are algebraically valid inputs, not a guarantee that a physical
  cold plate can be manufactured or that the selected correlation applies.

The model is suitable for transparent, conditional architecture screening when
the caller supplies credible component inputs. It is not validated for hardware
signoff, local hotspot prediction, complete CDU sizing, or any result that
depends materially on the omitted effects above.

## F) Engineering Notes
This model uses Dittus-Boelter for turbulent forced convection and a constant fully developed laminar Nusselt number for low-Re flow. These are reduced-order approximations selected for a transparent first-pass model; their use here is not a validation claim for arbitrary rectangular cold plates. Transitional flow is blended linearly to avoid discontinuities in optimization.

Failure modes not captured: flow maldistribution across channels, 2D/3D spreading resistance in package and base, contact-resistance scatter, TIM pump-out/aging, manifold/header losses, air ingestion, boiling inception, and transient warm-up behavior.

For a future hardware validation, collect: flow rate, inlet/outlet coolant temperatures, multiple base temperatures, pressure drop across the cold plate and relevant assembly, and electrical heat input. Then compare inferred thermal-resistance and pressure-drop curves versus model predictions at stated reference conditions. No such measured dataset is included in this repository today.

Potential future enhancements:
1. Temperature-dependent coolant properties and viscosity correction.
2. Explicit manifold + entrance/exit minor-loss coefficients.
3. Package/base spreading-resistance submodel.
4. Transient RC network for warm-up and control studies.
5. Calibrated contact/TIM resistance distributions (not single deterministic value).
6. Optional uncertainty propagation (Monte Carlo on key inputs).

## G) Rack-level model

`analyze_rack()` extends the single-plate model to N identical GPU cold plates
plumbed in series or parallel. Added 2026-03-06.

### Series topology

CDU supply flows through each cold plate in sequence. The outlet of GPU `i`
becomes the inlet of GPU `i+1`:

```
T_in[0] = T_cdu_supply
T_in[i] = T_in[i-1] + coolant_rise[i-1]
Tj[i]   = (T_in[i] + 0.5 × coolant_rise) + Q × R_total
```

Because fluid properties are constant (no temperature dependence), `coolant_rise`
and `R_total` are the same for every GPU. Therefore:

```
Tj[i+1] - Tj[i] = coolant_rise   (exact)
```

The last GPU is always the hottest. Total pressure drop:

```
ΔP_total = N × ΔP_single
```

This is exact: all cold plates see the same flow and geometry, so each ΔP is
identical. CDU outlet temperature:

```
T_cdu_out = T_cdu_supply + N × coolant_rise
```

### Parallel topology

CDU supply splits equally across all cold plates. Flow per GPU:

```
Q_per_gpu = Q_total / N
```

All GPUs share the same inlet (CDU supply temperature) and are hydraulically
identical. System pressure drop equals the branch pressure drop:

```
ΔP_total = ΔP_single(Q_per_gpu)
```

CDU outlet from an energy balance over the full rack:

```
T_cdu_out = T_cdu_supply + Q_rack_total / (m_dot_total × cp)
```

where `m_dot_total = (Q_total / 60000) × ρ`.

### Pump power

Same 50% efficiency assumption as the single-plate model:

```
P_pump = ΔP_total × (Q_total / 60000) / 0.50
```

### Assumptions and limitations

- **Ambient reference handling:** `ambient_temp_c` is optional for rack inputs.
  If omitted, rack analysis defaults ambient reference to `T_cdu_supply` when
  constructing per-GPU cold plate analyses.
- **Identical GPUs:** All cold plates have the same TDP, geometry, and thermal
  resistances. Heterogeneous racks (mix of GPU types) are not supported.
- **Uniform flow distribution:** No maldistribution between parallel branches.
  The model does not provide an empirical bound for local flow variation.
- **No manifold or header losses:** Only cold-plate ΔP is modeled. The actual
  non-plate loss is unknown to this model and must be supplied or measured before
  a rack-level hydraulic requirement is treated as complete.
- **Constant fluid properties:** The same fixed-25°C reference properties are
  used for every GPU in the rack. The repository does not establish an error
  bound at other temperatures.

### Validation

Two hand-calc tests in `tests/test_physics_behavior.py`:
- `test_rack_series_two_gpu_hand_calc`: Verifies GPU 0 = standalone analysis,
  GPU 1 = GPU 0 + coolant_rise, CDU outlet, and total ΔP for 2-GPU series case.
- `test_rack_parallel_two_gpu_hand_calc`: Verifies all GPUs = standalone at
  per-GPU flow, total ΔP = single-plate ΔP, CDU outlet from energy balance.

---

## Section H: Sensitivity and Uncertainty Analysis

### Motivation

The 1D resistance model produces a single point estimate for `junction_temp_c`.
That estimate should be read as conditional on the supplied inputs and model
assumptions. The `compute_sensitivity()` function exposes illustrative
perturbations through `sensitivity=True` on the `analyze_coldplate` tool. These
perturbations are not measured distributions, manufacturing tolerances, field
service predictions, or lifecycle forecasts.

Current illustrative perturbations are:

- `R_jc`: a centered ±20% change.
- `R_tim`: a doubled value.
- Heat load: a small positive perturbation used to report `∂Tj/∂Q`.

The current helper applies these fixed perturbations. A caller making a hardware
decision must run separate scenarios with evidence-backed bounds outside this
helper. A perturbation result is a model delta, not an implied probability or
service-life expectation.

### Finite-difference scheme

All derivatives use forward differences with step sizes chosen to be small
relative to operating ranges while avoiding floating-point cancellation:

| Parameter | Step | Notes |
|-----------|------|-------|
| Q_heat    | max(1% × Q, 1 W) | Linear regime; forward diff exact |
| R_tim     | max(1% × R_tim, 1e-4 K/W) | Linear regime; forward diff exact |
| T_inlet   | 0.1°C | Forward diff; should return exactly 1.0 |
| R_jc      | ±20% (centered) | Illustrative perturbation, not an uncertainty bound |
| R_tim_aged | R_tim × 2.0 | Illustrative scenario, not a field-degradation prediction |

### Analytical verification

Because the model is linear in Q, R_tim, and T_inlet at fixed flow:

```
Tj = T_inlet + 0.5 × Q/(m_dot × cp) + Q × R_total

∂Tj/∂Q        = (Tj - T_inlet) / Q               [°C/W]
∂Tj/∂R_tim    = Q                                  [°C per K/W]
∂Tj/∂T_inlet  = 1.0                               [dimensionless, exact]
```

The finite-difference tests in `test_sensitivity_*` confirm numerical results
match these analytical values to < 0.01°C tolerance.

### margin_c in optimize_flow_rate

The `margin_c` parameter shifts the optimizer's effective target:

```
effective_target = max_junction_temp_c - margin_c
```

No universal margin is recommended by this model. A caller may use `margin_c` to
encode an externally justified guardband, but the value must reflect the actual
package, TIM, operating, and measurement evidence for the design. Setting
`margin_c=0` (default) reproduces legacy behavior exactly; it does not mean that
zero engineering margin is safe.
