"""MCP layer smoke and error-path tests.

Tests the _impl functions in mcp_server.py — which are the thin wrappers
that validate inputs and delegate to physics.py. These tests check:
  - Happy path: expected keys present with correct types
  - Error paths: ValidationError returns {"error": [...]} dict
  - Depth checks: result values are populated (not just keys present)
  - Geometry passthrough: non-default geometry propagates to physics

No new physics here — correctness is covered in test_physics_behavior.py.
"""

from thermal_mcp_server import mcp_server


# ---------------------------------------------------------------------------
# analyze_coldplate_impl
# ---------------------------------------------------------------------------

def test_analyze_tool_shape():
    out = mcp_server.analyze_coldplate_impl(heat_load_w=700, flow_rate_lpm=8, coolant="water")
    assert "junction_temp_c" in out
    assert "pressure_drop_pa" in out
    assert "resistances_k_per_w" in out


def test_analyze_coldplate_error_negative_heat_load():
    out = mcp_server.analyze_coldplate_impl(heat_load_w=-1, flow_rate_lpm=8)
    assert "error" in out
    assert isinstance(out["error"], list)
    assert len(out["error"]) > 0


def test_analyze_coldplate_error_invalid_coolant():
    out = mcp_server.analyze_coldplate_impl(heat_load_w=700, flow_rate_lpm=8, coolant="helium")
    assert "error" in out


def test_analyze_coldplate_error_zero_flow():
    out = mcp_server.analyze_coldplate_impl(heat_load_w=700, flow_rate_lpm=0)
    assert "error" in out


def test_analyze_coldplate_geometry_passthrough():
    """Non-default geometry (20 channels) must propagate and change Reynolds number."""
    default_out = mcp_server.analyze_coldplate_impl(heat_load_w=700, flow_rate_lpm=8)
    custom_out = mcp_server.analyze_coldplate_impl(
        heat_load_w=700,
        flow_rate_lpm=8,
        geometry={"channel_count": 20},  # fewer channels → higher velocity → higher Re
    )
    # 20 channels: twice the velocity of 40 channels → Re doubles
    assert custom_out["reynolds"] > default_out["reynolds"] * 1.5


def test_analyze_coldplate_geometry_extra_key_rejected():
    """Geometry with unknown key must return error (extra='forbid' on Geometry model)."""
    out = mcp_server.analyze_coldplate_impl(
        heat_load_w=700,
        flow_rate_lpm=8,
        geometry={"channel_count": 40, "nonexistent_field": 99},
    )
    assert "error" in out


# ---------------------------------------------------------------------------
# compare_coolants_impl
# ---------------------------------------------------------------------------

def test_compare_tool_shape():
    out = mcp_server.compare_coolants_impl(heat_load_w=700, flow_rate_lpm=8)
    assert set(out["results"].keys()) == {"water", "glycol50"}


def test_compare_coolants_depth_check():
    """Both coolant results must contain actual analysis fields, not just keys."""
    out = mcp_server.compare_coolants_impl(heat_load_w=700, flow_rate_lpm=8)
    for coolant in ("water", "glycol50"):
        result = out["results"][coolant]
        assert "junction_temp_c" in result
        assert "pressure_drop_pa" in result
        assert "reynolds" in result
        assert isinstance(result["junction_temp_c"], float)
        assert result["junction_temp_c"] > 0


def test_compare_coolants_glycol_hotter_than_water():
    """Glycol50 has lower thermal conductivity → higher junction temp at same flow."""
    out = mcp_server.compare_coolants_impl(heat_load_w=700, flow_rate_lpm=8)
    tj_water = out["results"]["water"]["junction_temp_c"]
    tj_glycol = out["results"]["glycol50"]["junction_temp_c"]
    assert tj_glycol > tj_water


def test_compare_coolants_error_negative_heat_load():
    out = mcp_server.compare_coolants_impl(heat_load_w=-1, flow_rate_lpm=8)
    assert "error" in out


def test_compare_coolants_inputs_echoed():
    """Inputs dict must be present in return value."""
    out = mcp_server.compare_coolants_impl(heat_load_w=500, flow_rate_lpm=6)
    assert "inputs" in out
    assert out["inputs"]["heat_load_w"] == 500
    assert out["inputs"]["flow_rate_lpm"] == 6


# ---------------------------------------------------------------------------
# optimize_flow_rate_impl
# ---------------------------------------------------------------------------

