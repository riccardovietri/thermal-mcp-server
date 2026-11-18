"""Reference case: the public chips at a realistic flow per kW.

For each chip in ``ALL_CHIPS`` (examples/real_chip_benchmarks.py), water at 35 °C
inlet with the default package resistances (R_jc 0.04 K/W, R_tim 0.02 K/W), three
configurations are evaluated:

- A: default plate, 8 LPM (the repo's historical default operating point).
- B: default plate, 1.5 LPM per kW of TDP.
- C: reference straight-fin plate, 1.5 LPM per kW of TDP.

It also searches the minimum flow that meets each chip's limit (margin 0, search
0.2 to 30 LPM) on both plates.

The reference straight-fin plate is the screened design from the companion
``thermal-design-loop`` study. Coolant properties are fixed at 25 °C nominal
values (temperature-dependent properties are not yet modeled), so results at
35 °C inlet carry that approximation. These are screening estimates, not
validated predictions. Deterministic and offline.

Run:
    python examples/reference_case.py
"""

from __future__ import annotations

from typing import Any

from real_chip_benchmarks import ALL_CHIPS

from thermal_mcp_server.physics import analyze, optimize_flow
from thermal_mcp_server.schemas import AnalyzeColdplateInput, Geometry, OptimizeFlowRateInput

INLET_C = 35.0
COOLANT = "water"
LEGACY_FLOW_LPM = 8.0
FLOW_PER_KW_LPM = 1.5
SEARCH_MIN_LPM = 0.2
SEARCH_MAX_LPM = 30.0

DEFAULT_PLATE = Geometry()

# Screened straight-fin design from the companion thermal-design-loop study:
# 76 channels, 0.39 mm wide, 0.39 mm fins, 3.75 mm tall, 60 mm long, 2 mm copper base.
# Contact area is the finned footprint, 76 x (0.39 + 0.39) mm x 60 mm.
REFERENCE_PLATE = Geometry(
    channel_model="straight_fin",
    channel_count=76,
    channel_width_m=0.39e-3,
    fin_thickness_m=0.39e-3,
    channel_height_m=3.75e-3,
    channel_length_m=0.06,
    base_thickness_m=2.0e-3,
    copper_k_w_mk=385.0,
    contact_area_m2=76 * 0.78e-3 * 0.06,
)

PLATES = {"default": DEFAULT_PLATE, "reference": REFERENCE_PLATE}


def _configurations(tdp_w: float) -> list[tuple[str, str, float]]:
    reference_flow = FLOW_PER_KW_LPM * tdp_w / 1000.0
    return [
        ("A", "default", LEGACY_FLOW_LPM),
        ("B", "default", reference_flow),
        ("C", "reference", reference_flow),
    ]


def reference_case() -> dict[str, Any]:
    """Return the reference-case results as plain dictionaries.

    ``points``: one dict per chip and configuration (A, B, C) with junction
    temperature, margin to the chip limit, pressure drop, pump power, Reynolds
    number, regime, the resistance stack in K/W and the fin efficiency
    (``None`` on the default plate).

    ``min_flow``: one dict per chip and plate with the minimum passing flow and
    the pressure drop there, or ``None`` for both when no point in the search
    range passes.
    """
    points: list[dict[str, Any]] = []
    min_flow: list[dict[str, Any]] = []
    for chip in ALL_CHIPS:
        for config, plate, flow in _configurations(chip.tdp_w):
            result = analyze(
                AnalyzeColdplateInput(
                    heat_load_w=chip.tdp_w,
                    flow_rate_lpm=flow,
                    inlet_temp_c=INLET_C,
                    coolant=COOLANT,
                    geometry=PLATES[plate],
                )
            )
            points.append(
                {
                    "chip": chip.name,
                    "tdp_w": chip.tdp_w,
                    "tj_limit_c": chip.tj_limit_c,
                    "config": config,
                    "plate": plate,
                    "flow_lpm": flow,
                    "tj_c": result.junction_temp_c,
                    "margin_c": chip.tj_limit_c - result.junction_temp_c,
                    "dp_kpa": result.pressure_drop_pa / 1000.0,
                    "pump_w": result.pump_power_w,
                    "reynolds": result.reynolds,
                    "regime": result.regime,
                    "resistances_k_per_w": dict(result.resistances_k_per_w),
                    "fin_efficiency": result.fin_efficiency,
                }
            )
        for plate, geometry in PLATES.items():
            flow, best = optimize_flow(
                OptimizeFlowRateInput(
                    heat_load_w=chip.tdp_w,
                    max_junction_temp_c=chip.tj_limit_c,
                    margin_c=0.0,
                    inlet_temp_c=INLET_C,
                    coolant=COOLANT,
                    flow_min_lpm=SEARCH_MIN_LPM,
                    flow_max_lpm=SEARCH_MAX_LPM,
                    geometry=geometry,
                )
            )
            min_flow.append(
                {
                    "chip": chip.name,
                    "plate": plate,
                    "min_flow_lpm": flow if best is not None else None,
                    "dp_kpa": best.pressure_drop_pa / 1000.0 if best is not None else None,
                    "regime": best.regime if best is not None else None,
                }
            )
    return {"points": points, "min_flow": min_flow}


