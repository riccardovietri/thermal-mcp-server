# Model Overview

`thermal-mcp-server` is a steady-state, first-pass model for liquid-cooled
accelerator cold plates and identical-GPU racks. It is intended to make the
calculation path inspectable before an engineer commits to detailed simulation,
hardware testing, or a supplier curve.

For a short explanation suitable for an interview or project walkthrough, start
with the [representative eight-GPU case](representative-walkthrough.md).

## Where the physics lives

The implementation is organized as a small, reviewable stack:

- [`physics.py`](../src/thermal_mcp_server/physics.py) contains `analyze()`,
  `analyze_rack()`, `compute_sensitivity()`, and `optimize_flow()`.
- [`schemas.py`](../src/thermal_mcp_server/schemas.py) defines units, defaults,
  and input boundaries.
- [`decision_report.py`](../src/thermal_mcp_server/decision_report.py) composes
  results into a first-pass decision memo without adding new physics.
- [`test_physics_behavior.py`](../tests/test_physics_behavior.py) contains
  behavioral and independent hand-calculation checks.
- [`physics.md`](physics.md) contains the detailed derivation, assumptions, and
  limitations.

## System boundary

The model starts with a steady package heat load and ends at cold-plate coolant
outlet or rack CDU return temperature. It does not include facility loops, CDU
internals, manifolds, pump curves, measured vendor calibration, transient thermal
mass, boiling, or local temperature fields. Rack results assume identical GPUs,
identical cold plates, and equal flow split in parallel branches.

## What is universal, empirical, and device-specific

Some relationships below are conservation or definition-level relationships.
Others are empirical closures whose validity depends on geometry and regime. The
remaining quantities describe a particular package, cold plate, coolant, or pump
and must come from the caller or measured data.

| Category | Examples in this model | Interpretation |
|---|---|---|
| Conservation / definitions | `Q_dot = m_dot * cp * deltaT`, continuity, `Dh`, `Re`, `Pr` | General relationships under the stated steady single-phase assumptions |
| Analytical idealizations | Fully developed laminar `Nu=4.36` under constant heat flux; Darcy–Weisbach form | Conditional idealizations that require the stated flow and boundary assumptions |
| Empirical closures | Dittus–Boelter `Nu`, smooth-pipe Blasius friction | First-pass approximations; correlation domain and geometry matter |
| Numerical interpolation | Transitional blend between laminar and turbulent endpoints | Solver continuity choice, not a physical or experimental correlation |
| Device or scenario inputs | `R_jc`, `R_tim`, channel geometry, coolant properties, pump efficiency, Tj limit | Must have provenance or be labeled as assumptions; defaults are not measured hardware facts |

## Governing equations

### Energy balance and thermal network

For a steady single-phase stream, heat pickup is represented by:

```text
Q_dot = m_dot * cp * deltaT_coolant
```

The cold plate is a lumped resistance chain. Fourier conduction gives the base
resistance and Newton's law gives the convective resistance:

```text
R_base = t_base / (k_copper * A_contact)
R_conv = 1 / (h * A_wetted)
R_total = sum(R_i) = R_jc + R_tim + R_base + R_conv
```

The reported junction temperature uses the mean coolant temperature in the
plate, approximated as half the bulk rise above the inlet:

```text
T_junction = T_inlet + 0.5 * deltaT_coolant + Q_dot * sum(R_i)
```

`A_wetted` is an effective heated area formed from the channel wetted perimeter
and length. It does not assert that every wall is heated uniformly or include
fin efficiency, spreading, or the actual heat-source footprint.

### Flow, dimensionless groups, and heat transfer

For `n` identical rectangular channels, continuity gives:

```text
v = V_dot / (n * width * height)
Dh = 2 * width * height / (width + height)
Re = rho * v * Dh / mu
Pr = cp * mu / k
```

The model closes heat transfer with `Nu=4.36` for its fully developed,
constant-heat-flux laminar idealization and Dittus–Boelter for its turbulent
approximation:

```text
h = Nu * k / Dh
```

The official [F-Chart/EES rectangular-duct procedure](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1120.htm)
uses Reynolds number, Prandtl number, length/hydraulic-diameter ratio, aspect
ratio, relative roughness, wall boundary condition, and developing-flow
corrections. Its [laminar duct procedure](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1122.htm)
expects `Re < 2300` and uses bulk-average properties. Those documented inputs
show why a single `Nu=4.36` or Dittus–Boelter value cannot establish accuracy for
arbitrary rectangular cold plates. This implementation does not model those
corrections or enforce a correlation-specific validity range. The linear
transition blend from `Re=2300` to `Re=4000` provides numerical continuity for
optimization, not experimental validation.

### Pressure drop and pump estimate

The channel pressure drop uses Darcy–Weisbach with hydraulic diameter:

```text
deltaP = f * (L / Dh) * (rho * v^2 / 2)
```

The turbulent friction closure is the smooth-pipe Blasius form:

```text
f = 0.3164 * Re^(-0.25)
```

The official [EES turbulent pipe procedure](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1022.htm)
requires Reynolds number, length/diameter, relative roughness, and developing-
flow treatment when estimating turbulent friction. The model's smooth-pipe
Blasius closure is therefore only a simplified channel estimate; it does not
cover manifold, header, entrance, exit, roughness, or other minor losses. Pump
power is only an illustrative estimate using the fixed model efficiency:

```text
P_pump = deltaP * V_dot / 0.50
```

The result is not a pump curve or a system operating point.

## Worked default case

For `700 W`, `8 L/min` water, `25°C` inlet, and the default geometry and
resistances, the model calculates:

```text
coolant rise                 1.25976°C
mean coolant rise            0.62988°C
package + TIM rise          42.00000°C   (700 * (0.04 + 0.02))
base conduction rise         0.363636°C
convection rise              2.90879°C
reported junction temp      70.9023°C
pressure drop               16.8003 kPa
```

The temperature is therefore `25 + 0.62988 + 42 + 0.363636 + 2.90879`.
This is a reproducible calculation of the stated model and inputs, not measured
validation of an H100 or any other physical cold plate.

## Rack aggregation

Rack analysis supports two idealized topologies:

- Series: one stream passes through each cold plate. Coolant temperature and
  cold-plate pressure drop accumulate GPU by GPU.
- Parallel: total flow splits equally across identical branches. Each GPU sees
  the CDU supply temperature and rack pressure drop equals one branch's modeled
  cold-plate drop.

Only cold-plate pressure drop is calculated. A manifold or CDU requirement is
incomplete unless non-plate losses and available pump head are supplied separately.

## Applying the model beyond GPU racks

The same reduced-order calculation can apply conditionally to an electronics or
robotics inverter cold plate when the heat load is steady, the coolant is
single-phase, the flow geometry is represented, and package/interface resistances
have a defensible source. It does not automatically model a motor. Motors add
time-varying losses, winding and core conduction paths, thermal mass, rotating
components, and often different cooling boundaries. Those cases require their
own thermal network, transient analysis, or measured component data.
