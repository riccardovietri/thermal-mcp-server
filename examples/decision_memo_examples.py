"""Reference thermal screening reports for GPU liquid cooling trade studies.

Three named scenarios that demonstrate the decision_report synthesis layer:

1. H100 SXM — 8-GPU DGX-class server, series vs parallel comparison
2. B200-proxy — 8-GPU high-power rack, water at 20°C inlet
3. H100 coolant trade study — water vs glycol50 side by side

Each scenario prints a rendered markdown memo. Run directly:

    python examples/decision_memo_examples.py

For the compact Milestone 1 owner-review cases:

    python examples/decision_memo_examples.py --review

These examples use engineering-estimate inputs where vendor data is not
publicly available. All vendor-sourced and estimated values are labeled.
"""

from __future__ import annotations

import argparse

from thermal_mcp_server.decision_report import generate_decision_report
from thermal_mcp_server.schemas import DecisionScenario

DIVIDER = "\n" + "=" * 72 + "\n"


# ---------------------------------------------------------------------------
# Scenario 1: H100 SXM — 8-GPU DGX-class, series vs parallel
# H100 SXM TDP: 700 W (NVIDIA datasheet)
# Tj throttle onset: 83°C (NVIDIA thermal guidelines)
# R_jc, R_tim: engineering estimates; NVIDIA does not publish these.
# ---------------------------------------------------------------------------

H100_BASE = dict(
    chip_label="H100 SXM",
    heat_load_w=700.0,
    r_jc_k_per_w=0.04,  # engineering estimate
    r_tim_k_per_w=0.02,  # engineering estimate
    target_junction_temp_c=83.0,
    margin_c=5.0,
    coolant="water",
    inlet_temp_c=25.0,
)


def scenario_h100_series_vs_parallel() -> None:
    print(DIVIDER)
    print("SCENARIO 1: H100 SXM — 8-GPU DGX-class Server (Series vs Parallel)")
    print(DIVIDER)
    print("Input provenance:")
    print("  heat_load_w=700  [published — NVIDIA H100 SXM datasheet]")
    print("  target_junction_temp_c=83  [published — NVIDIA thermal guidelines]")
    print("  R_jc, R_tim  [engineering estimates — NVIDIA does not publish these]")
    print()

    for topology in ("series", "parallel"):
        scenario = DecisionScenario(gpu_count=8, topology=topology, **H100_BASE)
        report = generate_decision_report(scenario)
        print(report.rendered_memo)
        print()


# ---------------------------------------------------------------------------
# Scenario 2: B200-proxy — high-power 8-GPU rack
# B200 TDP: 1200 W (SemiAnalysis estimate — NOT NVIDIA-published)
# Tj limit: 75°C (SemiAnalysis estimate — NOT NVIDIA-published)
# All thermal resistances are engineering estimates.
# Geometry: high-performance cold plate (narrower channels, larger contact area)
# ---------------------------------------------------------------------------

B200_GEOMETRY = dict(
    channel_count=60,
    channel_width_m=0.7e-3,
    channel_height_m=1.5e-3,
    channel_length_m=0.10,
    base_thickness_m=1.5e-3,
    contact_area_m2=0.016,
)


def scenario_b200_proxy() -> None:
    print(DIVIDER)
    print("SCENARIO 2: B200-proxy — 1200 W, 8 GPUs, Parallel, 20°C Inlet")
    print(DIVIDER)
    print("Input provenance:")
    print("  heat_load_w=1200  [ESTIMATED — SemiAnalysis; NOT NVIDIA-published]")
    print("  target_junction_temp_c=75  [ESTIMATED — SemiAnalysis; NOT NVIDIA-published]")
    print("  R_jc=0.02, R_tim=0.015  [engineering estimates for larger die]")
    print("  Geometry: high-performance cold plate (engineering estimate)")
    print()

    scenario = DecisionScenario(
        chip_label="B200 NVL-proxy",
        heat_load_w=1200.0,
        gpu_count=8,
        topology="parallel",
        target_junction_temp_c=75.0,
        margin_c=5.0,
        coolant="water",
        inlet_temp_c=20.0,
        r_jc_k_per_w=0.02,
        r_tim_k_per_w=0.015,
        geometry=B200_GEOMETRY,
    )
    report = generate_decision_report(scenario)
    print(report.rendered_memo)


# ---------------------------------------------------------------------------
# Scenario 3: H100 coolant trade study — water vs glycol50, single GPU
# Same chip and conditions; compare conditional thermal search results.
# ---------------------------------------------------------------------------


def scenario_h100_coolant_trade_study() -> None:
    print(DIVIDER)
    print("SCENARIO 3: H100 SXM — Coolant Trade Study (Water vs Glycol50, 1 GPU)")
    print(DIVIDER)
    print("Input provenance:")
    print("  Same as Scenario 1, single GPU, comparing coolant choice")
    print()

    results = {}
    for coolant in ("water", "glycol50"):
        scenario = DecisionScenario(gpu_count=1, **{**H100_BASE, "coolant": coolant})
        results[coolant] = generate_decision_report(scenario)
        print(f"--- {coolant.upper()} ---")
        print(results[coolant].rendered_memo)
        print()

    # Summary comparison table
    print("## Side-by-Side Summary")
    print()
    header = f"{'Coolant':<12} {'Status':<35} {'Evaluated LPM':<16} {'Tj (°C)':<12} {'Guarded margin (°C)'}"
    print(header)
    print("-" * len(header))
    for coolant, report in results.items():
        point = report.evaluated_point
        if point is None:
            print(f"{coolant:<12} {report.status.value:<35} unavailable")
        else:
            print(f"{coolant:<12} {report.status.value:<35} {point.flow_lpm_per_gpu:<16.3f} {point.junction_temp_c:<12.1f} {point.margin_to_criterion_c:.1f}")
    print("System hydraulic feasibility and overall risk are not assessed.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def review_cases() -> None:
    """Show the four previously misleading outcomes without full memo output."""
    cases = {
        "Fixed 8 LPM": DecisionScenario(flow_rate_lpm=8.0),
        "Failed thermal search": DecisionScenario(heat_load_w=1200.0, target_junction_temp_c=75.0),
        "Series candidate": DecisionScenario(gpu_count=8, topology="series"),
        "Unavailable rack": DecisionScenario(gpu_count=256, topology="series", flow_rate_lpm=8.0),
    }
    print("Milestone 1: conditional thermal screening, assumed component inputs")
    print(f"{'Case':<24} {'Status':<35} {'Flow LPM/GPU':<15} {'Tj C':<10} {'Guarded margin C'}")
    for label, scenario in cases.items():
        report = generate_decision_report(scenario)
        point = report.evaluated_point
        if point is None:
            print(f"{label:<24} {report.status.value:<35} {'unavailable':<15} {'unavailable':<10} unavailable")
        else:
            print(f"{label:<24} {report.status.value:<35} {point.flow_lpm_per_gpu:<15.3f} {point.junction_temp_c:<10.2f} {point.margin_to_criterion_c:.2f}")
    print("Failed-search and series-candidate points are diagnostics, not recommendations.")
    print("System hydraulic feasibility and overall risk: not assessed. Hardware accuracy: unvalidated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", action="store_true", help="Print the compact Milestone 1 review cases")
    if parser.parse_args().review:
        review_cases()
    else:
        scenario_h100_series_vs_parallel()
        scenario_b200_proxy()
        scenario_h100_coolant_trade_study()
