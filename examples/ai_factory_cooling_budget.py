"""AI Factory Cooling Budget — From Single GPU to Cluster Scale.

"AI factory" is the term used for large-scale GPU clusters purpose-built
for model training (NVIDIA's term; adopted by hyperscalers and colocation
providers). This example scales the single-cold-plate physics model up to
realistic cluster configurations and estimates operational cooling costs.

Questions answered:
  1. How much cooling infrastructure does each cluster configuration require?
  2. What fraction of total cluster power goes to moving coolant (cooling tax)?
  3. What does the CDU farm look like (count, flow, heat rejection)?
  4. How does electricity cost compare for water vs. glycol50 cooling?

Run: python examples/ai_factory_cooling_budget.py

Financial assumptions (adjust for your facility):
  - Electricity: $0.08/kWh (US data center average, 2025)
  - CDU pump efficiency: 50% (built into physics model)
  - GPU utilization: 75% of TDP nameplate (typical training workload)
  - Hours/year: 8,760 (continuous operation assumed)
"""

from __future__ import annotations

from dataclasses import dataclass

from thermal_mcp_server.physics import analyze_rack
from thermal_mcp_server.schemas import AnalyzeRackInput, Geometry


# ---------------------------------------------------------------------------
# Financial constants
# ---------------------------------------------------------------------------

ELECTRICITY_USD_PER_KWH = 0.08      # $/kWh — US data center average, 2025
GPU_UTILIZATION = 0.75               # fraction of TDP nameplate
HOURS_PER_YEAR = 8_760

# B200-specific high-performance cold plate (from nvl72_rack_analysis.py)
# 60 × 0.7 mm × 1.5 mm channels, 100 mm long, 160 cm² contact area.
# R_jc = 0.02 K/W (engineering estimate; NVIDIA does not publish this value).
B200_COLD_PLATE = Geometry(
    channel_count=60,
    channel_width_m=0.7e-3,
    channel_height_m=1.5e-3,
    channel_length_m=0.10,
    base_thickness_m=1.5e-3,
    contact_area_m2=0.016,
)
B200_R_JC = 0.02   # K/W — see nvl72_rack_analysis.py for full assumptions


# ---------------------------------------------------------------------------
# Cluster configurations
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClusterSpec:
    name: str
    gpu_name: str
    gpu_count_per_rack: int
    rack_count: int
    tdp_per_gpu_w: float
    tj_limit_c: float
    flow_per_gpu_lpm: float
    cdu_supply_c: float = 25.0
    coolant: str = "water"
    r_jc: float = 0.04
    geometry: Geometry | None = None
    note: str = ""


CLUSTERS = [
    ClusterSpec(
        name="H100 Training Cluster (small)",
        gpu_name="H100 SXM",
        gpu_count_per_rack=8,
        rack_count=16,
        tdp_per_gpu_w=700.0,
        tj_limit_c=83.0,
        flow_per_gpu_lpm=8.0,
        note="128 GPUs — typical DGX-scale AI lab",
    ),
    ClusterSpec(
        name="H100 Training Cluster (large)",
        gpu_name="H100 SXM",
        gpu_count_per_rack=8,
        rack_count=256,
        tdp_per_gpu_w=700.0,
        tj_limit_c=83.0,
        flow_per_gpu_lpm=8.0,
        note="2,048 GPUs — hyperscale training cluster",
    ),
    ClusterSpec(
        name="B200 NVL72 Cluster",
        gpu_name="B200",
        gpu_count_per_rack=72,
        rack_count=20,
        tdp_per_gpu_w=1200.0,
        tj_limit_c=75.0,
        flow_per_gpu_lpm=20.0,   # requires high flow for B200 TDP
        cdu_supply_c=25.0,
        r_jc=B200_R_JC,
        geometry=B200_COLD_PLATE,
        note="1,440 GPUs — 86.4 kW/rack, B200-optimised cold plate",
    ),
    ClusterSpec(
        name="MI300X Cluster",
        gpu_name="MI300X",
        gpu_count_per_rack=8,
        rack_count=32,
        tdp_per_gpu_w=750.0,
        tj_limit_c=85.0,
        flow_per_gpu_lpm=8.0,
        note="256 GPUs — AMD-based AI cluster",
    ),
]


# ---------------------------------------------------------------------------
# Section 1: Cooling budget per cluster
# ---------------------------------------------------------------------------

