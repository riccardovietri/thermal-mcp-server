from thermal_mcp_server import mcp_server


def test_analyze_tool_shape():
    out = mcp_server.analyze_coldplate_impl(heat_load_w=700, flow_rate_lpm=8, coolant="water")
    assert "junction_temp_c" in out
    assert "pressure_drop_pa" in out
    assert "resistances_k_per_w" in out


def test_compare_tool_shape():
    out = mcp_server.compare_coolants_impl(heat_load_w=700, flow_rate_lpm=8)
    assert set(out["results"].keys()) == {"water", "glycol50"}


def test_optimize_tool_shape():
    out = mcp_server.optimize_flow_rate_impl(heat_load_w=700, max_junction_temp_c=85, coolant="water")
    assert "minimum_flow_rate_lpm" in out
    assert "analysis_at_minimum_flow" in out
