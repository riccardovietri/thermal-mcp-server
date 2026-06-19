# Assumptions

This file lists the model assumptions that most affect interpretation.

## Coolants

The package supports `water` and `glycol50`. Fluid properties are fixed nominal
values, not temperature-dependent lookups. This keeps runs deterministic but
means viscosity and pressure-drop estimates are approximate when coolant
temperature differs materially from the nominal point.

## Cold Plate

The default geometry is a simplified rectangular-channel cold plate. It is not
a vendor plate design. Geometry inputs control channel count, channel width,
channel height, channel length, base thickness, contact area, and copper
conductivity.

The model assumes uniform flow across channels and a single effective contact
area. It does not model local maldistribution, detailed fin geometry, 2D
spreading, fouling, or manufacturing variation.

## Heat Load And Package Resistance

Heat load is a steady-state chip power input. `R_jc` and `R_tim` are explicit
inputs with H100-like defaults. For chips where vendors do not publish package
thermal resistance or junction limits, examples label values as estimates or
proxies.

## Rack

Rack analysis assumes identical GPUs and identical cold plates. Series topology
uses one loop through all GPUs. Parallel topology splits flow evenly across all
GPUs. Manifold and header losses are excluded by design.

## Validation Boundary

Tests include behavioral checks and independent hand-calculation validation for
core equations. The model is checked against public power-and-thermal design
envelopes, not proprietary measurements.
