"""First-pass cooling decision synthesis for GPU liquid cooling trade studies.

Composes existing physics APIs (analyze, optimize_flow, analyze_rack,
compute_sensitivity) into a structured engineering recommendation memo.
No new physics here — this is synthesis and presentation only.
"""

from __future__ import annotations

from pydantic import ValidationError

from .physics import analyze, analyze_rack, compute_sensitivity, optimize_flow
from .schemas import (
    AnalyzeColdplateInput,
    AnalyzeRackInput,
    DecisionReport,
    DecisionScenario,
    FlowBand,
    Geometry,
    OptimizeFlowRateInput,
    RiskLevel,
)

# Documented model limitations — always surfaced to callers, never suppressed.
# Source: docs/physics.md sections E and G.
KNOWN_LIMITATIONS: list[str] = [
    "Manifold and header pressure losses are not modeled; actual system ΔP will be higher.",
    "Fluid properties are assumed constant at the nominal inlet temperature; glycol viscosity "
    "varies ~2× over 20–60°C, which affects ΔP and Nusselt predictions at elevated temperatures.",
    "All GPUs are assumed identical (same TDP, geometry, resistances); "
    "real rack heterogeneity is not captured.",
    "Steady-state only — no transient thermal capacitance or thermal mass effects.",
    "Uniform flow distribution assumed; no maldistribution across channels or parallel branches.",
    "No boiling or two-phase flow; model is valid only for single-phase liquid cooling.",
]

# Flow band scaling factors relative to the minimum feasible flow.
_RECOMMENDED_FACTOR = 1.15  # 15% above minimum for operating margin
_MAX_FACTOR = 1.50          # 50% above minimum as upper bound


def _resolve_geometry(geometry: Geometry | None) -> Geometry:
    return geometry if geometry is not None else Geometry()


def _make_coldplate_input(scenario: DecisionScenario, flow_lpm: float) -> AnalyzeColdplateInput:
    return AnalyzeColdplateInput(
        heat_load_w=scenario.heat_load_w,
        flow_rate_lpm=flow_lpm,
        inlet_temp_c=scenario.inlet_temp_c,
        coolant=scenario.coolant,
        r_jc_k_per_w=scenario.r_jc_k_per_w,
        r_tim_k_per_w=scenario.r_tim_k_per_w,
        geometry=_resolve_geometry(scenario.geometry),
    )


def _topology_rationale(scenario: DecisionScenario, per_gpu_flow_lpm: float) -> str:
    if scenario.gpu_count <= 1:
        return "Single GPU — topology not applicable."

    # Compare topologies at the same per-GPU flow (the user-relevant operating
    # point). Series has total = per-GPU (single loop), parallel has
    # total = per-GPU × N (split across N branches). See analyze_rack semantics.
    common = dict(
        gpu_count=scenario.gpu_count,
        heat_load_per_gpu_w=scenario.heat_load_w,
        cdu_supply_temp_c=scenario.inlet_temp_c,
        coolant=scenario.coolant,
        r_jc_k_per_w=scenario.r_jc_k_per_w,
        r_tim_k_per_w=scenario.r_tim_k_per_w,
        geometry=_resolve_geometry(scenario.geometry),
    )
    try:
        r_series = analyze_rack(
            AnalyzeRackInput(topology="series", total_flow_lpm=per_gpu_flow_lpm, **common)
        )
    except ValidationError:
        # Series stacking overflowed the model bound — comparison can't run.
        return (
            f"{scenario.topology} topology selected. Series comparison unavailable: "
            f"{scenario.gpu_count} GPUs in series at {per_gpu_flow_lpm:.2f} LPM "
            "would push downstream coolant past the 80°C model bound."
        )
    r_parallel = analyze_rack(
        AnalyzeRackInput(
            topology="parallel",
            total_flow_lpm=per_gpu_flow_lpm * scenario.gpu_count,
            **common,
        )
    )

    delta_tj = r_series.max_junction_temp_c - r_parallel.max_junction_temp_c
    delta_pump = r_series.total_pump_power_w - r_parallel.total_pump_power_w

    chosen = scenario.topology
    if chosen == "series":
        return (
            f"Series topology selected. "
            f"Series Tj_max = {r_series.max_junction_temp_c:.1f}°C vs "
            f"parallel Tj_max = {r_parallel.max_junction_temp_c:.1f}°C "
            f"(Δ = {delta_tj:+.1f}°C). "
            f"Series pump power = {r_series.total_pump_power_w:.1f} W vs "
            f"parallel = {r_parallel.total_pump_power_w:.1f} W "
            f"(Δ = {delta_pump:+.1f} W). "
            "Series plumbing is simpler (one loop) but delivers hotter coolant to downstream GPUs."
        )
    else:
        return (
            f"Parallel topology selected. "
            f"Parallel Tj_max = {r_parallel.max_junction_temp_c:.1f}°C vs "
            f"series Tj_max = {r_series.max_junction_temp_c:.1f}°C "
            f"(Δ = {abs(delta_tj):.1f}°C lower with parallel). "
            f"Parallel pump power = {r_parallel.total_pump_power_w:.1f} W vs "
            f"series = {r_series.total_pump_power_w:.1f} W "
            f"(Δ = {abs(delta_pump):.1f} W {'lower' if delta_pump > 0 else 'higher'} with parallel). "
            "Parallel topology equalizes inlet temperature across all GPUs but requires a manifold."
        )


