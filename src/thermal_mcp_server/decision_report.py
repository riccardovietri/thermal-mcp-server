"""Version 2 cooling decision synthesis for bounded GPU thermal studies."""

from __future__ import annotations

import importlib.metadata
from typing import Any

from pydantic import ValidationError

from .physics import analyze, analyze_rack, optimize_flow
from .schemas import (
    AnalyzeColdplateInput,
    AnalyzeRackInput,
    DecisionReport,
    DecisionScenario,
    DecisionStatus,
    EvaluatedPoint,
    EvaluatedPointRole,
    EvaluationMode,
    FlowSearch,
    FlowSearchScope,
    Geometry,
    ModelMetadata,
    StressScenarioInputs,
    StressScenarioResult,
)

KNOWN_LIMITATIONS: list[str] = [
    "Manifold and header pressure losses are not modeled; system hydraulic feasibility is not assessed.",
    "Fluid properties are assumed constant at nominal 25°C properties.",
    "All GPUs are assumed identical; heterogeneous racks are not captured.",
    "Steady-state only — no transient thermal capacitance or thermal mass effects.",
    "Uniform flow distribution is assumed; no channel or parallel-branch maldistribution is modeled.",
    "No boiling or two-phase flow; the model is limited to single-phase liquid cooling.",
]

APPLICABILITY_NOTICES: list[str] = [
    "Transition-regime Nusselt and friction correlations are linearly blended for continuity; this is not experimental validation.",
    "Rectangular-channel correlations are reduced-order and do not establish validity for every aspect ratio or developing-flow condition.",
    "Effective heated area and spreading are simplified; local hotspot temperatures are unavailable.",
    "Coolant properties are fixed at nominal reference conditions and are not temperature-dependent.",
    "No measured cold-plate or rack calibration is included; numeric precision is not model accuracy.",
]

_FLOW_MIN_LPM = 0.5
_FLOW_MAX_LPM = 60.0


def _package_version() -> str:
    try:
        return importlib.metadata.version("thermal-mcp-server")
    except importlib.metadata.PackageNotFoundError:
        return "0.3.0"


def _resolve_geometry(geometry: Geometry | None) -> Geometry:
    return geometry if geometry is not None else Geometry()


def _make_coldplate_input(
    scenario: DecisionScenario,
    flow_lpm: float,
    *,
    inlet_temp_c: float | None = None,
    heat_load_w: float | None = None,
    r_jc: float | None = None,
    r_tim: float | None = None,
) -> AnalyzeColdplateInput:
    return AnalyzeColdplateInput(
        heat_load_w=scenario.heat_load_w if heat_load_w is None else heat_load_w,
        flow_rate_lpm=flow_lpm,
        inlet_temp_c=scenario.inlet_temp_c if inlet_temp_c is None else inlet_temp_c,
        coolant=scenario.coolant,
        r_jc_k_per_w=scenario.r_jc_k_per_w if r_jc is None else r_jc,
        r_tim_k_per_w=scenario.r_tim_k_per_w if r_tim is None else r_tim,
        geometry=_resolve_geometry(scenario.geometry),
    )


def _make_rack_input(
    scenario: DecisionScenario,
    flow_lpm_per_gpu: float,
    *,
    inlet_temp_c: float | None = None,
    heat_load_w: float | None = None,
    r_jc: float | None = None,
    r_tim: float | None = None,
) -> AnalyzeRackInput:
    total_flow = flow_lpm_per_gpu if scenario.topology == "series" else flow_lpm_per_gpu * scenario.gpu_count
    return AnalyzeRackInput(
        gpu_count=scenario.gpu_count,
        topology=scenario.topology,
        heat_load_per_gpu_w=scenario.heat_load_w if heat_load_w is None else heat_load_w,
        total_flow_lpm=total_flow,
        cdu_supply_temp_c=scenario.inlet_temp_c if inlet_temp_c is None else inlet_temp_c,
        coolant=scenario.coolant,
        r_jc_k_per_w=scenario.r_jc_k_per_w if r_jc is None else r_jc,
        r_tim_k_per_w=scenario.r_tim_k_per_w if r_tim is None else r_tim,
        geometry=_resolve_geometry(scenario.geometry),
    )


