"""Series vs Parallel Rack Plumbing — Engineering Trade-off Analysis.

Liquid-cooled GPU racks can be plumbed in series (coolant flows through
each cold plate in sequence) or parallel (coolant splits across all cold
plates simultaneously). The choice affects:

  - Max junction temperature: series stacks coolant temperature per GPU;
    parallel keeps every GPU at CDU supply temperature.
  - Pressure drop: series accumulates ΔP across all plates; parallel sees
    only the single-plate ΔP (but needs proportionally more total flow).
  - CDU specification: series needs less total flow but higher ΔP pump;
    parallel needs more flow but lower ΔP.

This example compares both topologies across three representative rack
configurations at equivalent per-GPU flow rates.

Run: python examples/rack_topology_tradeoffs.py
"""

from __future__ import annotations

from dataclasses import dataclass

from thermal_mcp_server.physics import analyze_rack
from thermal_mcp_server.schemas import AnalyzeRackInput


@dataclass(frozen=True)
class RackConfig:
    name: str
    gpu_count: int
    tdp_per_gpu_w: float
    tj_limit_c: float
    flow_per_gpu_lpm: float   # flow rate to compare at (same for both topologies)
    cdu_supply_c: float = 25.0
    coolant: str = "water"


# Three representative rack configurations
CONFIGS = [
    RackConfig(
        name="DGX H100 (8× H100 SXM)",
        gpu_count=8,
        tdp_per_gpu_w=700.0,
        tj_limit_c=83.0,
        flow_per_gpu_lpm=8.0,
    ),
    RackConfig(
        name="HGX H100 (16× H100 SXM)",
        gpu_count=16,
        tdp_per_gpu_w=700.0,
        tj_limit_c=83.0,
        flow_per_gpu_lpm=8.0,
    ),
    RackConfig(
        name="B200 NVL36 (36× B200, half-rack)",
        gpu_count=36,
        tdp_per_gpu_w=1200.0,
        tj_limit_c=75.0,
        flow_per_gpu_lpm=12.0,
        cdu_supply_c=25.0,
    ),
]


def analyze_topology_pair(cfg: RackConfig) -> None:
    """Print side-by-side series vs parallel comparison for one rack config."""
    print("=" * 72)
    print(f"  {cfg.name}")
    print(f"  {cfg.gpu_count} GPUs × {cfg.tdp_per_gpu_w:.0f} W = "
          f"{cfg.gpu_count * cfg.tdp_per_gpu_w / 1000:.1f} kW total | "
          f"CDU supply: {cfg.cdu_supply_c}°C | "
          f"Per-GPU flow: {cfg.flow_per_gpu_lpm} LPM")
    print("-" * 72)

    # Series: same per-GPU flow → total flow = flow_per_gpu
    series = analyze_rack(AnalyzeRackInput(
        gpu_count=cfg.gpu_count,
        topology="series",
        heat_load_per_gpu_w=cfg.tdp_per_gpu_w,
        total_flow_lpm=cfg.flow_per_gpu_lpm,   # each GPU sees full CDU flow
        cdu_supply_temp_c=cfg.cdu_supply_c,
        coolant=cfg.coolant,
    ))

    # Parallel: same per-GPU flow → total flow = N × flow_per_gpu
    parallel = analyze_rack(AnalyzeRackInput(
        gpu_count=cfg.gpu_count,
        topology="parallel",
        heat_load_per_gpu_w=cfg.tdp_per_gpu_w,
        total_flow_lpm=cfg.flow_per_gpu_lpm * cfg.gpu_count,
        cdu_supply_temp_c=cfg.cdu_supply_c,
        coolant=cfg.coolant,
    ))

    # At equivalent per-GPU flow, parallel should give same Tj as series GPU 0
    # (all GPUs see same inlet). Series hottest GPU is GPU[N-1].

    header = f"  {'Metric':<30}  {'Series':>14}  {'Parallel':>14}"
    print(header)
    print("-" * 72)

    def row(label: str, s_val: str, p_val: str, note: str = "") -> None:
        print(f"  {label:<30}  {s_val:>14}  {p_val:>14}  {note}")

    row("Total CDU flow (LPM)",
        f"{cfg.flow_per_gpu_lpm:.1f}",
        f"{cfg.flow_per_gpu_lpm * cfg.gpu_count:.1f}",
        "← series needs N× less flow")

    row("Total ΔP (kPa)",
        f"{series.total_pressure_drop_pa / 1000:.1f}",
        f"{parallel.total_pressure_drop_pa / 1000:.1f}",
        "← series accumulates N× ΔP")

    row("Total pump power (W)",
        f"{series.total_pump_power_w:.1f}",
        f"{parallel.total_pump_power_w:.1f}")

    row("CDU return temp (°C)",
        f"{series.cdu_outlet_temp_c:.1f}",
        f"{parallel.cdu_outlet_temp_c:.1f}")

    row("Max junction temp (°C)",
        f"{series.max_junction_temp_c:.1f}",
        f"{parallel.max_junction_temp_c:.1f}",
        "← parallel wins (no Tj stacking)")

    margin_s = cfg.tj_limit_c - series.max_junction_temp_c
    margin_p = cfg.tj_limit_c - parallel.max_junction_temp_c
    row(f"Tj margin vs {cfg.tj_limit_c:.0f}°C limit",
        f"{margin_s:+.1f}°C",
        f"{margin_p:+.1f}°C")

    row("Hottest GPU index (0-based)",
        f"{series.hottest_gpu_index}",
        f"{parallel.hottest_gpu_index}")

    print("-" * 72)

    # Recommendation
    if margin_s >= 3:
        rec = "Both topologies viable. Series preferred: less CDU flow, simpler manifold."
    elif margin_p >= 3:
        rec = "Parallel required: series temperature stacking exceeds Tj limit."
    else:
        rec = "Both topologies marginal. Increase flow rate or reduce inlet temp."

    print(f"  → {rec}")
    print()


