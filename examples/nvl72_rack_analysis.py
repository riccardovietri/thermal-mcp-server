"""NVIDIA NVL72 Rack Thermal Analysis — CDU Specification Guide.

The NVL72 (72× B200 GPUs per rack) is the flagship AI training system.
At 86.4 kW rack TDP, it is the most thermally demanding GPU deployment
in production today. This example answers the procurement question:

    "What CDU do I need to cool a B200 NVL72 rack?"

Outputs CDU spec (flow rate, heat rejection, max ΔP) as a function of
CDU supply temperature — the primary variable operators can control.

Run: python examples/nvl72_rack_analysis.py

Thermal assumptions (B200-specific, documented per CLAUDE.md protocol):
  - R_jc = 0.02 K/W: B200 SXM uses a larger, more optimised package than
    H100 SXM (R_jc 0.04 K/W). 0.02 K/W is an engineering estimate; NVIDIA
    does not publish this value. Treat as indicative.
  - R_tim = 0.015 K/W: slightly better TIM assumed for high-TDP package.
  - Cold plate geometry: 60 channels × 0.7 mm × 1.5 mm, 100 mm long,
    1.5 mm base, 160 cm² contact area. This is a high-performance cold plate
    sized for B200 TDP — not the H100 default geometry.
  - Tj limit: 75°C throttle onset per SemiAnalysis estimate. NVIDIA does not
    publish Tj_max for B200.
"""

from __future__ import annotations

from thermal_mcp_server.physics import analyze_rack, optimize_flow
from thermal_mcp_server.schemas import (
    AnalyzeRackInput,
    Geometry,
    OptimizeFlowRateInput,
)


# ---------------------------------------------------------------------------
# B200 parameters
# ---------------------------------------------------------------------------

B200_TDP_W = 1200.0
B200_TJ_LIMIT_C = 75.0      # SemiAnalysis estimate; not NVIDIA-published
B200_R_JC = 0.02             # K/W — engineering estimate; see module docstring
B200_R_TIM = 0.015           # K/W — better TIM assumed for high-TDP package
NVL72_GPU_COUNT = 72

# High-performance cold plate geometry for B200 TDP
# 60 × 0.7 mm × 1.5 mm channels, 100 mm long, 160 cm² contact area
B200_COLD_PLATE = Geometry(
    channel_count=60,
    channel_width_m=0.7e-3,
    channel_height_m=1.5e-3,
    channel_length_m=0.10,
    base_thickness_m=1.5e-3,
    contact_area_m2=0.016,
    copper_k_w_mk=385.0,
)


# ---------------------------------------------------------------------------
# Section 1: Single cold plate — flow sizing
# ---------------------------------------------------------------------------

def section_single_plate_sizing() -> dict[str, float]:
    """Find minimum flow per cold plate for Tj < 75°C at various inlet temps."""
    print("=" * 72)
    print("Section 1: Single B200 Cold Plate — Minimum Flow Rate Sizing")
    print(f"  TDP: {B200_TDP_W} W | Coolant: water | Tj limit: {B200_TJ_LIMIT_C}°C")
    print(f"  R_jc: {B200_R_JC} K/W (est.) | R_tim: {B200_R_TIM} K/W")
    print("-" * 72)
    print(f"  {'Inlet (°C)':>10}  {'Min Flow':>10}  {'Tj (°C)':>8}  "
          f"{'Margin':>8}  {'ΔP (kPa)':>9}  {'Regime':>12}")
    print("-" * 72)

    results = {}
    for inlet_c in [20.0, 25.0, 30.0, 35.0, 40.0]:
        opt = OptimizeFlowRateInput(
            heat_load_w=B200_TDP_W,
            max_junction_temp_c=B200_TJ_LIMIT_C,
            inlet_temp_c=inlet_c,
            coolant="water",
            flow_min_lpm=1.0,
            flow_max_lpm=60.0,
            r_jc_k_per_w=B200_R_JC,
            r_tim_k_per_w=B200_R_TIM,
            geometry=B200_COLD_PLATE,
        )
        min_flow, result = optimize_flow(opt)

        if result is not None:
            margin = B200_TJ_LIMIT_C - result.junction_temp_c
            print(f"  {inlet_c:>10.0f}  {min_flow:>9.1f}L  {result.junction_temp_c:>7.1f}  "
                  f"  {margin:>+6.1f}°  {result.pressure_drop_pa / 1000:>9.1f}  {result.regime:>12}")
            results[f"inlet_{int(inlet_c)}c"] = {
                "min_flow_lpm": min_flow,
                "tj_c": result.junction_temp_c,
                "dp_pa": result.pressure_drop_pa,
            }
        else:
            print(f"  {inlet_c:>10.0f}  {'infeasible':>10}  — cold plate cannot meet target —")

    print("-" * 72)
    print("  'Margin' = Tj_limit − Tj. Positive = safe. Negative = throttling.\n")
    return results


# ---------------------------------------------------------------------------
# Section 2: Full NVL72 rack — CDU specification
# ---------------------------------------------------------------------------

