"""MCP server exposing three thermal analysis tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from pydantic import ValidationError

from .physics import COOLANTS, analyze, optimize_flow
from .schemas import AnalyzeColdplateInput, CompareCoolantsInput, Geometry, OptimizeFlowRateInput

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
    return analyze(payload).model_dump()


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
) -> dict:
    try:
        payload = OptimizeFlowRateInput(
            heat_load_w=heat_load_w,
            max_junction_temp_c=max_junction_temp_c,
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
):
    """Calculate junction temperature, thermal resistances, and pressure drop for a liquid-cooled cold plate.

    Uses a 1D thermal resistance network (junction -> case -> TIM -> base -> convection)
    with Dittus-Boelter convection and Darcy-Weisbach pressure drop.
    Supports water and 50/50 glycol coolants. Returns warnings if junction temperature
    exceeds 85C or Reynolds number is dangerously low.
    """
    return analyze_coldplate_impl(
        heat_load_w, flow_rate_lpm, inlet_temp_c, ambient_temp_c,
        coolant, r_jc_k_per_w, r_tim_k_per_w, geometry,
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
):
    """Find the minimum coolant flow rate that keeps junction temperature at or below a target.

    Uses binary search between flow_min_lpm and flow_max_lpm.
    Returns the minimum flow rate, whether the target was met,
    and the full thermal analysis at that operating point.
    """
    return optimize_flow_rate_impl(
        heat_load_w, max_junction_temp_c, coolant, inlet_temp_c,
        ambient_temp_c, flow_min_lpm, flow_max_lpm,
        r_jc_k_per_w, r_tim_k_per_w, geometry,
    )


if __name__ == "__main__":
    mcp.run()