def _point(
    scenario: DecisionScenario,
    flow_lpm_per_gpu: float,
    junction_temp_c: float,
    pressure_drop_pa: float,
    pump_power_w: float,
    cdu_outlet_temp_c: float,
    role: EvaluatedPointRole,
) -> EvaluatedPoint:
    criterion = scenario.target_junction_temp_c - scenario.margin_c
    return EvaluatedPoint(
        role=role,
        flow_lpm_per_gpu=flow_lpm_per_gpu,
        supply_temp_c=scenario.inlet_temp_c,
        junction_temp_c=junction_temp_c,
        margin_to_limit_c=scenario.target_junction_temp_c - junction_temp_c,
        margin_to_criterion_c=criterion - junction_temp_c,
        meets_thermal_target=junction_temp_c <= criterion,
        pressure_drop_pa=pressure_drop_pa,
        pump_power_w=pump_power_w,
        cdu_outlet_temp_c=cdu_outlet_temp_c,
    )


def _evaluate_at_flow(
    scenario: DecisionScenario,
    flow_lpm_per_gpu: float,
    role: EvaluatedPointRole,
) -> tuple[EvaluatedPoint | None, list[str], str | None]:
    try:
        if scenario.gpu_count == 1:
            result = analyze(_make_coldplate_input(scenario, flow_lpm_per_gpu))
            return (
                _point(
                    scenario,
                    flow_lpm_per_gpu,
                    result.junction_temp_c,
                    result.pressure_drop_pa,
                    result.pump_power_w,
                    scenario.inlet_temp_c + result.coolant_rise_c,
                    role,
                ),
                result.warnings,
                None,
            )
        rack = analyze_rack(_make_rack_input(scenario, flow_lpm_per_gpu))
        return (
            _point(
                scenario,
                flow_lpm_per_gpu,
                rack.max_junction_temp_c,
                rack.total_pressure_drop_pa,
                rack.total_pump_power_w,
                rack.cdu_outlet_temp_c,
                role,
            ),
            rack.warnings,
            None,
        )
    except ValidationError:
        return None, [], "Rack evaluation unavailable: downstream inlet exceeds the supported input bound."


def _topology_assessment(scenario: DecisionScenario, flow_lpm_per_gpu: float | None) -> str:
    if scenario.gpu_count <= 1:
        return "Single GPU; topology comparison is not applicable."
    if flow_lpm_per_gpu is None:
        return "Topology comparison unavailable because no valid per-GPU operating point was evaluated."
    common: dict[str, Any] = {
        "gpu_count": scenario.gpu_count,
        "heat_load_per_gpu_w": scenario.heat_load_w,
        "cdu_supply_temp_c": scenario.inlet_temp_c,
        "coolant": scenario.coolant,
        "r_jc_k_per_w": scenario.r_jc_k_per_w,
        "r_tim_k_per_w": scenario.r_tim_k_per_w,
        "geometry": _resolve_geometry(scenario.geometry),
    }
    try:
        series = analyze_rack(AnalyzeRackInput(topology="series", total_flow_lpm=flow_lpm_per_gpu, **common))
        parallel = analyze_rack(AnalyzeRackInput(topology="parallel", total_flow_lpm=flow_lpm_per_gpu * scenario.gpu_count, **common))
    except ValidationError:
        return "Topology comparison unavailable because the series case exceeds the supported downstream inlet bound."
    return (
        f"At {flow_lpm_per_gpu:.3f} LPM/GPU, series Tj_max={series.max_junction_temp_c:.2f}°C and "
        f"parallel Tj_max={parallel.max_junction_temp_c:.2f}°C. "
        f"Series cold-plate-only ΔP={series.total_pressure_drop_pa / 1000:.2f} kPa; "
        f"parallel cold-plate-only ΔP={parallel.total_pressure_drop_pa / 1000:.2f} kPa. "
        "This comparison uses a common per-GPU flow; it does not select a topology or assess system hydraulics."
    )


def _resolved_scenario(scenario: DecisionScenario) -> dict[str, Any]:
    resolved = scenario.model_dump(mode="json")
    resolved["geometry"] = _resolve_geometry(scenario.geometry).model_dump(mode="json")
    return resolved


def _input_provenance(scenario: DecisionScenario) -> dict[str, dict[str, str | None]]:
    provenance: dict[str, dict[str, str | None]] = {}
    for field in DecisionScenario.model_fields:
        if field in {"geometry", "stress_scenarios", "input_source_notes"}:
            continue
        origin = "supplied" if field in scenario.model_fields_set else "defaulted"
        provenance[field] = {"origin": origin, "source_note": scenario.input_source_notes.get(field)}

    geometry = _resolve_geometry(scenario.geometry)
    geometry_supplied = scenario.geometry is not None
    for field in Geometry.model_fields:
        path = f"geometry.{field}"
        origin = "supplied" if geometry_supplied and field in geometry.model_fields_set else "defaulted"
        provenance[path] = {"origin": origin, "source_note": scenario.input_source_notes.get(path)}

    for field in StressScenarioInputs.model_fields:
        path = f"stress_scenarios.{field}"
        provenance[path] = {
            "origin": "supplied" if field in scenario.stress_scenarios.model_fields_set else "defaulted",
            "source_note": scenario.input_source_notes.get(path),
        }
    provenance["input_source_notes"] = {
        "origin": "supplied" if "input_source_notes" in scenario.model_fields_set else "defaulted",
        "source_note": None,
    }
    return provenance


