# Assumptions

This file lists the model assumptions that most affect interpretation.

## Coolants

The package supports `water` and `glycol50`. Fluid properties are fixed values at
a nominal 25°C reference point, not temperature-dependent lookups. This keeps
runs deterministic but means viscosity, heat capacity, conductivity, and
pressure-drop estimates are not bounded by this repository when coolant
temperature differs materially from that reference point.

## Cold Plate

The default geometry is a simplified rectangular-channel cold plate. It is not
a vendor plate design. Geometry inputs control channel count, channel width,
channel height, channel length, base thickness, contact area, and copper
conductivity.

The model assumes uniform flow across channels and a single effective contact
area. The convective resistance uses the full channel wetted perimeter times
length as an effective heated area; this does not establish uniform wall heating,
fin efficiency, or conjugate conduction. The rectangular-channel correlations
are first-pass approximations and do not cover every aspect ratio, boundary
condition, entrance length, or developing-flow state. See the
[F-Chart/EES rectangular-duct reference](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1122.htm)
for the kinds of factors that affect rectangular-channel correlations. The model
also does not represent local maldistribution, detailed fin geometry, 2D
spreading, fouling, or manufacturing variation.

## Heat Load And Package Resistance

Heat load is a steady-state chip power input. `R_jc` and `R_tim` are explicit
inputs with scenario defaults; they are not inferred or validated package
properties. For chips where vendors do not publish package thermal resistance or
junction limits, examples label values as estimates or proxies. The sensitivity
perturbations in the current implementation are illustrative model scenarios,
not manufacturing distributions, TIM service-life predictions, or TDP lifetime
forecasts.

## Rack

Rack analysis assumes identical GPUs and identical cold plates. Series topology
uses one loop through all GPUs. Parallel topology splits flow evenly across all
GPUs. Manifold and header losses are excluded by design.

## Validation Boundary

Tests include behavioral checks and independent hand-calculation checks for
core equations and rack aggregation. These tests establish that the implemented
relationships are reproducible; they do not validate predicted hardware
temperatures, pressure drops, or flow distribution. The repository contains no
measured cold-plate or rack dataset and no proprietary calibration.

### Claim and evidence matrix

| Claim or output | Evidence currently present | Boundary of what the evidence supports |
|---|---|---|
| Thermal and hydraulic equations are implemented deterministically | Source equations, hand calculations, and regression tests | Implementation correctness and repeatability; not hardware accuracy |
| Rectangular-channel heat transfer and pressure drop are represented | Hydraulic diameter plus laminar/turbulent approximations | Conditional first-pass estimates; arbitrary geometry and correlation validity are not established |
| Rack series/parallel aggregation is consistent | Two-GPU hand-calculation tests and invariants | Ideal identical-GPU aggregation with equal flow and no manifold losses |
| Sensitivity output identifies possible decision drivers | Finite-difference tests and explicit perturbations | Illustrative model deltas; no probability, population tolerance, or lifetime claim |
| Public accelerator scenarios are usable inputs | Source labels and estimate/proxy labels in `docs/public_specs.md` and examples | Scenario exploration only; public TDP or limit data do not validate thermal predictions |
| A rack/CDU design is hydraulically feasible | Not established without non-plate losses, available head, and component/system evidence | Treat feasibility as undetermined or require caller-supplied evidence when those inputs matter |

Results should therefore be reported as conditional engineering estimates with
their input provenance and omitted effects visible. A clean software result is
not evidence of measured performance.
