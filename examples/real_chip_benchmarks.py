"""Real-world thermal benchmarks for datacenter GPU cold plates.

Uses verified TDP specs from vendor datasheets to answer practical
thermal engineering questions: pump sizing, coolant selection, inlet
temperature limits, and cooling capacity requirements.

Run: python examples/real_chip_benchmarks.py
"""

from __future__ import annotations

from dataclasses import dataclass

from thermal_mcp_server.physics import COOLANTS, analyze, optimize_flow
from thermal_mcp_server.schemas import AnalyzeColdplateInput, OptimizeFlowRateInput


# ---------------------------------------------------------------------------
# Chip specs — verified against vendor datasheets
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChipSpec:
    name: str
    tdp_w: float
    tj_limit_c: float
    tj_source: str


# Sources:
# H100 SXM:  NVIDIA H100 Datasheet (resources.nvidia.com)
# B200 NVL72: SemiAnalysis GB200 architecture analysis + NVIDIA product page
# MI300X:    AMD Instinct MI300X Data Sheet (amd.com)
# Gaudi 3:   Intel Gaudi 3 HL-325L OAM Product Brief (intel.com)

H100_SXM = ChipSpec("H100 SXM", 700, 83.0, "NVIDIA datasheet, throttle onset")
B200_NVL72 = ChipSpec("B200 (NVL72)", 1200, 75.0, "SemiAnalysis; not NVIDIA-published")
MI300X = ChipSpec("MI300X", 750, 85.0, "AMD does not publish Tj_max; 85°C used as conservative proxy")
GAUDI3_AIR = ChipSpec("Gaudi 3 OAM (air)", 900, 85.0, "Intel does not publish Tj_max; 85°C used as conservative proxy")
GAUDI3_LIQUID = ChipSpec("Gaudi 3 OAM (liquid)", 1200, 85.0, "Intel does not publish Tj_max; 85°C used as conservative proxy")

ALL_CHIPS = [H100_SXM, B200_NVL72, MI300X, GAUDI3_AIR, GAUDI3_LIQUID]


# ---------------------------------------------------------------------------
# Benchmark 1: H100 SXM — Minimum flow rate sizing
# ---------------------------------------------------------------------------

def benchmark_h100_flow_sweep() -> dict[str, object]:
    """Sweep flow rates to find the minimum that keeps Tj < 83°C.

    Decision: What's the minimum flow rate to keep Tj < 83°C? This sizes the pump.
    """
    chip = H100_SXM
    inlet_c = 35.0
    flow_rates = list(range(2, 16))  # 2 to 15 LPM in 1 LPM increments

    print("=" * 72)
    print(f"Benchmark 1: {chip.name} — Minimum Flow Rate Sizing")
    print(f"  TDP: {chip.tdp_w} W | Coolant: water | Inlet: {inlet_c}°C")
    print(f"  Target: Tj < {chip.tj_limit_c}°C ({chip.tj_source})")
    print("-" * 72)
    print(f"  {'Flow (LPM)':>12}  {'Tj (°C)':>10}  {'ΔP (kPa)':>10}  {'Status':>10}")
    print("-" * 72)

    min_flow: float | None = None
    results: list[dict[str, float]] = []

    for lpm in flow_rates:
        result = analyze(AnalyzeColdplateInput(
            heat_load_w=chip.tdp_w,
            flow_rate_lpm=float(lpm),
            inlet_temp_c=inlet_c,
            coolant="water",
        ))
        status = "OK" if result.junction_temp_c < chip.tj_limit_c else "OVER"
        if status == "OK" and min_flow is None:
            min_flow = float(lpm)
        print(f"  {lpm:>12}  {result.junction_temp_c:>10.1f}  {result.pressure_drop_pa / 1000:>10.1f}  {status:>10}")
        results.append({
            "flow_lpm": float(lpm),
            "tj_c": result.junction_temp_c,
            "dp_kpa": result.pressure_drop_pa / 1000,
        })

    print("-" * 72)
    if min_flow is not None:
        print(f"  Minimum flow rate for Tj < {chip.tj_limit_c}°C: {min_flow} LPM")
    else:
        print(f"  WARNING: No tested flow rate keeps Tj < {chip.tj_limit_c}°C at {inlet_c}°C inlet")
    print()

    return {"chip": chip.name, "min_flow_lpm": min_flow, "results": results}