def section_cooling_budget() -> None:
    """Compute total cooling load, pump power, and CDU farm sizing."""
    print("=" * 80)
    print("Section 1: AI Factory Cooling Budget — Cluster Scale")
    print(f"  CDU supply: 25°C | Coolant: water | Flow topology: parallel per rack")
    print("-" * 80)

    for cluster in CLUSTERS:
        total_gpus = cluster.gpu_count_per_rack * cluster.rack_count
        effective_tdp = cluster.tdp_per_gpu_w * GPU_UTILIZATION

        # Analyze one representative rack (all racks identical)
        rack_kwargs: dict = dict(
            gpu_count=cluster.gpu_count_per_rack,
            topology="parallel",
            heat_load_per_gpu_w=effective_tdp,
            total_flow_lpm=cluster.flow_per_gpu_lpm * cluster.gpu_count_per_rack,
            cdu_supply_temp_c=cluster.cdu_supply_c,
            coolant=cluster.coolant,
            r_jc_k_per_w=cluster.r_jc,
        )
        if cluster.geometry is not None:
            rack_kwargs["geometry"] = cluster.geometry
        rack = analyze_rack(AnalyzeRackInput(**rack_kwargs))

        # Scale to full cluster
        total_gpu_power_kw = total_gpus * effective_tdp / 1000
        total_pump_power_kw = rack.total_pump_power_w / 1000 * cluster.rack_count
        total_flow_lpm = cluster.flow_per_gpu_lpm * cluster.gpu_count_per_rack * cluster.rack_count
        cooling_tax_pct = rack.total_pump_power_w / (cluster.gpu_count_per_rack * effective_tdp) * 100

        # Annual pump electricity cost
        pump_kwh_per_year = total_pump_power_kw * HOURS_PER_YEAR
        pump_cost_per_year = pump_kwh_per_year * ELECTRICITY_USD_PER_KWH

        print(f"\n  {cluster.name}")
        print(f"  {cluster.note}")
        print(f"  {total_gpus:,} GPUs × {effective_tdp:.0f}W effective = {total_gpu_power_kw:.0f} kW GPU power")
        margin = cluster.tj_limit_c - rack.max_junction_temp_c
        margin_str = f"{margin:+.1f}°C vs {cluster.tj_limit_c:.0f}°C limit"
        print(f"  ┌─ Rack thermal: {rack.total_heat_load_w/1000:.1f} kW/rack | "
              f"Max Tj: {rack.max_junction_temp_c:.1f}°C ({margin_str}) | "
              f"CDU return: {rack.cdu_outlet_temp_c:.1f}°C")
        print(f"  ├─ Pump power:   {rack.total_pump_power_w:.1f} W/rack × {cluster.rack_count} racks = "
              f"{total_pump_power_kw:.2f} kW total")
        print(f"  ├─ Cooling tax:  {cooling_tax_pct:.2f}% of GPU TDP goes to moving coolant")
        print(f"  ├─ CDU farm:     {cluster.rack_count} CDUs @ "
              f"{cluster.flow_per_gpu_lpm * cluster.gpu_count_per_rack:.0f} LPM each = "
              f"{cluster.flow_per_gpu_lpm * cluster.gpu_count_per_rack * cluster.rack_count:.0f} LPM total")
        print(f"  └─ Annual pump cost: ${pump_cost_per_year:,.0f}/year "
              f"({pump_kwh_per_year:,.0f} kWh × ${ELECTRICITY_USD_PER_KWH}/kWh)")

    print()


# ---------------------------------------------------------------------------
# Section 2: Coolant comparison at cluster scale
# ---------------------------------------------------------------------------

