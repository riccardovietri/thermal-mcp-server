# Model Overview

`thermal-mcp-server` is a steady-state, first-pass sizing model for liquid-cooled
accelerator cold plates and identical-GPU racks.

## System Boundary

The model starts at package heat load and ends at cold-plate coolant outlet or
rack CDU return temperature. It does not include facility loops, CDU internals,
manifolds, pump curves, or measured vendor calibration.

## Cold-Plate Thermal Path

The cold plate is represented as a 1D resistance chain:

```text
R_total = R_jc + R_tim + R_base + R_conv
T_junction = T_inlet + 0.5 * coolant_rise + Q * R_total
coolant_rise = Q / (m_dot * cp)
```

`R_jc` and `R_tim` are caller-provided package/interface resistances. `R_base`
comes from copper thickness, copper conductivity, and contact area. `R_conv`
comes from the heat-transfer coefficient over the simplified channel wetted
area.

## Flow And Pressure

Flow is split across identical rectangular channels. Hydraulic diameter is:

```text
Dh = 2 * width * height / (width + height)
```

Heat transfer uses:

- `Nu = 4.36` for laminar flow.
- Dittus-Boelter for turbulent flow.
- Linear blending from `Re = 2300` to `Re = 4000`.

Pressure drop uses Darcy-Weisbach with laminar friction, Blasius turbulent
friction, and the same transition blend.

## Rack Aggregation

Rack analysis supports identical GPUs in two topologies:

- Series: one coolant stream flows through each cold plate in sequence. Coolant
  temperature rises GPU by GPU, pressure drop accumulates across cold plates.
- Parallel: total flow splits evenly across all cold plates. Each GPU sees CDU
  supply temperature, and rack pressure drop equals one branch pressure drop.

Rack pressure drop is cold-plate-only. Manifold/header losses must be added
outside this model when they matter.

## Outputs

Core outputs include junction temperature, coolant rise, Reynolds number,
Nusselt number, pressure drop, pump power, rack return temperature, and warnings
when model limits are exceeded.