def _render_memo(report: DecisionReport) -> str:
    feasibility = "FEASIBLE" if report.feasible else "INFEASIBLE"
    risk_str = report.risk_level.value.upper()

    lines = [
        f"# Thermal Decision Memo — {report.scenario_label}",
        "",
        f"**Feasibility:** {feasibility}  |  **Risk Level:** {risk_str}",
        "",
        "## Recommended Operating Point",
        "",
        f"- **Supply temperature:** {report.recommended_supply_temp_c:.1f}°C",
        f"- **Flow rate (per GPU):** {report.recommended_flow.recommended_lpm:.2f} LPM "
        f"(min {report.recommended_flow.min_lpm:.2f}, search max {report.recommended_flow.max_lpm:.2f})",
        f"- **Junction temperature at recommended flow:** {report.junction_temp_at_recommended_c:.1f}°C",
        f"- **Margin remaining:** {report.margin_remaining_c:.1f}°C "
        f"(after {report.recommended_flow.basis})",
        "",
    ]

    if report.topology_recommendation:
        lines += [
            "## Topology Recommendation",
            "",
            report.topology_recommendation,
            "",
        ]

    lines += [
        "## Uncertainty & Guardband",
        "",
        "The following sources contribute to Tj uncertainty:",
        "",
    ]
    for source, delta in report.uncertainty_section.items():
        lines.append(f"- **{source}:** ±{delta:.1f}°C")

    lines += [""]

    if report.warnings:
        lines += [
            "## Warnings",
            "",
        ]
        for w in report.warnings:
            lines.append(f"- {w}")
        lines += [""]

    lines += [
        "## Model Blind Spots",
        "",
        "The following effects are **not modeled** and must be accounted for separately:",
        "",
    ]
    for bs in report.blind_spots:
        lines.append(f"- {bs}")

    lines += [
        "",
        "---",
        "*Generated by thermal-mcp-server. First-pass sizing only — not a substitute for detailed CFD or measured validation.*",
    ]

    return "\n".join(lines)