def section_coolant_comparison() -> None:
    """Water vs glycol50 cooling tax for a 256-GPU H100 cluster."""
    cluster = CLUSTERS[0]   # 128-GPU H100 cluster
    total_gpus = cluster.gpu_count_per_rack * cluster.rack_count
    effective_tdp = cluster.tdp_per_gpu_w * GPU_UTILIZATION

    print("=" * 80)
    print("Section 2: Coolant Selection — Water vs Glycol50 at Cluster Scale")
    print(f"  Config: {cluster.name} | {total_gpus} GPUs | "
          f"{effective_tdp:.0f}W effective TDP/GPU")
    print("-" * 80)
    print(f"  {'Metric':<35}  {'Water':>14}  {'Glycol50':>14}")
    print("-" * 80)

    results = {}
    for coolant in ["water", "glycol50"]:
        rack = analyze_rack(AnalyzeRackInput(
            gpu_count=cluster.gpu_count_per_rack,
            topology="parallel",
            heat_load_per_gpu_w=effective_tdp,
            total_flow_lpm=cluster.flow_per_gpu_lpm * cluster.gpu_count_per_rack,
            cdu_supply_temp_c=cluster.cdu_supply_c,
            coolant=coolant,
        ))
        total_pump_kw = rack.total_pump_power_w / 1000 * cluster.rack_count
        annual_cost = total_pump_kw * HOURS_PER_YEAR * ELECTRICITY_USD_PER_KWH
        results[coolant] = {
            "rack": rack,
            "total_pump_kw": total_pump_kw,
            "annual_cost": annual_cost,
        }

    w = results["water"]
    g = results["glycol50"]

    def row(label: str, wval: str, gval: str) -> None:
        print(f"  {label:<35}  {wval:>14}  {gval:>14}")

    row("Max junction temp (°C)",
        f"{w['rack'].max_junction_temp_c:.1f}°C",
        f"{g['rack'].max_junction_temp_c:.1f}°C")
    row("Cold plate ΔP (kPa)",
        f"{w['rack'].total_pressure_drop_pa/1000:.1f} kPa",
        f"{g['rack'].total_pressure_drop_pa/1000:.1f} kPa")
    row("Pump power per rack (W)",
        f"{w['rack'].total_pump_power_w:.1f} W",
        f"{g['rack'].total_pump_power_w:.1f} W")
    row(f"Total pump power ({cluster.rack_count} racks) (kW)",
        f"{w['total_pump_kw']:.3f} kW",
        f"{g['total_pump_kw']:.3f} kW")
    row("Annual pump electricity cost",
        f"${w['annual_cost']:,.0f}/yr",
        f"${g['annual_cost']:,.0f}/yr")
    row("Glycol annual penalty",
        "—",
        f"${g['annual_cost'] - w['annual_cost']:,.0f}/yr more")

    print("-" * 80)
    penalty_pct = (g["rack"].total_pump_power_w / w["rack"].total_pump_power_w - 1) * 100
    print(f"  → Glycol50 requires {penalty_pct:.0f}% more pump power per rack "
          f"due to higher viscosity.")
    print(f"  → Glycol advantage: freeze protection, corrosion inhibition.")
    print(f"  → Water advantage: better thermal performance, lower pump cost.")
    print()


# ---------------------------------------------------------------------------
# Section 3: Cooling tax summary across GPU generations
# ---------------------------------------------------------------------------

def section_cooling_tax_summary() -> None:
    """Cooling tax (pump W / GPU TDP) for each GPU generation at typical flow."""
    print("=" * 80)
    print("Section 3: Cooling Tax by GPU Generation")
    print("  Pump power as a fraction of GPU TDP — the 'invisible' power overhead")
    print("-" * 80)
    print(f"  {'GPU':<22}  {'TDP (W)':>8}  {'Flow/GPU':>9}  "
          f"{'Pump/GPU (W)':>13}  {'Cooling Tax':>12}")
    print("-" * 80)

    gpu_configs = [
        ("H100 SXM",  700.0,  8.0),
        ("MI300X",    750.0,  8.0),
        ("B200",     1200.0, 12.0),
        ("B200",     1200.0, 20.0),
    ]

    for gpu_name, tdp, flow_per_gpu in gpu_configs:
        rack = analyze_rack(AnalyzeRackInput(
            gpu_count=1,
            topology="parallel",
            heat_load_per_gpu_w=tdp,
            total_flow_lpm=flow_per_gpu,
            cdu_supply_temp_c=25.0,
            coolant="water",
        ))
        pump_per_gpu = rack.total_pump_power_w
        tax_pct = pump_per_gpu / tdp * 100
        label = f"{gpu_name} @ {flow_per_gpu:.0f} LPM"
        print(f"  {label:<22}  {tdp:>8.0f}  {flow_per_gpu:>8.0f}L  "
              f"{pump_per_gpu:>12.1f}  {tax_pct:>11.2f}%")

    print("-" * 80)
    print("  Cooling tax is small (<3%) at typical flows — but multiplied across")
    print("  thousands of GPUs in a large cluster, it becomes a meaningful OpEx line.")
    print()


if __name__ == "__main__":
    print()
    print("  AI FACTORY COOLING BUDGET")
    print(f"  Electricity: ${ELECTRICITY_USD_PER_KWH}/kWh | "
          f"GPU utilization: {GPU_UTILIZATION*100:.0f}% | 8,760 hr/yr")
    print()

    section_cooling_budget()
    section_coolant_comparison()
    section_cooling_tax_summary()