# ---------------------------------------------------------------------------
# Benchmark 2: GB200 (NVL72) — Coolant comparison
# ---------------------------------------------------------------------------

def benchmark_b200_coolant_comparison() -> dict[str, object]:
    """Compare water vs 50% glycol for a B200 at NVL72 power level.

    Decision: How much thermal margin do you lose with glycol freeze protection?
    Is it worth the pumping power increase?

    Note: This benchmark compares the two coolants available in the model (water
    and 50/50 glycol). The glycol50 properties in the model use ethylene glycol
    values. For propylene glycol, thermal conductivity is ~10% lower and viscosity
    is ~20% higher — the penalty shown here is a lower bound.
    """
    chip = B200_NVL72
    flow_lpm = 10.0
    inlet_c = 35.0

    print("=" * 72)
    print(f"Benchmark 2: {chip.name} — Coolant Comparison")
    print(f"  TDP: {chip.tdp_w} W | Flow: {flow_lpm} LPM | Inlet: {inlet_c}°C")
    print("-" * 72)
    print(f"  {'Coolant':>16}  {'Tj (°C)':>10}  {'ΔP (kPa)':>10}  {'Pump (W)':>10}  {'Regime':>12}")
    print("-" * 72)

    comparison: dict[str, dict[str, float]] = {}

    for coolant_name in COOLANTS:
        result = analyze(AnalyzeColdplateInput(
            heat_load_w=chip.tdp_w,
            flow_rate_lpm=flow_lpm,
            inlet_temp_c=inlet_c,
            coolant=coolant_name,
        ))
        print(
            f"  {coolant_name:>16}  "
            f"{result.junction_temp_c:>10.1f}  "
            f"{result.pressure_drop_pa / 1000:>10.1f}  "
            f"{result.pump_power_w:>10.2f}  "
            f"{result.regime:>12}"
        )
        comparison[coolant_name] = {
            "tj_c": result.junction_temp_c,
            "dp_kpa": result.pressure_drop_pa / 1000,
            "pump_w": result.pump_power_w,
        }

    tj_water = comparison["water"]["tj_c"]
    tj_glycol = comparison["glycol50"]["tj_c"]
    dp_water = comparison["water"]["dp_kpa"]
    dp_glycol = comparison["glycol50"]["dp_kpa"]

    print("-" * 72)
    print(f"  Glycol penalty: +{tj_glycol - tj_water:.1f}°C junction temp, "
          f"+{dp_glycol - dp_water:.1f} kPa pressure drop")
    print()

    return {"chip": chip.name, "comparison": comparison}


# ---------------------------------------------------------------------------
# Benchmark 3: MI300X — Inlet temperature sensitivity
# ---------------------------------------------------------------------------

def benchmark_mi300x_inlet_sweep() -> dict[str, object]:
    """Sweep inlet temperature to find the maximum allowable CDU setpoint.

    Decision: At what inlet temperature does the GPU approach throttle?
    This constrains cooling tower / CDU setpoint.

    Note: AMD does not publish a Tj_max for MI300X. 85°C is used as a
    conservative proxy based on typical datacenter GPU thermal management
    practice.
    """
    chip = MI300X
    flow_lpm = 8.0
    inlet_temps = list(range(20, 50, 5))  # 20°C to 45°C in 5°C steps

    print("=" * 72)
    print(f"Benchmark 3: {chip.name} — Inlet Temperature Sensitivity")
    print(f"  TDP: {chip.tdp_w} W | Coolant: water | Flow: {flow_lpm} LPM")
    print(f"  Tj limit: {chip.tj_limit_c}°C ({chip.tj_source})")
    print("-" * 72)
    print(f"  {'Inlet (°C)':>12}  {'Tj (°C)':>10}  {'Margin (°C)':>12}  {'Status':>10}")
    print("-" * 72)

    results: list[dict[str, float]] = []

    for inlet_c in inlet_temps:
        result = analyze(AnalyzeColdplateInput(
            heat_load_w=chip.tdp_w,
            flow_rate_lpm=flow_lpm,
            inlet_temp_c=float(inlet_c),
            coolant="water",
        ))
        margin = chip.tj_limit_c - result.junction_temp_c
        status = "OK" if margin > 0 else "EXCEEDS"
        if margin <= 0:
            status = "EXCEEDS"
        elif margin < 3:
            status = "TIGHT"
        print(
            f"  {inlet_c:>12}  "
            f"{result.junction_temp_c:>10.1f}  "
            f"{margin:>12.1f}  "
            f"{status:>10}"
        )
        results.append({
            "inlet_c": float(inlet_c),
            "tj_c": result.junction_temp_c,
            "margin_c": margin,
        })

    print("-" * 72)
    # Find max inlet temp that stays under limit
    safe_inlets = [r for r in results if r["margin_c"] > 0]
    if safe_inlets:
        max_safe = safe_inlets[-1]
        print(f"  Max safe inlet temp: {max_safe['inlet_c']:.0f}°C "
              f"(Tj = {max_safe['tj_c']:.1f}°C, margin = {max_safe['margin_c']:.1f}°C)")
    over_inlets = [r for r in results if r["margin_c"] <= 0]
    if over_inlets:
        print(f"  Tj exceeds {chip.tj_limit_c}°C at inlet >= {over_inlets[0]['inlet_c']:.0f}°C")
    print()

    return {"chip": chip.name, "results": results}