def main() -> None:
    data = reference_case()
    rule = "-" * 104
    print("Reference case: water, 35 °C inlet, R_jc 0.04 K/W, R_tim 0.02 K/W, properties fixed at 25 °C")
    print("  A: default plate, 8 LPM | B: default plate, 1.5 LPM/kW | C: reference straight-fin plate, 1.5 LPM/kW")
    print(rule)
    print(f"  {'Chip':<22} {'Cfg':>3} {'Flow (LPM)':>10} {'Tj (°C)':>8} {'Margin (°C)':>11} {'ΔP (kPa)':>9} {'Pump (W)':>9} {'Re':>6}  {'Regime':<12}")
    print(rule)
    for p in data["points"]:
        print(
            f"  {p['chip']:<22} {p['config']:>3} {p['flow_lpm']:>10.2f} {p['tj_c']:>8.1f} {p['margin_c']:>11.1f} "
            f"{p['dp_kpa']:>9.2f} {p['pump_w']:>9.3f} {p['reynolds']:>6.0f}  {p['regime']:<12}"
        )
    print(rule)
    print()
    print(f"Minimum flow to meet the chip limit (margin 0, search {SEARCH_MIN_LPM:g} to {SEARCH_MAX_LPM:g} LPM)")
    print(rule)
    print(f"  {'Chip':<22} {'Plate':<10} {'Min flow (LPM)':>14} {'ΔP (kPa)':>9}  {'Regime':<12}")
    print(rule)
    for m in data["min_flow"]:
        if m["min_flow_lpm"] is None:
            print(f"  {m['chip']:<22} {m['plate']:<10} no passing point in {SEARCH_MIN_LPM:g} to {SEARCH_MAX_LPM:g} LPM")
        else:
            print(f"  {m['chip']:<22} {m['plate']:<10} {m['min_flow_lpm']:>14.3f} {m['dp_kpa']:>9.2f}  {m['regime']:<12}")
    print(rule)
    print()
    print(f"{ALL_CHIPS[0].name} resistance stack (mK/W); package share = (R_jc + R_tim) / total")
    print(rule)
    print(f"  {'Cfg':>3} {'R_jc':>7} {'R_tim':>7} {'base':>7} {'convection':>11} {'total':>8} {'package':>8} {'fin eff.':>9}")
    print(rule)
    for p in data["points"]:
        if p["chip"] == ALL_CHIPS[0].name:
            r = {k: v * 1000.0 for k, v in p["resistances_k_per_w"].items()}
            eta = "-" if p["fin_efficiency"] is None else f"{p['fin_efficiency']:.3f}"
            print(
                f"  {p['config']:>3} {r['junction_to_case']:>7.3f} {r['tim']:>7.3f} {r['base_conduction']:>7.3f} "
                f"{r['convection']:>11.3f} {r['total']:>8.3f} {(r['junction_to_case'] + r['tim']) / r['total']:>8.1%} {eta:>9}"
            )
    print(rule)


if __name__ == "__main__":
    main()
