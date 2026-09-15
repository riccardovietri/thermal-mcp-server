"""MCP server exposing thermal analysis tools for liquid-cooled GPU cold plates."""

from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP
from pydantic import ValidationError

from .decision_report import generate_decision_report
from .physics import COOLANTS, analyze, analyze_rack, compute_sensitivity, optimize_flow
from .schemas import (
    AnalyzeColdplateInput,
    AnalyzeRackInput,
    CompareCoolantsInput,
    CoolantName,
    DecisionScenario,
    Geometry,
    OptimizeFlowRateInput,
    RackTopology,
)

mcp = FastMCP("thermal-mcp-server")


def _geometry_from_dict(geometry: dict[str, Any] | None) -> Geometry:
    return Geometry(**(geometry or {}))


def analyze_coldplate_impl(
    heat_load_w: float,
    flow_rate_lpm: float,
    inlet_temp_c: float = 25.0,
    ambient_temp_c: float = 25.0,
    coolant: CoolantName = "water",
    r_jc_k_per_w: float = 0.04,
    r_tim_k_per_w: float = 0.02,
    geometry: dict[str, Any] | None = None,
    sensitivity: bool = False,
) -> dict:
    try:
        payload = AnalyzeColdplateInput(
            heat_load_w=heat_load_w,
            flow_rate_lpm=flow_rate_lpm,
            inlet_temp_c=inlet_temp_c,
            ambient_temp_c=ambient_temp_c,
            coolant=coolant,
            r_jc_k_per_w=r_jc_k_per_w,
            r_tim_k_per_w=r_tim_k_per_w,
            geometry=_geometry_from_dict(geometry),
        )
    except ValidationError as exc:
        return {"error": exc.errors()}
    result = analyze(payload)
    if sensitivity:
        result = result.model_copy(update={"sensitivity": compute_sensitivity(payload)})
    return result.model_dump()


def compare_coolants_impl(
    heat_load_w: float,
    flow_rate_lpm: float,
    inlet_temp_c: float = 25.0,
    ambient_temp_c: float = 25.0,
    r_jc_k_per_w: float = 0.04,
    r_tim_k_per_w: float = 0.02,
    geometry: dict[str, Any] | None = None,
) -> dict:
    try:
        payload = CompareCoolantsInput(
            heat_load_w=heat_load_w,
            flow_rate_lpm=flow_rate_lpm,
            inlet_temp_c=inlet_temp_c,
            ambient_temp_c=ambient_temp_c,
            r_jc_k_per_w=r_jc_k_per_w,
            r_tim_k_per_w=r_tim_k_per_w,
            geometry=_geometry_from_dict(geometry),
        )
    except ValidationError as exc:
        return {"error": exc.errors()}

    base = payload.model_dump()
    comparisons: dict[str, dict] = {}
    for coolant in COOLANTS:
        point = AnalyzeColdplateInput(coolant=coolant, **base)
        comparisons[coolant] = analyze(point).model_dump()

    return {"inputs": payload.model_dump(), "results": comparisons}


def optimize_flow_rate_impl(
    heat_load_w: float,
    max_junction_temp_c: float,
    coolant: CoolantName = "water",
    inlet_temp_c: float = 25.0,
    ambient_temp_c: float = 25.0,
    flow_min_lpm: float = 1.0,
    flow_max_lpm: float = 40.0,
    r_jc_k_per_w: float = 0.04,
    r_tim_k_per_w: float = 0.02,
    geometry: dict[str, Any] | None = None,
    margin_c: float = 0.0,
) -> dict:
    try:
        payload = OptimizeFlowRateInput(
            heat_load_w=heat_load_w,
            max_junction_temp_c=max_junction_temp_c,
            margin_c=margin_c,
            coolant=coolant,
            inlet_temp_c=inlet_temp_c,
            ambient_temp_c=ambient_temp_c,
            flow_min_lpm=flow_min_lpm,
            flow_max_lpm=flow_max_lpm,
            r_jc_k_per_w=r_jc_k_per_w,
            r_tim_k_per_w=r_tim_k_per_w,
            geometry=_geometry_from_dict(geometry),
        )
    except ValidationError as exc:
        return {"error": exc.errors()}

    flow_lpm, result = optimize_flow(payload)
    return {
        "target_max_junction_temp_c": payload.max_junction_temp_c,
        "effective_target_c": payload.max_junction_temp_c - payload.margin_c,
        "margin_c": payload.margin_c,
        "minimum_flow_rate_lpm": flow_lpm,
        "met_target": result is not None,
        "analysis_at_minimum_flow": result.model_dump() if result else None,
    }