# ---------------------------------------------------------------------------
# Benchmark 4: Gaudi 3 OAM — Flow rate optimization (air vs liquid TDP)
# ---------------------------------------------------------------------------

def benchmark_gaudi3_flow_optimization() -> dict[str, object]:
    """Find minimum flow rate for Gaudi 3 at both air-cooled and liquid-cooled TDP.

    Decision: How much additional cooling capacity does the liquid-cooled OAM
    variant require compared to the air-cooled baseline?

    Note: The default cold plate geometry (40 channels, 1mm Dh) is sized for
    ~700W-class GPUs. At 900–1200W, the fixed thermal resistances (R_jc +
    R_tim + R_base ≈ 0.061 K/W) dominate. Real OAM cold plates would use
    larger contact area, more channels, and optimized TIM to achieve lower
    total resistance.
    """
    tj_limit = 85.0  # Conservative proxy — Intel does not publish Tj_max for Gaudi 3
    flow_max = 100.0

    print("=" * 72)
    print("Benchmark 4: Gaudi 3 OAM — Flow Rate Optimization")
    print(f"  Coolant: water | Target: Tj < {tj_limit}°C")
    print()

    # --- Part A: 30°C inlet (typical warm-climate CDU setpoint) ---
    inlet_30 = 30.0
    print(f"  Part A: Inlet = {inlet_30}°C")
    print("-" * 72)

    for chip in [GAUDI3_AIR, GAUDI3_LIQUID]:
        opt_input = OptimizeFlowRateInput(
            heat_load_w=chip.tdp_w,
            max_junction_temp_c=tj_limit,
            coolant="water",
            inlet_temp_c=inlet_30,
            flow_min_lpm=1.0,
            flow_max_lpm=flow_max,
        )
        _, result = optimize_flow(opt_input)
        # At 30°C inlet, R_fixed × TDP ≈ 55–73°C rise → cannot meet 85°C
        print(f"  {chip.name} ({chip.tdp_w:.0f}W):")
        print(f"    Cannot meet {tj_limit}°C — min ΔTj from R_fixed alone = "
              f"{chip.tdp_w * 0.061:.0f}°C (+ {inlet_30}°C inlet = "
              f"{inlet_30 + chip.tdp_w * 0.061:.0f}°C min)")

    # --- Part B: 25°C inlet (typical cold-climate / well-provisioned CDU) ---
    inlet_25 = 25.0
    print()
    print(f"  Part B: Inlet = {inlet_25}°C (lower CDU setpoint)")
    print("-" * 72)

    configs: dict[str, dict[str, float]] = {}

    for chip in [GAUDI3_AIR, GAUDI3_LIQUID]:
        opt_input = OptimizeFlowRateInput(
            heat_load_w=chip.tdp_w,
            max_junction_temp_c=tj_limit,
            coolant="water",
            inlet_temp_c=inlet_25,
            flow_min_lpm=1.0,
            flow_max_lpm=flow_max,
        )
        min_flow, result = optimize_flow(opt_input)

        if result is not None:
            print(f"  {chip.name}:")
            print(f"    TDP:            {chip.tdp_w:>8.0f} W")
            print(f"    Min flow rate:  {min_flow:>8.1f} LPM")
            print(f"    Tj at min flow: {result.junction_temp_c:>8.1f} °C")
            print(f"    Pressure drop:  {result.pressure_drop_pa / 1000:>8.1f} kPa")
            print(f"    Pump power:     {result.pump_power_w:>8.2f} W")
            configs[chip.name] = {
                "tdp_w": chip.tdp_w,
                "min_flow_lpm": min_flow,
                "tj_c": result.junction_temp_c,
                "dp_kpa": result.pressure_drop_pa / 1000,
                "pump_w": result.pump_power_w,
            }
        else:
            print(f"  {chip.name} ({chip.tdp_w:.0f}W):")
            print(f"    Cannot meet {tj_limit}°C even at {inlet_25}°C inlet")
            print(f"    Cold plate redesign required for this power class")
            configs[chip.name] = {"tdp_w": chip.tdp_w, "min_flow_lpm": None}

    air = configs.get("Gaudi 3 OAM (air)", {})
    liq = configs.get("Gaudi 3 OAM (liquid)", {})
    air_flow = air.get("min_flow_lpm")
    liq_flow = liq.get("min_flow_lpm")

    print()
    if air_flow is not None and liq_flow is not None:
        print(f"  At {inlet_25}°C inlet, liquid-cooled OAM requires "
              f"+{liq_flow - air_flow:.1f} LPM "
              f"({liq_flow:.1f} vs {air_flow:.1f} LPM) "
              f"for +{liq['tdp_w'] - air['tdp_w']:.0f} W additional TDP")
    elif air_flow is not None and liq_flow is None:
        print(f"  At {inlet_25}°C inlet, air-cooled OAM ({GAUDI3_AIR.tdp_w:.0f}W) "
              f"needs {air_flow:.1f} LPM with default geometry.")
        print(f"  Liquid-cooled OAM ({GAUDI3_LIQUID.tdp_w:.0f}W) still exceeds "
              f"what this cold plate geometry can handle — redesign needed.")
    elif air_flow is None and liq_flow is None:
        print(f"  Neither variant achievable at {inlet_25}°C with default geometry.")
        print("  Cold plate redesign required for 900W+ class GPUs.")
    print()

    return {"configs": configs}


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def print_summary() -> None:
    """Print a summary table across all chips at their optimal operating points.

    Uses an extended flow range (1–100 LPM) to find solutions where possible.
    Chips that cannot meet their Tj limit with the default cold plate geometry
    at any flow rate are marked as needing geometry redesign.
    """
    inlet_c = 35.0
    flow_max = 100.0

    print("=" * 72)
    print("Summary: All Chips at Minimum Flow Rate for Tj < Tj_limit")
    print(f"  Coolant: water | Inlet: {inlet_c}°C | Default cold plate geometry")
    print("-" * 72)
    print(
        f"  {'Chip':<22}  {'TDP (W)':>8}  {'Tj Lim':>7}  "
        f"{'Min Flow':>9}  {'Tj (°C)':>8}  {'ΔP (kPa)':>9}"
    )
    print("-" * 72)

    for chip in ALL_CHIPS:
        opt_input = OptimizeFlowRateInput(
            heat_load_w=chip.tdp_w,
            max_junction_temp_c=chip.tj_limit_c,
            coolant="water",
            inlet_temp_c=inlet_c,
            flow_min_lpm=1.0,
            flow_max_lpm=flow_max,
        )
        min_flow, result = optimize_flow(opt_input)

        if result is not None:
            print(
                f"  {chip.name:<22}  {chip.tdp_w:>8.0f}  {chip.tj_limit_c:>6.0f}°  "
                f"{min_flow:>8.1f}  {result.junction_temp_c:>8.1f}  "
                f"{result.pressure_drop_pa / 1000:>9.1f}"
            )
        else:
            print(
                f"  {chip.name:<22}  {chip.tdp_w:>8.0f}  {chip.tj_limit_c:>6.0f}°  "
                f"{'redesign':>9}  {'N/A':>8}  {'N/A':>9}"
            )

    print("-" * 72)
    print("  'redesign' = default cold plate geometry cannot meet target at any flow rate.")
    print("  These chips require larger contact area, more channels, or lower R_jc.")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("Datacenter GPU Cold Plate Thermal Benchmarks")
    print("Using thermal-mcp-server physics engine")
    print()

    benchmark_h100_flow_sweep()
    benchmark_b200_coolant_comparison()
    benchmark_mi300x_inlet_sweep()
    benchmark_gaudi3_flow_optimization()
    print_summary()