def _stress_cases(settings: StressScenarioInputs) -> list[tuple[str, str, float, str]]:
    return [
        ("r_jc_minus_variation", "r_jc_k_per_w", 1.0 - settings.r_jc_variation_fraction, "K/W"),
        ("r_jc_plus_variation", "r_jc_k_per_w", 1.0 + settings.r_jc_variation_fraction, "K/W"),
        ("r_tim_multiplier", "r_tim_k_per_w", settings.r_tim_multiplier, "K/W"),
        ("heat_load_delta", "heat_load_w", settings.heat_load_delta_w, "W"),
        ("supply_temp_delta", "inlet_temp_c", settings.supply_temp_delta_c, "°C"),
    ]


def _evaluate_stresses(
    scenario: DecisionScenario,
    settings: StressScenarioInputs,
    flow_lpm_per_gpu: float | None,
    baseline: EvaluatedPoint | None,
    allow_evaluation: bool,
) -> list[StressScenarioResult]:
    results: list[StressScenarioResult] = []
    for name, parameter, change, units in _stress_cases(settings):
        heat_load = scenario.heat_load_w
        r_jc = scenario.r_jc_k_per_w
        r_tim = scenario.r_tim_k_per_w
        inlet_temp = scenario.inlet_temp_c
        if parameter == "r_jc_k_per_w":
            perturbed = r_jc * change
            base_value = r_jc
            r_jc = perturbed
        elif parameter == "r_tim_k_per_w":
            perturbed = r_tim * change
            base_value = r_tim
            r_tim = perturbed
        elif parameter == "heat_load_w":
            perturbed = heat_load + change
            base_value = heat_load
            heat_load = perturbed
        else:
            perturbed = inlet_temp + change
            base_value = inlet_temp
            inlet_temp = perturbed
        if baseline is None:
            unavailable_reason = "No valid evaluated point is available for stress evaluation."
        elif baseline.role == "search_bound_diagnostic" or not allow_evaluation:
            unavailable_reason = "Stress evaluation is not run on a search-bound diagnostic point."
        elif flow_lpm_per_gpu is None:
            unavailable_reason = "No evaluated flow is available for stress evaluation."
        else:
            unavailable_reason = "Stress evaluation is unavailable for this point."
        if not allow_evaluation or flow_lpm_per_gpu is None or baseline is None:
            results.append(
                StressScenarioResult(
                    name=name,
                    status="unavailable",
                    changed_parameter=parameter,
                    base_value=base_value,
                    perturbed_value=perturbed,
                    units=units,
                    reason=unavailable_reason,
                )
            )
            continue
        try:
            if scenario.gpu_count == 1:
                result = analyze(_make_coldplate_input(scenario, flow_lpm_per_gpu, inlet_temp_c=inlet_temp, heat_load_w=heat_load, r_jc=r_jc, r_tim=r_tim))
                tj = result.junction_temp_c
            else:
                rack = analyze_rack(_make_rack_input(scenario, flow_lpm_per_gpu, inlet_temp_c=inlet_temp, heat_load_w=heat_load, r_jc=r_jc, r_tim=r_tim))
                tj = rack.max_junction_temp_c
        except (ValidationError, ZeroDivisionError):
            results.append(
                StressScenarioResult(
                    name=name,
                    status="unavailable",
                    changed_parameter=parameter,
                    base_value=base_value,
                    perturbed_value=perturbed,
                    units=units,
                    reason="Perturbed inputs exceed the supported model boundary.",
                )
            )
            continue
        results.append(
            StressScenarioResult(
                name=name,
                status="evaluated",
                changed_parameter=parameter,
                base_value=base_value,
                perturbed_value=perturbed,
                units=units,
                signed_junction_delta_c=tj - baseline.junction_temp_c,
                flow_lpm_per_gpu=flow_lpm_per_gpu,
                junction_temp_c=tj,
                margin_to_limit_c=scenario.target_junction_temp_c - tj,
                margin_to_criterion_c=scenario.target_junction_temp_c - scenario.margin_c - tj,
            )
        )
    return results