def section_coolant_rise_explanation() -> None:
    """Illustrate the temperature stacking effect in a series chain."""
    print("=" * 72)
    print("  Why Series Stacks Temperature: Per-GPU Tj Breakdown")
    print("  Config: 8× H100 SXM in series, 700W each, 8 LPM, 25°C supply")
    print("-" * 72)
    print(f"  {'GPU':>5}  {'Inlet (°C)':>11}  {'Tj (°C)':>9}  {'ΔTj from prev':>14}")
    print("-" * 72)

    rack = analyze_rack(AnalyzeRackInput(
        gpu_count=8,
        topology="series",
        heat_load_per_gpu_w=700.0,
        total_flow_lpm=8.0,
        cdu_supply_temp_c=25.0,
        coolant="water",
    ))

    tjs = rack.per_gpu_junction_temps_c
    # Reconstruct per-GPU inlets from coolant rise
    from thermal_mcp_server.physics import analyze
    from thermal_mcp_server.schemas import AnalyzeColdplateInput
    ref = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8.0))
    rise = ref.coolant_rise_c

    for i, tj in enumerate(tjs):
        inlet = 25.0 + i * rise
        delta = f"{tj - tjs[i-1]:+.2f}°C" if i > 0 else "—"
        print(f"  {i:>5}  {inlet:>10.2f}  {tj:>9.2f}  {delta:>14}")

    print("-" * 72)
    print(f"  Coolant rise per GPU: {rise:.3f}°C (700W ÷ ṁ·cp)")
    print(f"  Each GPU in series is exactly {rise:.3f}°C hotter than the previous.")
    print(f"  Total CDU temperature rise: {rack.cdu_outlet_temp_c - 25.0:.2f}°C "
          f"({25.0}°C supply → {rack.cdu_outlet_temp_c:.2f}°C return)")
    print()


if __name__ == "__main__":
    print()
    print("  SERIES vs PARALLEL RACK TOPOLOGY — TRADE-OFF ANALYSIS")
    print("  Compared at equivalent per-GPU flow rate for each configuration")
    print()

    for cfg in CONFIGS:
        analyze_topology_pair(cfg)

    section_coolant_rise_explanation()