@mcp.tool(name="analyze_coldplate")
def analyze_coldplate(
    heat_load_w: float,
    flow_rate_lpm: float,
    inlet_temp_c: float = 25.0,
    ambient_temp_c: float = 25.0,
    coolant: CoolantName = "water",
    r_jc_k_per_w: float = 0.04,
    r_tim_k_per_w: float = 0.02,
    geometry: dict[str, Any] | None = None,
    sensitivity: bool = False,
):
    """Calculate junction temperature, thermal resistances, and pressure drop for a liquid-cooled cold plate.

    Uses a 1D thermal resistance network (junction -> case -> TIM -> base -> convection)
    with Dittus-Boelter convection and Darcy-Weisbach pressure drop.
    Supports water and 50/50 glycol coolants. Returns model-applicability notices
    and low-Reynolds-number warnings. Temperature acceptance requires a caller's
    component-specific limit or the decision-report tool.

    Set sensitivity=True to include finite-difference partial derivatives and
    illustrative perturbations: ∂Tj/∂Q, ∂Tj/∂R_tim, ±20% R_jc variation,
    and Tj rise when R_tim is doubled. These are not measured uncertainty or lifetime estimates.
    """
    return analyze_coldplate_impl(
        heat_load_w,
        flow_rate_lpm,
        inlet_temp_c,
        ambient_temp_c,
        coolant,
        r_jc_k_per_w,
        r_tim_k_per_w,
        geometry,
        sensitivity,
    )


@mcp.tool(name="compare_coolants")
def compare_coolants(
    heat_load_w: float,
    flow_rate_lpm: float,
    inlet_temp_c: float = 25.0,
    ambient_temp_c: float = 25.0,
    r_jc_k_per_w: float = 0.04,
    r_tim_k_per_w: float = 0.02,
    geometry: dict[str, Any] | None = None,
):
    """Compare thermal and hydraulic performance of water vs 50/50 glycol under identical conditions.

    Runs analyze_coldplate for each coolant and returns side-by-side results
    including junction temperature, pressure drop, and pump power for each.
    """
    return compare_coolants_impl(
        heat_load_w,
        flow_rate_lpm,
        inlet_temp_c,
        ambient_temp_c,
        r_jc_k_per_w,
        r_tim_k_per_w,
        geometry,
    )


@mcp.tool(name="optimize_flow_rate")
def optimize_flow_rate(
    heat_load_w: float,
    max_junction_temp_c: float,
    coolant: CoolantName = "water",
    inlet_temp_c: float = 25.0,
    ambient_temp_c: float = 25.0,
    flow_min_lpm: float = 1.0,
    flow_max_lpm: float = 40.0,
    r_jc_k_per_w: float = 0.04,
    r_tim_k_per_w: float = 0.02,
    geometry: dict[str, Any] | None = None,
    margin_c: float = 0.0,
):
    """Find the minimum coolant flow rate that keeps junction temperature at or below a target.

    Uses binary search between flow_min_lpm and flow_max_lpm.
    Returns the minimum flow rate, whether the target was met,
    and the full thermal analysis at that operating point.

    margin_c: Optional safety margin in °C. The optimizer targets
    (max_junction_temp_c - margin_c) as the effective ceiling.
    Choose the guardband from component and operating evidence; the model
    does not establish a universal margin or service-life forecast.
    """
    return optimize_flow_rate_impl(
        heat_load_w,
        max_junction_temp_c,
        coolant,
        inlet_temp_c,
        ambient_temp_c,
        flow_min_lpm,
        flow_max_lpm,
        r_jc_k_per_w,
        r_tim_k_per_w,
        geometry,
        margin_c,
    )