def _render_memo(report: DecisionReport) -> str:
    lines = [
        f"# Thermal Decision Memo — {report.scenario_label}",
        "",
        f"**Status:** `{report.status.value}`",
        "",
        "System hydraulic feasibility and overall engineering risk are **not assessed**.",
        "",
    ]
    if report.evaluated_point is None:
        lines.extend(["No valid operating point was evaluated.", ""])
    else:
        point = report.evaluated_point
        lines.extend(
            [
                f"## Evaluated Point ({point.role})",
                "",
                f"- **Flow:** {point.flow_lpm_per_gpu:.3f} LPM/GPU",
                f"- **Supply temperature:** {point.supply_temp_c:.2f}°C",
                f"- **Junction temperature:** {point.junction_temp_c:.2f}°C",
                f"- **Margin to criterion:** {point.margin_to_criterion_c:.2f}°C",
                f"- **Margin to limit:** {point.margin_to_limit_c:.2f}°C",
                "- **Display precision:** rounded for the memo; structured fields retain calculation precision.",
                "",
            ]
        )
    if report.flow_search is not None:
        search = report.flow_search
        minimum = "null" if search.minimum_feasible_lpm_per_gpu is None else f"{search.minimum_feasible_lpm_per_gpu:.3f} LPM/GPU"
        lines.extend(
            [
                "## Flow Search",
                "",
                f"- **Scope:** `{search.scope}`",
                f"- **Range:** {search.min_lpm_per_gpu:.3f}–{search.max_lpm_per_gpu:.3f} LPM/GPU",
                f"- **Minimum feasible flow:** {minimum}",
                "",
            ]
        )
    lines.extend(["## Topology Assessment", "", report.topology_assessment, "", "## Stress Scenarios", ""])
    for stress in report.stress_scenarios:
        if stress.status == "evaluated":
            lines.append(f"- **{stress.name}:** ΔTj {stress.signed_junction_delta_c:+.2f}°C")
        else:
            lines.append(f"- **{stress.name}:** unavailable — {stress.reason}")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in report.warnings)
    lines.extend(["", "## Model Blind Spots", ""])
    lines.extend(f"- {blind_spot}" for blind_spot in report.blind_spots)
    lines.extend(["", "---", "*First-pass reduced-order analysis; not a substitute for measured validation or detailed CFD.*"])
    return "\n".join(lines)