def generate_decision_report(scenario: DecisionScenario) -> DecisionReport:
    """Synthesize a first-pass cooling decision report for a GPU thermal scenario.

    Composes optimize_flow, analyze, analyze_rack, and compute_sensitivity into
    a structured recommendation with explicit guardbands and model blind spots.

    Args:
        scenario: Scenario parameters. flow_rate_lpm=None triggers auto-optimization.

    Returns:
        DecisionReport with recommended flow band, risk level, uncertainty breakdown,
        topology rationale (for multi-GPU), and a rendered markdown memo.
    """
    geom = _resolve_geometry(scenario.geometry)
    effective_target = scenario.target_junction_temp_c - scenario.margin_c

    # Step 1: find minimum feasible flow (or use the provided fixed flow).
    if scenario.flow_rate_lpm is None:
        opt_inp = OptimizeFlowRateInput(
            heat_load_w=scenario.heat_load_w,
            max_junction_temp_c=scenario.target_junction_temp_c,
            margin_c=scenario.margin_c,
            inlet_temp_c=scenario.inlet_temp_c,
            coolant=scenario.coolant,
            r_jc_k_per_w=scenario.r_jc_k_per_w,
            r_tim_k_per_w=scenario.r_tim_k_per_w,
            geometry=geom,
            flow_min_lpm=0.5,
            flow_max_lpm=60.0,
        )
        min_flow_lpm, opt_result = optimize_flow(opt_inp)
        feasible = opt_result is not None
        flow_basis = f"margin_c={scenario.margin_c}°C applied to target {scenario.target_junction_temp_c}°C"
    else:
        min_flow_lpm = scenario.flow_rate_lpm
        cp_inp = _make_coldplate_input(scenario, min_flow_lpm)
        opt_result = analyze(cp_inp)
        feasible = opt_result.junction_temp_c <= effective_target
        flow_basis = "fixed flow rate provided by caller"

    recommended_lpm = min_flow_lpm * _RECOMMENDED_FACTOR
    max_search_lpm = min_flow_lpm * _MAX_FACTOR

    flow_band = FlowBand(
        min_lpm=round(min_flow_lpm, 3),
        recommended_lpm=round(recommended_lpm, 3),
        max_lpm=round(max_search_lpm, 3),
        basis=flow_basis,
    )

    # Step 2: full analysis at recommended flow for Tj and sensitivity.
    # Sensitivity is per-coldplate; rack physics is layered on top below.
    rec_inp = _make_coldplate_input(scenario, recommended_lpm)
    rec_result = analyze(rec_inp)
    sensitivity = compute_sensitivity(rec_inp)
    rack_warnings: list[str] = []

    # Step 2b: for multi-GPU, override the single-coldplate verdict with
    # rack-aware physics. In series, downstream GPUs see hotter inlets, so a
    # single-coldplate "feasible" reading can hide a real overheat at the last
    # GPU. In parallel, results match single-coldplate but we still surface
    # the rack max for clarity.
    if scenario.gpu_count > 1:
        # AnalyzeRackInput.total_flow_lpm is the flow at the rack inlet:
        # - series: that single flow passes through every GPU, so total = per-GPU
        # - parallel: the flow is split across N branches, so total = N × per-GPU
        if scenario.topology == "series":
            total_flow_for_rack = recommended_lpm
        else:
            total_flow_for_rack = recommended_lpm * scenario.gpu_count
        try:
            rack_inp = AnalyzeRackInput(
                gpu_count=scenario.gpu_count,
                topology=scenario.topology,
                heat_load_per_gpu_w=scenario.heat_load_w,
                total_flow_lpm=total_flow_for_rack,
                cdu_supply_temp_c=scenario.inlet_temp_c,
                coolant=scenario.coolant,
                r_jc_k_per_w=scenario.r_jc_k_per_w,
                r_tim_k_per_w=scenario.r_tim_k_per_w,
                geometry=geom,
            )
            rack_result = analyze_rack(rack_inp)
            tj_at_rec = rack_result.max_junction_temp_c
            rack_warnings = list(rack_result.warnings)
            # Rack physics has the final say on feasibility for multi-GPU.
            feasible = feasible and (tj_at_rec <= effective_target)
        except ValidationError:
            # Series stacking pushed a downstream inlet past the 80°C schema
            # bound. That is itself a clear infeasibility signal.
            tj_at_rec = rec_result.junction_temp_c  # best-effort placeholder
            rack_warnings = [
                f"{scenario.topology} topology with {scenario.gpu_count} GPUs "
                f"at {recommended_lpm:.2f} LPM/GPU pushes downstream coolant "
                f"past the 80°C model bound; configuration is infeasible."
            ]
            feasible = False
    else:
        tj_at_rec = rec_result.junction_temp_c

    # Margin to the actual hard limit (before subtracting margin_c), so callers
    # see total headroom to the design ceiling — not headroom to the internal
    # optimization sub-target.
    margin_remaining = scenario.target_junction_temp_c - tj_at_rec

    # Step 3: risk level from remaining margin to the actual hard limit.
    # Thresholds account for the user-specified margin_c being already baked in:
    # LOW: ≥10°C total headroom to design ceiling
    # MEDIUM: 5–10°C
    # HIGH: <5°C or infeasible
    if not feasible:
        risk = RiskLevel.HIGH
    elif margin_remaining >= 10.0:
        risk = RiskLevel.LOW
    elif margin_remaining >= 5.0:
        risk = RiskLevel.MEDIUM
    else:
        risk = RiskLevel.HIGH

    # Step 4: topology rationale for multi-GPU scenarios (uses recommended flow).
    topology_rec = _topology_rationale(scenario, recommended_lpm)

    # Step 5: uncertainty section from sensitivity output.
    uncertainty: dict[str, float] = {
        "R_jc manufacturing variation (±20%)": round(sensitivity.r_jc_uncertainty_pm_c, 2),
        "TIM pump-out degradation (R_tim ×2 after 2–3 yr)": round(sensitivity.r_tim_aged_delta_c, 2),
        "∂Tj/∂Q × 10W TDP creep": round(abs(sensitivity.dtj_dq_c_per_w) * 10.0, 2),
        "∂Tj/∂T_inlet × 1°C supply drift": round(abs(sensitivity.dtj_dt_inlet_dimensionless) * 1.0, 2),
    }

    # Step 6: aggregate warnings.
    all_warnings = list(rec_result.warnings) + rack_warnings
    if not feasible:
        all_warnings.insert(
            0,
            f"INFEASIBLE: cannot reach Tj ≤ {effective_target:.1f}°C "
            f"(target {scenario.target_junction_temp_c}°C − margin {scenario.margin_c}°C) "
            "with the recommended flow and selected topology.",
        )

    report = DecisionReport(
        scenario_label=f"{scenario.chip_label} — {scenario.heat_load_w:.0f} W, "
        f"{scenario.gpu_count} GPU{'s' if scenario.gpu_count > 1 else ''}, "
        f"{scenario.coolant}, {scenario.inlet_temp_c:.0f}°C inlet",
        feasible=feasible,
        risk_level=risk,
        recommended_flow=flow_band,
        recommended_supply_temp_c=scenario.inlet_temp_c,
        junction_temp_at_recommended_c=round(tj_at_rec, 2),
        margin_remaining_c=round(margin_remaining, 2),
        topology_recommendation=topology_rec,
        uncertainty_section=uncertainty,
        warnings=all_warnings,
        blind_spots=KNOWN_LIMITATIONS,
        rendered_memo="",  # placeholder — filled below
    )

    report = report.model_copy(update={"rendered_memo": _render_memo(report)})
    return report
