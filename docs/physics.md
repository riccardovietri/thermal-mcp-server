# Physics Model and Assumptions

## A) Overview
The model is a steady-state, 1D thermal resistance network for rapid design analysis.

Thermal path:
`Junction -> Case -> TIM -> Base conduction -> Convection to coolant -> Coolant bulk rise -> Ambient reference`

## B) Equations used
- Reynolds number:
  - `Re = rho * v * Dh / mu`
- Prandtl number:
  - `Pr = cp * mu / k`
- Nusselt number:
  - Laminar (`Re < 2300`): `Nu = 4.36` (fully developed, constant heat flux)
  - Turbulent (`Re > 4000`): `Nu = 0.023 * Re^0.8 * Pr^0.4` (Dittus–Boelter)
  - Transitional: linear blend between laminar and turbulent endpoints
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
- Both Nusselt number and friction factor are linearly blended in the transition regime (Re 2300–4000) to avoid discontinuities. The friction factor blends between the laminar value at Re=2300 (`64/2300 ≈ 0.0278`) and the Blasius turbulent value at Re=4000 (`0.3164 × 4000^−0.25 ≈ 0.0398`), matching the Nusselt number treatment.
- Pump power is computed as `ΔP × Q / η` with η = 0.50 (50% pump efficiency). This is representative for a centrifugal pump at partial load; users should adjust for their specific pump curve when sizing actual hardware.

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

Coolant table (nominal, room-temperature):
- Water: `rho=997 kg/m3`, `cp=4180 J/kg-K`, `k=0.60 W/m-K`, `mu=0.00089 Pa*s`
- Ethylene glycol 50% (by volume, 25°C nominal): `rho=1060 kg/m3`, `cp=3400 J/kg-K`, `k=0.40 W/m-K`, `mu=0.0048 Pa*s`. For propylene glycol, viscosity is ~60-80% higher at 25°C.

## E) Limitations
- No manifold-loss model or channel maldistribution.
- No boiling/two-phase behavior.
- No transient thermal capacitance.
- No explicit 2D spreading resistance in substrate/base.
- Constant properties (no temperature-dependent fluid properties).

## F) Engineering Notes
This model uses Dittus-Boelter for turbulent forced convection and a constant fully developed laminar Nusselt number for low-Re flow. These correlations are well-established for internal flow in heat transfer literature and appropriate for first-pass design analysis. Transitional flow is blended linearly to avoid discontinuities in optimization.

Failure modes not captured: flow maldistribution across channels, 2D/3D spreading resistance in package and base, contact-resistance scatter, TIM pump-out/aging, manifold/header losses, air ingestion, boiling inception, and transient warm-up behavior.

For validation on hardware, collect: flow rate, inlet/outlet coolant temperatures, multiple base temperatures, pressure drop across cold plate, and electrical heat input. Then compare inferred thermal resistance and pressure-drop curves versus model predictions.

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

- **Identical GPUs:** All cold plates have the same TDP, geometry, and thermal
  resistances. Heterogeneous racks (mix of GPU types) are not supported.
- **Uniform flow distribution:** No maldistribution between parallel branches.
  Real manifolds can produce ±10–30% local flow variation.
- **No manifold or header losses:** Only cold plate ΔP is modeled. Manifold
  losses can be 20–50% of cold plate ΔP in a dense rack and are not included.
- **Constant fluid properties:** Same limitation as single-plate model. Negligible
  error at typical operating points; more significant at high inlet temperature.

### Validation

Two hand-calc tests in `tests/test_physics_behavior.py`:
- `test_rack_series_two_gpu_hand_calc`: Verifies GPU 0 = standalone analysis,
  GPU 1 = GPU 0 + coolant_rise, CDU outlet, and total ΔP for 2-GPU series case.
- `test_rack_parallel_two_gpu_hand_calc`: Verifies all GPUs = standalone at
  per-GPU flow, total ΔP = single-plate ΔP, CDU outlet from energy balance.