def analyze_rack_impl(
    gpu_count: int,
    topology: RackTopology,
    heat_load_per_gpu_w: float,
    total_flow_lpm: float,
    cdu_supply_temp_c: float = 25.0,
    ambient_temp_c: float | None = None,
    coolant: CoolantName = "water",
    r_jc_k_per_w: float = 0.04,
    r_tim_k_per_w: float = 0.02,
    geometry: dict[str, Any] | None = None,
) -> dict:
    try:
        payload = AnalyzeRackInput(
            gpu_count=gpu_count,
            topology=topology,
            heat_load_per_gpu_w=heat_load_per_gpu_w,
            total_flow_lpm=total_flow_lpm,
            cdu_supply_temp_c=cdu_supply_temp_c,
            ambient_temp_c=ambient_temp_c,
            coolant=coolant,
            r_jc_k_per_w=r_jc_k_per_w,
            r_tim_k_per_w=r_tim_k_per_w,
            geometry=_geometry_from_dict(geometry),
        )
    except ValidationError as exc:
        return {"error": exc.errors()}
    try:
        return analyze_rack(payload).model_dump()
    except ValidationError as exc:
        # analyze_rack builds per-GPU AnalyzeColdplateInput objects internally;
        # series mode can push a downstream GPU's inlet_temp_c above the schema
        # limit (>80°C) even when the top-level AnalyzeRackInput is valid.
        return {"error": exc.errors()}


@mcp.tool(name="analyze_rack")
def analyze_rack_tool(
    gpu_count: int,
    topology: RackTopology,
    heat_load_per_gpu_w: float,
    total_flow_lpm: float,
    cdu_supply_temp_c: float = 25.0,
    ambient_temp_c: float | None = None,
    coolant: CoolantName = "water",
    r_jc_k_per_w: float = 0.04,
    r_tim_k_per_w: float = 0.02,
    geometry: dict[str, Any] | None = None,
):
    """Rack-level thermal analysis for N identical GPU cold plates.

    Models steady-state heat removal across a full rack using either series
    or parallel plumbing topology.

    Series: coolant flows through each cold plate in sequence. Each GPU's
    inlet temperature equals the previous GPU's outlet. Pressure drop accumulates
    (ΔP_total = N × ΔP_per_plate). Hottest GPU is always the last in the chain.

    Parallel: coolant splits equally to all cold plates. All GPUs share the
    same inlet temperature. Flow per GPU = total_flow_lpm / gpu_count.
    System ΔP equals per-plate ΔP (not cumulative).

    Assumptions: identical GPUs, uniform flow distribution, no manifold losses.
    Ambient temperature is optional; if omitted, rack analysis defaults ambient
    reference to cdu_supply_temp_c.

    Args:
        gpu_count: Number of GPU cold plates in the rack (1–256).
        topology: Plumbing layout — "series" or "parallel".
        heat_load_per_gpu_w: Thermal design power per GPU in watts.
        total_flow_lpm: Total CDU coolant flow rate in L/min.
        cdu_supply_temp_c: CDU supply temperature at rack inlet in °C.
        ambient_temp_c: Optional ambient reference temperature in °C.
            Defaults to cdu_supply_temp_c when omitted.
        coolant: Coolant type — "water" or "glycol50".
        r_jc_k_per_w: Junction-to-case thermal resistance per GPU in K/W.
        r_tim_k_per_w: TIM resistance per GPU in K/W.
        geometry: Optional cold plate geometry overrides (same for all GPUs).
    """
    return analyze_rack_impl(
        gpu_count,
        topology,
        heat_load_per_gpu_w,
        total_flow_lpm,
        cdu_supply_temp_c,
        ambient_temp_c,
        coolant,
        r_jc_k_per_w,
        r_tim_k_per_w,
        geometry,
    )