def generate_decision_report(scenario: DecisionScenario) -> DecisionReport:
    """Generate a v2 report with explicit search scope and unknown states."""
    warnings: list[str] = []
    evaluated_point: EvaluatedPoint | None = None
    flow_search: FlowSearch | None = None
    attempted_flow = scenario.flow_rate_lpm
    evaluation_mode = EvaluationMode.FIXED_FLOW if scenario.flow_rate_lpm is not None else EvaluationMode.THERMAL_SEARCH
    status: DecisionStatus
    stress_flow: float | None = None
    allow_stress = False

    if scenario.flow_rate_lpm is not None:
        evaluated_point, physics_warnings, reason = _evaluate_at_flow(scenario, scenario.flow_rate_lpm, "fixed_input")
        warnings.extend(physics_warnings)
        if evaluated_point is None:
            status = DecisionStatus.UNDETERMINED
            warnings.append(reason or "Operating-point evaluation unavailable.")
        elif evaluated_point.meets_thermal_target:
            status = DecisionStatus.MEETS_TARGET
            stress_flow = scenario.flow_rate_lpm
            allow_stress = True
        else:
            status = DecisionStatus.FAILS_AT_EVALUATED_FLOW
            stress_flow = scenario.flow_rate_lpm
            allow_stress = True
            warnings.append("The supplied fixed flow misses the guarded thermal criterion; another flow may work.")
    else:
        from .schemas import OptimizeFlowRateInput

        scope: FlowSearchScope
        if scenario.gpu_count == 1:
            scope = "single_plate"
        elif scenario.topology == "parallel":
            scope = "parallel_rack"
        else:
            scope = "single_plate_candidate_for_series"
        optimizer = OptimizeFlowRateInput(
            heat_load_w=scenario.heat_load_w,
            max_junction_temp_c=scenario.target_junction_temp_c,
            margin_c=scenario.margin_c,
            inlet_temp_c=scenario.inlet_temp_c,
            coolant=scenario.coolant,
            flow_min_lpm=_FLOW_MIN_LPM,
            flow_max_lpm=_FLOW_MAX_LPM,
            r_jc_k_per_w=scenario.r_jc_k_per_w,
            r_tim_k_per_w=scenario.r_tim_k_per_w,
            geometry=_resolve_geometry(scenario.geometry),
        )
        lower_point, _, _ = _evaluate_at_flow(scenario, _FLOW_MIN_LPM, "search_bound_diagnostic")
        upper_point, upper_warnings, upper_reason = _evaluate_at_flow(scenario, _FLOW_MAX_LPM, "search_bound_diagnostic")
        min_flow, optimization_result = optimize_flow(optimizer)
        lower_pass = lower_point is not None and lower_point.meets_thermal_target
        upper_pass = upper_point is not None and upper_point.meets_thermal_target
        candidate_found = optimization_result is not None
        if not candidate_found and upper_pass:
            min_flow = _FLOW_MAX_LPM
            candidate_found = True
        minimum_feasible = min_flow if candidate_found else None
        if scope == "single_plate_candidate_for_series":
            # The optimizer solved a single cold plate. Its candidate may prove
            # that a series rack point passes, but it cannot prove the rack's
            # minimum feasible flow without a rack-wide search.
            minimum_feasible = None
        flow_search = FlowSearch(
            scope=scope,
            min_lpm_per_gpu=_FLOW_MIN_LPM,
            max_lpm_per_gpu=_FLOW_MAX_LPM,
            minimum_feasible_lpm_per_gpu=minimum_feasible,
            lower_bound_limited=lower_pass,
        )
        if not candidate_found:
            if scenario.gpu_count == 1 or scenario.topology == "parallel":
                evaluated_point = upper_point
                warnings.extend(upper_warnings)
                if upper_reason:
                    warnings.append(upper_reason)
                status = DecisionStatus.NO_FEASIBLE_FLOW_IN_SEARCH_RANGE
                warnings.append(f"No modeled point in {_FLOW_MIN_LPM:g}–{_FLOW_MAX_LPM:g} LPM/GPU meets the guarded thermal criterion.")
            else:
                status = DecisionStatus.UNDETERMINED
                warnings.append("Single-plate search failed, but no rack-wide series search was performed.")
        else:
            attempted_flow = min_flow
            role: EvaluatedPointRole = "thermal_search_result" if scenario.gpu_count == 1 or scenario.topology == "parallel" else "series_candidate"
            evaluated_point, physics_warnings, reason = _evaluate_at_flow(scenario, min_flow, role)
            warnings.extend(physics_warnings)
            if evaluated_point is None:
                status = DecisionStatus.UNDETERMINED
                warnings.append(reason or "Operating-point evaluation unavailable.")
            elif evaluated_point.meets_thermal_target:
                status = DecisionStatus.MEETS_TARGET
                stress_flow = min_flow
                allow_stress = True
                if scope == "single_plate_candidate_for_series":
                    warnings.append(
                        "This is a passing single-plate candidate evaluated on the series rack, not a minimum rack flow or operating recommendation."
                    )
                else:
                    warnings.append(
                        "The minimum feasible flow is the modeled thermal threshold, not an operating recommendation; "
                        "select operating allowance from system evidence."
                    )
            else:
                status = DecisionStatus.UNDETERMINED
                stress_flow = min_flow
                allow_stress = True
                warnings.append("The series candidate fails at the evaluated flow, but no rack-wide search was performed.")

    topology_flow = stress_flow or (evaluated_point.flow_lpm_per_gpu if evaluated_point is not None else None)
    topology_assessment = _topology_assessment(scenario, topology_flow)
    stress_results = _evaluate_stresses(
        scenario,
        scenario.stress_scenarios,
        stress_flow,
        evaluated_point,
        allow_stress,
    )
    if evaluated_point is None:
        warnings.append("No temperature or thermal margin is available for this report.")

    gpu_label = "GPU" if scenario.gpu_count == 1 else "GPUs"
    scenario_label = (
        f"{scenario.chip_label} — {scenario.heat_load_w:.0f} W, {scenario.gpu_count} {gpu_label}, {scenario.coolant}, {scenario.inlet_temp_c:.12g}°C inlet"
    )
    report = DecisionReport(
        scenario_label=scenario_label,
        status=status,
        evaluation_mode=evaluation_mode,
        attempted_flow_lpm_per_gpu=attempted_flow,
        evaluated_point=evaluated_point,
        flow_search=flow_search,
        system_hydraulic_feasibility="not_assessed",
        risk_assessment="not_assessed",
        topology_assessment=topology_assessment,
        stress_scenarios=stress_results,
        resolved_scenario=_resolved_scenario(scenario),
        input_provenance=_input_provenance(scenario),
        model=ModelMetadata(package_version=_package_version(), applicability_notices=APPLICABILITY_NOTICES),
        warnings=warnings,
        blind_spots=KNOWN_LIMITATIONS,
        rendered_memo="",
    )
    return report.model_copy(update={"rendered_memo": _render_memo(report)})