def test_optimize_tool_shape():
    out = mcp_server.optimize_flow_rate_impl(heat_load_w=700, max_junction_temp_c=85, coolant="water")
    assert "minimum_flow_rate_lpm" in out
    assert "analysis_at_minimum_flow" in out


def test_optimize_feasible_target_met():
    """Achievable target: met_target=True and analysis populated."""
    out = mcp_server.optimize_flow_rate_impl(heat_load_w=700, max_junction_temp_c=85, coolant="water")
    assert out["met_target"] is True
    assert out["analysis_at_minimum_flow"] is not None
    assert "junction_temp_c" in out["analysis_at_minimum_flow"]
    tj = out["analysis_at_minimum_flow"]["junction_temp_c"]
    assert tj <= 85.0 + 0.01  # binary search result must satisfy the constraint


def test_optimize_infeasible_target():
    """Target so low (25°C junction with 700W heat load) that even max flow can't meet it."""
    out = mcp_server.optimize_flow_rate_impl(
        heat_load_w=700,
        max_junction_temp_c=25,  # physically impossible given 25°C inlet
        coolant="water",
        flow_max_lpm=40.0,
    )
    assert out["met_target"] is False
    assert out["analysis_at_minimum_flow"] is None


def test_optimize_flow_range_invalid():
    """flow_max_lpm <= flow_min_lpm must return error."""
    out = mcp_server.optimize_flow_rate_impl(
        heat_load_w=700,
        max_junction_temp_c=85,
        flow_min_lpm=10.0,
        flow_max_lpm=5.0,  # invalid: max < min
    )
    assert "error" in out


def test_optimize_target_echoed():
    """target_max_junction_temp_c must be echoed in output."""
    out = mcp_server.optimize_flow_rate_impl(heat_load_w=700, max_junction_temp_c=80)
    assert out["target_max_junction_temp_c"] == 80


# ---------------------------------------------------------------------------
# analyze_rack_impl
# ---------------------------------------------------------------------------

def test_analyze_rack_smoke_series():
    """Basic series rack: output keys and types correct."""
    out = mcp_server.analyze_rack_impl(
        gpu_count=8,
        topology="series",
        heat_load_per_gpu_w=700,
        total_flow_lpm=64,
    )
    assert "max_junction_temp_c" in out
    assert "total_pressure_drop_pa" in out
    assert "total_pump_power_w" in out
    assert "cdu_outlet_temp_c" in out
    assert "per_gpu_junction_temps_c" in out
    assert len(out["per_gpu_junction_temps_c"]) == 8
    assert out["topology"] == "series"
    assert out["gpu_count"] == 8


def test_analyze_rack_smoke_parallel():
    """Basic parallel rack: system ΔP equals single plate ΔP, all Tj identical."""
    out = mcp_server.analyze_rack_impl(
        gpu_count=8,
        topology="parallel",
        heat_load_per_gpu_w=700,
        total_flow_lpm=64,
    )
    assert out["topology"] == "parallel"
    tjs = out["per_gpu_junction_temps_c"]
    assert all(abs(tj - tjs[0]) < 0.001 for tj in tjs), "parallel: all GPUs same Tj"


def test_analyze_rack_error_invalid_topology():
    """Invalid topology string must return error."""
    out = mcp_server.analyze_rack_impl(
        gpu_count=8,
        topology="diagonal",  # invalid
        heat_load_per_gpu_w=700,
        total_flow_lpm=64,
    )
    assert "error" in out


def test_analyze_rack_error_gpu_count_out_of_range():
    """gpu_count=0 must return error (ge=1 constraint)."""
    out = mcp_server.analyze_rack_impl(
        gpu_count=0,
        topology="series",
        heat_load_per_gpu_w=700,
        total_flow_lpm=64,
    )
    assert "error" in out


def test_analyze_rack_geometry_passthrough():
    """Non-default geometry propagates into rack analysis (different Re → different Tj)."""
    default_out = mcp_server.analyze_rack_impl(
        gpu_count=4, topology="parallel", heat_load_per_gpu_w=700, total_flow_lpm=32
    )
    custom_out = mcp_server.analyze_rack_impl(
        gpu_count=4,
        topology="parallel",
        heat_load_per_gpu_w=700,
        total_flow_lpm=32,
        geometry={"channel_count": 20},  # higher velocity → better convection → lower Tj
    )
    assert custom_out["max_junction_temp_c"] != default_out["max_junction_temp_c"]
