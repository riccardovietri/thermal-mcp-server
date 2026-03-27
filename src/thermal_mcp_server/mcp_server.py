"""MCP server exposing three thermal analysis tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from pydantic import ValidationError

from .physics import COOLANTS, analyze, analyze_rack, compute_sensitivity, optimize_flow
from .schemas import AnalyzeColdplateInput, AnalyzeRackInput, CompareCoolantsInput, Geometry, OptimizeFlowRateInput

mcp = FastMCP("thermal-mcp-server")


def _geometry_from_dict(geometry: dict[str, Any] | None) -> Geometry:
    return Geometry(**(geometry or {}))


def analyze_coldplate_impl(
    heat_load_w: float,
    flow_rate_lpm: float,
    inlet_temp_c: float = 25.0,
    ambient_temp_c: float = 25.0,
    coolant: str = "water",
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
    coolant: str = "water",
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
    coolant: str = "water",
    r_jc_k_per_w: float = 0.04,
    r_tim_k_per_w: float = 0.02,
    geometry: dict[str, Any] | None = None,
    sensitivity: bool = False,
):
    """Calculate junction temperature, thermal resistances, and pressure drop for a liquid-cooled cold plate.

    Uses a 1D thermal resistance network (junction -> case -> TIM -> base -> convection)
    with Dittus-Boelter convection and Darcy-Weisbach pressure drop.
    Supports water and 50/50 glycol coolants. Returns warnings if junction temperature
    exceeds 85C or Reynolds number is dangerously low.

    Set sensitivity=True to include finite-difference partial derivatives and
    uncertainty bounds: ∂Tj/∂Q, ∂Tj/∂R_tim, ±20% R_jc manufacturing variation,
    and Tj rise from TIM pump-out degradation (R_tim doubles after 2-3 years).
    """
    return analyze_coldplate_impl(
        heat_load_w, flow_rate_lpm, inlet_temp_c, ambient_temp_c,
        coolant, r_jc_k_per_w, r_tim_k_per_w, geometry, sensitivity,
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
        heat_load_w, flow_rate_lpm, inlet_temp_c, ambient_temp_c,
        r_jc_k_per_w, r_tim_k_per_w, geometry,
    )


@mcp.tool(name="optimize_flow_rate")
def optimize_flow_rate(
    heat_load_w: float,
    max_junction_temp_c: float,
    coolant: str = "water",
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
    Recommended: ≥5°C to cover R_jc manufacturing variation (±20%)
    and TIM degradation over 2-3 years of field service.
    """
    return optimize_flow_rate_impl(
        heat_load_w, max_junction_temp_c, coolant, inlet_temp_c,
        ambient_temp_c, flow_min_lpm, flow_max_lpm,
        r_jc_k_per_w, r_tim_k_per_w, geometry, margin_c,
    )


def analyze_rack_impl(
    gpu_count: int,
    topology: str,
    heat_load_per_gpu_w: float,
    total_flow_lpm: float,
    cdu_supply_temp_c: float = 25.0,
    ambient_temp_c: float | None = None,
    coolant: str = "water",
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
    topology: str,
    heat_load_per_gpu_w: float,
    total_flow_lpm: float,
    cdu_supply_temp_c: float = 25.0,
    ambient_temp_c: float | None = None,
    coolant: str = "water",
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
        gpu_count, topology, heat_load_per_gpu_w, total_flow_lpm,
        cdu_supply_temp_c, ambient_temp_c, coolant, r_jc_k_per_w, r_tim_k_per_w, geometry,
    )


if __name__ == "__main__":
    mcp.run()