def section_nvl72_cdu_spec(single_plate_results: dict[str, float]) -> None:
    """Scale to 72-GPU rack and output CDU procurement spec."""
    print("=" * 72)
    print("Section 2: NVL72 Rack (72× B200) — CDU Specification")
    print(f"  Total TDP: {NVL72_GPU_COUNT * B200_TDP_W / 1000:.1f} kW "
          f"| Topology: parallel | Coolant: water")
    print("-" * 72)
    print(f"  {'CDU Supply':>10}  {'Flow (LPM)':>11}  {'Heat Rej':>10}  "
          f"{'ΔP (kPa)':>9}  {'CDU Return':>11}  {'Tj (°C)':>8}")
    print("-" * 72)

    cdu_specs = []
    for inlet_c in [20.0, 25.0, 30.0, 35.0, 40.0]:
        key = f"inlet_{int(inlet_c)}c"
        if key not in single_plate_results:
            print(f"  {inlet_c:>10.0f}°C  — infeasible at this supply temperature —")
            continue

        flow_per_gpu = single_plate_results[key]["min_flow_lpm"]
        total_flow = flow_per_gpu * NVL72_GPU_COUNT

        rack = analyze_rack(AnalyzeRackInput(
            gpu_count=NVL72_GPU_COUNT,
            topology="parallel",
            heat_load_per_gpu_w=B200_TDP_W,
            total_flow_lpm=total_flow,
            cdu_supply_temp_c=inlet_c,
            coolant="water",
            r_jc_k_per_w=B200_R_JC,
            r_tim_k_per_w=B200_R_TIM,
            geometry=B200_COLD_PLATE,
        ))

        heat_rejection_kw = rack.total_heat_load_w / 1000
        dp_kpa = rack.total_pressure_drop_pa / 1000
        cdu_specs.append({
            "supply_c": inlet_c,
            "total_flow_lpm": total_flow,
            "heat_rejection_kw": heat_rejection_kw,
            "dp_kpa": dp_kpa,
            "return_c": rack.cdu_outlet_temp_c,
            "max_tj_c": rack.max_junction_temp_c,
        })

        print(f"  {inlet_c:>9.0f}°C  {total_flow:>10.0f}L  {heat_rejection_kw:>8.1f}kW  "
              f"{dp_kpa:>9.1f}  {rack.cdu_outlet_temp_c:>10.1f}°C  {rack.max_junction_temp_c:>7.1f}")

    print("-" * 72)

    # Best-case CDU spec (25°C supply — typical facility chilled water)
    spec_25 = next((s for s in cdu_specs if s["supply_c"] == 25.0), None)
    if spec_25:
        print()
        print("  CDU PROCUREMENT SPEC (25°C facility supply):")
        print(f"    Minimum flow rate:   {spec_25['total_flow_lpm']:.0f} L/min")
        print(f"    Heat rejection:      {spec_25['heat_rejection_kw']:.1f} kW")
        print(f"    Max cold plate ΔP:   {spec_25['dp_kpa']:.1f} kPa "
              f"({spec_25['dp_kpa'] / 100:.2f} bar)")
        print(f"    CDU return temp:     {spec_25['return_c']:.1f}°C")
        print(f"    Max junction temp:   {spec_25['max_tj_c']:.1f}°C "
              f"({B200_TJ_LIMIT_C - spec_25['max_tj_c']:+.1f}°C margin)")
    print()


# ---------------------------------------------------------------------------
# Section 3: Inlet temperature sensitivity — CDU supply setpoint impact
# ---------------------------------------------------------------------------

def section_inlet_sensitivity() -> None:
    """Show how CDU supply temperature affects junction temperature margin."""
    print("=" * 72)
    print("Section 3: Inlet Temperature Sensitivity at Fixed Flow (20 LPM/GPU)")
    print("  Design question: how much margin does a colder CDU supply buy?")
    print(f"  Fixed: 20 LPM/GPU × {NVL72_GPU_COUNT} GPUs = "
          f"{20 * NVL72_GPU_COUNT} LPM total")
    print("-" * 72)
    print(f"  {'CDU Supply':>10}  {'Max Tj':>8}  {'Tj Margin':>10}  "
          f"{'CDU Return':>11}  {'Status':>12}")
    print("-" * 72)

    flow_per_gpu = 20.0  # LPM — fixed for this sweep
    for inlet_c in [15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0]:
        rack = analyze_rack(AnalyzeRackInput(
            gpu_count=NVL72_GPU_COUNT,
            topology="parallel",
            heat_load_per_gpu_w=B200_TDP_W,
            total_flow_lpm=flow_per_gpu * NVL72_GPU_COUNT,
            cdu_supply_temp_c=inlet_c,
            coolant="water",
            r_jc_k_per_w=B200_R_JC,
            r_tim_k_per_w=B200_R_TIM,
            geometry=B200_COLD_PLATE,
        ))

        margin = B200_TJ_LIMIT_C - rack.max_junction_temp_c
        status = "OK" if margin >= 3 else ("WARNING <3°C" if margin >= 0 else "THROTTLING")
        print(f"  {inlet_c:>9.0f}°C  {rack.max_junction_temp_c:>7.1f}  "
              f"  {margin:>+8.1f}°  {rack.cdu_outlet_temp_c:>10.1f}°C  {status:>12}")

    print("-" * 72)
    print("  3°C margin is a common engineering design target (guard against TIM aging).")
    print("  WARNING: <3°C margin leaves no headroom for R_tim degradation over time.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("  NVIDIA NVL72 RACK THERMAL ANALYSIS")
    print("  72× B200 GPUs | 86.4 kW total TDP | Direct liquid cooling")
    print()
    print("  NOTE: B200 R_jc = 0.02 K/W is an engineering estimate.")
    print("  NVIDIA does not publish this value. Tj limit (75°C) is a")
    print("  SemiAnalysis estimate, not an NVIDIA-published specification.")
    print()

    single_results = section_single_plate_sizing()
    section_nvl72_cdu_spec(single_results)
    section_inlet_sensitivity()