def generate_decision_report_impl(
    chip_label: str | None = None,
    heat_load_w: float | None = None,
    gpu_count: int | None = None,
    topology: RackTopology | None = None,
    target_junction_temp_c: float | None = None,
    margin_c: float | None = None,
    coolant: CoolantName | None = None,
    inlet_temp_c: float | None = None,
    flow_rate_lpm: float | None = None,
    geometry: dict[str, Any] | None = None,
    r_jc_k_per_w: float | None = None,
    r_tim_k_per_w: float | None = None,
    stress_scenarios: dict[str, Any] | None = None,
    input_source_notes: dict[str, str] | None = None,
) -> dict:
    # Domain defaults belong to DecisionScenario so omission remains observable.
    supplied = {
        "chip_label": chip_label,
        "heat_load_w": heat_load_w,
        "gpu_count": gpu_count,
        "topology": topology,
        "target_junction_temp_c": target_junction_temp_c,
        "margin_c": margin_c,
        "coolant": coolant,
        "inlet_temp_c": inlet_temp_c,
        "flow_rate_lpm": flow_rate_lpm,
        "geometry": geometry,
        "r_jc_k_per_w": r_jc_k_per_w,
        "r_tim_k_per_w": r_tim_k_per_w,
        "stress_scenarios": stress_scenarios,
        "input_source_notes": input_source_notes,
    }
    try:
        scenario = DecisionScenario.model_validate({key: value for key, value in supplied.items() if value is not None})
        return generate_decision_report(scenario).model_dump(mode="json")
    except ValidationError as exc:
        return {"error": json.loads(exc.json())}


@mcp.tool(name="generate_decision_report")
def generate_decision_report_tool(
    chip_label: str | None = None,
    heat_load_w: float | None = None,
    gpu_count: int | None = None,
    topology: RackTopology | None = None,
    target_junction_temp_c: float | None = None,
    margin_c: float | None = None,
    coolant: CoolantName | None = None,
    inlet_temp_c: float | None = None,
    flow_rate_lpm: float | None = None,
    geometry: dict[str, Any] | None = None,
    r_jc_k_per_w: float | None = None,
    r_tim_k_per_w: float | None = None,
    stress_scenarios: dict[str, Any] | None = None,
    input_source_notes: dict[str, str] | None = None,
):
    """Return a schema-v2 thermal screening report, not a hardware recommendation.

    Omitted or null arguments use DecisionScenario defaults: 700 W, one GPU,
    parallel, 83°C limit, 5°C caller guardband, water at 25°C, R_jc=0.04 K/W,
    R_tim=0.02 K/W, default geometry. Null flow requests a thermal search;
    a supplied flow is evaluated unchanged in LPM per GPU.

    Read status and evaluated_point before using numbers. A failed series
    candidate does not prove architecture infeasibility. Unavailable results
    are null; system hydraulic feasibility and overall risk are not assessed.
    The model has not been validated against measured hardware.

    stress_scenarios accepts r_jc_variation_fraction, r_tim_multiplier,
    heat_load_delta_w, and supply_temp_delta_c. These are independent,
    illustrative perturbations, not probability or lifetime predictions.
    input_source_notes maps input field paths (including geometry fields) to
    caller-provided provenance notes; supplied values are not automatically
    verified. Explicit values equal to defaults retain supplied provenance.
    """
    return generate_decision_report_impl(
        chip_label=chip_label,
        heat_load_w=heat_load_w,
        gpu_count=gpu_count,
        topology=topology,
        target_junction_temp_c=target_junction_temp_c,
        margin_c=margin_c,
        coolant=coolant,
        inlet_temp_c=inlet_temp_c,
        flow_rate_lpm=flow_rate_lpm,
        geometry=geometry,
        r_jc_k_per_w=r_jc_k_per_w,
        r_tim_k_per_w=r_tim_k_per_w,
        stress_scenarios=stress_scenarios,
        input_source_notes=input_source_notes,
    )


if __name__ == "__main__":
    mcp.run()
