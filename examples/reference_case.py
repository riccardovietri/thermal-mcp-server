"""Reference case: the public chips at a realistic flow per kW.

For each chip in ``ALL_CHIPS`` (examples/real_chip_benchmarks.py), water at 35 °C
inlet with the default package resistances (R_jc 0.04 K/W, R_tim 0.02 K/W), three
configurations are evaluated:

- A: default plate, 8 LPM (the repo's historical default operating point).
- B: default plate, 1.5 LPM per kW of TDP.
- C: reference straight-fin plate, 1.5 LPM per kW of TDP.

It also searches the minimum flow that meets each chip's limit (margin 0, search
0.2 to 30 LPM) on both plates.

The default package (R_jc + R_tim = 60 mK/W) is a generic conservative case.
For the chips whose die area is known (H100, and the Blackwell GPU with an
order-of-magnitude footprint), configuration C is also evaluated with a package
band estimated from die area and published interface data
(docs/research/package-resistance-review.md, sections Q1 and Q2): bare die and
lidded builds, each at a low and a high end. That estimate is 1D conduction over
the die area with uniform power and no hotspot factor; no vendor publishes
junction-to-case resistance for these parts, and whether they are lidded is not
known. It is low confidence on values.

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

from real_chip_benchmarks import ALL_CHIPS, B200_NVL72, H100_SXM

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

# ---------------------------------------------------------------------------
# Package band, estimated from die area (examples only; src/ defaults unchanged).
# Source tags (S4, S13, ...) refer to docs/research/package-resistance-review.md.
# Area-specific interface values are in K·cm²/W and converted to K·m²/W.
# ---------------------------------------------------------------------------
CM2 = 1.0e-4  # m² per cm²

# Silicon at 350 K: 1.5 (350/300)^(-4/3) W/cm·K = 122 W/m·K (S16, derived).
SILICON_K_W_MK = 122.0
# Die thickness 0.5 to 0.8 mm: assumption, no source found.
DIE_THICKNESS_M = {"low": 0.5e-3, "high": 0.8e-3}
# TIM1, reflowed indium (lidded only): 0.2 mm / 86 W/m·K = 0.023 K·cm²/W (S18, derived)
# to < 0.05 K·cm²/W for the solder class (S15).
TIM1_K_M2_PER_W = {"low": 0.023 * CM2, "high": 0.05 * CM2}
# Copper lid (lidded only): 1.5 to 3 mm, assumption, no source found; k = repo copper_k.
LID_THICKNESS_M = {"low": 1.5e-3, "high": 3.0e-3}
LID_K_W_MK = 385.0
# TIM2: phase-change pad 0.04 K·cm²/W (S31) to optimized grease 0.12 K·cm²/W (S14).
TIM2_K_M2_PER_W = {"low": 0.04 * CM2, "high": 0.12 * CM2}

# Die areas. H100: GH100 die, 814 mm² (S4, NVIDIA). Blackwell GPU: 60 × 26 mm heater
# footprint from a published test-vehicle paper (S13, InterPACK 2025); an
# order-of-magnitude footprint for two reticle-sized dies, not a measured die area.
DIE_AREA_M2 = {
    H100_SXM.name: 8.14 * CM2,
    B200_NVL72.name: 15.6 * CM2,
}
DIE_AREA_NOTE = {
    H100_SXM.name: "GH100 die area, NVIDIA",
    B200_NVL72.name: "order-of-magnitude footprint from a published test-vehicle paper, not a measured die area",
}
# Chips left on the generic package because no die area was found.
GENERIC_ONLY_NOTE = "die area not published"

BUILDS = (("bare die", "low"), ("bare die", "high"), ("lidded", "low"), ("lidded", "high"))


def package_resistances(die_area_m2: float, build: str, end: str) -> tuple[float, float]:
    """Return ``(r_jc_k_per_w, r_tim_k_per_w)`` for a die area, a build and a band end.

    1D conduction over the die area, uniform power, no hotspot factor.
    Bare die: R_jc = die conduction; R_tim = TIM2.
    Lidded: R_jc = die conduction + TIM1 + copper lid; R_tim = TIM2.
    ``build`` is ``"bare die"`` or ``"lidded"``; ``end`` is ``"low"`` or ``"high"``.
    """
    if build not in ("bare die", "lidded") or end not in ("low", "high"):
        raise ValueError(f"unknown build or end: {build!r}, {end!r}")
    r_jc = DIE_THICKNESS_M[end] / (SILICON_K_W_MK * die_area_m2)
    if build == "lidded":
        r_jc += TIM1_K_M2_PER_W[end] / die_area_m2
        r_jc += LID_THICKNESS_M[end] / (LID_K_W_MK * die_area_m2)
    r_tim = TIM2_K_M2_PER_W[end] / die_area_m2
    return r_jc, r_tim


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

    ``package_band``: configuration C for each chip in ``DIE_AREA_M2``, one dict
    per build (bare die and lidded, low and high, from ``package_resistances``)
    plus the generic 60 mK/W case, with R_jc, R_tim (K/W), junction temperature
    and margin.
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
    return {"points": points, "min_flow": min_flow, "package_band": _package_band()}


def _package_band() -> list[dict[str, Any]]:
    band: list[dict[str, Any]] = []
    for chip in ALL_CHIPS:
        if chip.name not in DIE_AREA_M2:
            continue
        area = DIE_AREA_M2[chip.name]
        flow = FLOW_PER_KW_LPM * chip.tdp_w / 1000.0
        generic = AnalyzeColdplateInput(heat_load_w=chip.tdp_w)
        cases: list[tuple[str, str | None, float, float]] = [(build, end, *package_resistances(area, build, end)) for build, end in BUILDS]
        cases.append(("generic", None, generic.r_jc_k_per_w, generic.r_tim_k_per_w))
        for build, end, r_jc, r_tim in cases:
            result = analyze(
                AnalyzeColdplateInput(
                    heat_load_w=chip.tdp_w,
                    flow_rate_lpm=flow,
                    inlet_temp_c=INLET_C,
                    coolant=COOLANT,
                    r_jc_k_per_w=r_jc,
                    r_tim_k_per_w=r_tim,
                    geometry=REFERENCE_PLATE,
                )
            )
            band.append(
                {
                    "chip": chip.name,
                    "tdp_w": chip.tdp_w,
                    "tj_limit_c": chip.tj_limit_c,
                    "die_area_m2": area,
                    "config": "C",
                    "build": build,
                    "end": end,
                    "flow_lpm": flow,
                    "r_jc_k_per_w": r_jc,
                    "r_tim_k_per_w": r_tim,
                    "tj_c": result.junction_temp_c,
                    "margin_c": chip.tj_limit_c - result.junction_temp_c,
                    "resistances_k_per_w": dict(result.resistances_k_per_w),
                }
            )
    return band


def main() -> None:
    data = reference_case()
    rule = "-" * 109
    print("Reference case: water, 35 °C inlet, R_jc 0.04 K/W, R_tim 0.02 K/W, properties fixed at 25 °C")
    print("  A: default plate, 8 LPM | B: default plate, 1.5 LPM/kW | C: reference straight-fin plate, 1.5 LPM/kW")
    print("  Package in A, B, C: generic 60 mK/W (R_jc + R_tim), a conservative case, not a vendor value")
    print(rule)
    print(f"  {'Chip':<27} {'Cfg':>3} {'Flow (LPM)':>10} {'Tj (°C)':>8} {'Margin (°C)':>11} {'ΔP (kPa)':>9} {'Pump (W)':>9} {'Re':>6}  {'Regime':<12}")
    print(rule)
    for p in data["points"]:
        print(
            f"  {p['chip']:<27} {p['config']:>3} {p['flow_lpm']:>10.2f} {p['tj_c']:>8.1f} {p['margin_c']:>11.1f} "
            f"{p['dp_kpa']:>9.2f} {p['pump_w']:>9.3f} {p['reynolds']:>6.0f}  {p['regime']:<12}"
        )
    print(rule)
    print()
    print(f"Minimum flow to meet the chip limit (margin 0, search {SEARCH_MIN_LPM:g} to {SEARCH_MAX_LPM:g} LPM)")
    print(rule)
    print(f"  {'Chip':<27} {'Plate':<10} {'Min flow (LPM)':>14} {'ΔP (kPa)':>9}  {'Regime':<12}")
    print(rule)
    for m in data["min_flow"]:
        if m["min_flow_lpm"] is None:
            print(f"  {m['chip']:<27} {m['plate']:<10} no passing point in {SEARCH_MIN_LPM:g} to {SEARCH_MAX_LPM:g} LPM")
        else:
            print(f"  {m['chip']:<27} {m['plate']:<10} {m['min_flow_lpm']:>14.3f} {m['dp_kpa']:>9.2f}  {m['regime']:<12}")
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
    print()
    print_package_band(data["package_band"], rule)


def print_package_band(band: list[dict[str, Any]], rule: str) -> None:
    print("Package band, configuration C (straight-fin plate, 1.5 LPM/kW, 35 °C inlet)")
    print("  Estimated from die area and published interface data; low confidence on values.")
    print("  1D conduction over the die area, uniform power, no hotspot factor. No vendor publishes")
    print("  junction-to-case resistance for these parts, and whether they are lidded is not known.")
    print("  Die and lid thickness are assumptions. Generic = the 60 mK/W conservative case above.")
    for chip, note in DIE_AREA_NOTE.items():
        print(f"  {chip}: die area {DIE_AREA_M2[chip] / CM2:.2f} cm² ({note})")
    shown = set(DIE_AREA_M2)
    for chip in ALL_CHIPS:
        if chip.name not in shown:
            print(f"  {chip.name}: generic package only ({GENERIC_ONLY_NOTE})")
    print(rule)
    print(f"  {'Chip':<27} {'Build':<16} {'R_jc (mK/W)':>11} {'R_tim (mK/W)':>12} {'Sum (mK/W)':>10} {'Tj (°C)':>8} {'Margin (°C)':>11}")
    print(rule)
    for b in band:
        build = "generic 60 mK/W" if b["end"] is None else f"{b['build']}, {b['end']}"
        r_jc, r_tim = b["r_jc_k_per_w"] * 1000.0, b["r_tim_k_per_w"] * 1000.0
        print(f"  {b['chip']:<27} {build:<16} {r_jc:>11.3f} {r_tim:>12.3f} {r_jc + r_tim:>10.3f} {b['tj_c']:>8.2f} {b['margin_c']:>11.2f}")
    print(rule)


if __name__ == "__main__":
    main()
