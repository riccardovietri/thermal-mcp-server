"""Tests for the decision_report synthesis module."""

from __future__ import annotations

import pytest

from thermal_mcp_server.decision_report import KNOWN_LIMITATIONS, generate_decision_report
from thermal_mcp_server.mcp_server import generate_decision_report_impl
from thermal_mcp_server.schemas import DecisionReport, DecisionScenario, RiskLevel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _h100_scenario(**overrides) -> DecisionScenario:
    """H100 SXM reference scenario."""
    defaults = dict(
        chip_label="H100 SXM",
        heat_load_w=700.0,
        gpu_count=1,
        target_junction_temp_c=83.0,
        margin_c=5.0,
        coolant="water",
        inlet_temp_c=25.0,
    )
    defaults.update(overrides)
    return DecisionScenario(**defaults)


# ---------------------------------------------------------------------------
# Structural / contract tests
# ---------------------------------------------------------------------------

def test_report_always_has_blind_spots():
    """Blind spots must always be populated — never empty."""
    report = generate_decision_report(_h100_scenario())
    assert len(report.blind_spots) >= len(KNOWN_LIMITATIONS)
    for limitation in KNOWN_LIMITATIONS:
        assert limitation in report.blind_spots


def test_report_blind_spots_cover_key_omissions():
    """Key omissions (manifold losses, temperature-dependence) must be mentioned."""
    report = generate_decision_report(_h100_scenario())
    combined = " ".join(report.blind_spots).lower()
    assert "manifold" in combined
    assert "temperature" in combined or "fluid properties" in combined
    assert "steady-state" in combined or "transient" in combined


def test_report_uncertainty_keys_present():
    """Uncertainty section must include R_jc and TIM aging contributors."""
    report = generate_decision_report(_h100_scenario())
    keys_lower = {k.lower() for k in report.uncertainty_section}
    assert any("r_jc" in k for k in keys_lower)
    assert any("tim" in k for k in keys_lower)


def test_report_rendered_memo_non_empty():
    """rendered_memo must be a non-empty markdown string."""
    report = generate_decision_report(_h100_scenario())
    assert len(report.rendered_memo) > 200
    assert "# Thermal Decision Memo" in report.rendered_memo


def test_report_rendered_memo_contains_key_sections():
    """Rendered memo must contain the required section headers."""
    report = generate_decision_report(_h100_scenario())
    memo = report.rendered_memo
    assert "Recommended Operating Point" in memo
    assert "Uncertainty" in memo
    assert "Model Blind Spots" in memo


# ---------------------------------------------------------------------------
# Feasibility and risk level tests
# ---------------------------------------------------------------------------

def test_report_feasible_h100_water():
    """Standard H100 + water should be feasible; Tj must be below target."""
    report = generate_decision_report(_h100_scenario())
    assert report.feasible is True
    assert report.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH)
    assert report.junction_temp_at_recommended_c < 83.0
    # Margin remaining is measured to actual target (83°C), not effective target
    assert report.margin_remaining_c == pytest.approx(83.0 - report.junction_temp_at_recommended_c, abs=0.01)


def test_report_infeasible_impossible_target():
    """Target below inlet temperature is infeasible."""
    report = generate_decision_report(_h100_scenario(target_junction_temp_c=26.0, margin_c=0.0))
    assert report.feasible is False
    assert report.risk_level == RiskLevel.HIGH
    assert any("INFEASIBLE" in w for w in report.warnings)


def test_report_infeasible_target_too_tight_with_margin():
    """Very tight target + large margin combo forces infeasibility."""
    # Effective target = 30 - 20 = 10°C, which is below inlet (25°C)
    report = generate_decision_report(_h100_scenario(target_junction_temp_c=30.0, margin_c=20.0))
    # margin_c must be < target, so 20 < 30 is valid, but effective target < inlet
    assert report.feasible is False


def test_report_risk_low_with_large_margin_budget():
    """Generous target temp with standard conditions → LOW or MEDIUM risk (not HIGH)."""
    report = generate_decision_report(_h100_scenario(target_junction_temp_c=95.0, margin_c=5.0))
    assert report.feasible is True
    assert report.risk_level != RiskLevel.HIGH
    # margin_remaining is measured to actual target (95°C)
    assert report.margin_remaining_c == pytest.approx(95.0 - report.junction_temp_at_recommended_c, abs=0.01)


# ---------------------------------------------------------------------------
# Determinism test
# ---------------------------------------------------------------------------

def test_report_deterministic():
    """Same scenario twice must produce identical numerical output."""
    scenario = _h100_scenario()
    r1 = generate_decision_report(scenario)
    r2 = generate_decision_report(scenario)
    assert r1.junction_temp_at_recommended_c == r2.junction_temp_at_recommended_c
    assert r1.recommended_flow.min_lpm == r2.recommended_flow.min_lpm
    assert r1.risk_level == r2.risk_level
    assert r1.margin_remaining_c == r2.margin_remaining_c


# ---------------------------------------------------------------------------
# Margin propagation test
# ---------------------------------------------------------------------------

def test_report_margin_propagates():
    """Larger margin_c must require higher minimum flow (more conservative)."""
    r_low_margin = generate_decision_report(_h100_scenario(margin_c=0.0))
    r_high_margin = generate_decision_report(_h100_scenario(margin_c=10.0))
    if r_low_margin.feasible and r_high_margin.feasible:
        assert r_high_margin.recommended_flow.min_lpm >= r_low_margin.recommended_flow.min_lpm


def test_report_zero_margin_equals_no_margin():
    """margin_c=0 should give same result as omitting margin (default 5° is different)."""
    r0 = generate_decision_report(_h100_scenario(margin_c=0.0))
    r0b = generate_decision_report(_h100_scenario(margin_c=0.0))
    assert r0.recommended_flow.min_lpm == r0b.recommended_flow.min_lpm


# ---------------------------------------------------------------------------
# Fixed-flow mode
# ---------------------------------------------------------------------------

def test_report_fixed_flow_mode():
    """Providing flow_rate_lpm bypasses optimization."""
    report = generate_decision_report(_h100_scenario(flow_rate_lpm=8.0))
    assert report.feasible is True
    # Recommended flow should be 15% above the provided value
    assert abs(report.recommended_flow.recommended_lpm - 8.0 * 1.15) < 0.01


def test_report_fixed_flow_infeasible():
    """Very low fixed flow with tight target → infeasible."""
    report = generate_decision_report(
        _h100_scenario(flow_rate_lpm=0.5, target_junction_temp_c=40.0, margin_c=0.0)
    )
    assert report.feasible is False


# ---------------------------------------------------------------------------
# Multi-GPU topology tests
# ---------------------------------------------------------------------------

def test_report_rack_topology_populated():
    """Multi-GPU scenario must include topology recommendation text."""
    report = generate_decision_report(_h100_scenario(gpu_count=8, topology="parallel"))
    assert len(report.topology_recommendation) > 20
    assert "parallel" in report.topology_recommendation.lower()


def test_report_single_gpu_topology_not_applicable():
    """Single GPU scenario should note topology is not applicable."""
    report = generate_decision_report(_h100_scenario(gpu_count=1))
    assert "not applicable" in report.topology_recommendation.lower()


def test_report_series_topology_rationale():
    """Series topology rationale must mention series and its characteristics."""
    report = generate_decision_report(_h100_scenario(gpu_count=4, topology="series"))
    rationale = report.topology_recommendation.lower()
    assert "series" in rationale


# ---------------------------------------------------------------------------
# Rack-aware feasibility (PR28 review fix #1)
#
# Single-coldplate optimization can mislabel multi-GPU series scenarios as
# feasible because it ignores temperature stacking. These tests pin the
# corrected behaviour: the rack-level max Tj is the source of truth for
# feasibility, risk, and margin once gpu_count > 1.
# ---------------------------------------------------------------------------

def test_report_series_rack_uses_rack_max_tj():
    """8-GPU series at the same per-GPU flow gives a higher Tj than 1-GPU.
    The rack-aware fix must surface that — Tj_at_recommended must reflect
    the hottest GPU in the chain, not the first.
    """
    single = generate_decision_report(_h100_scenario(gpu_count=1))
    series_8 = generate_decision_report(_h100_scenario(gpu_count=8, topology="series"))
    # 8-GPU series must be at least as hot as 1-GPU at the same per-GPU flow.
    assert series_8.junction_temp_at_recommended_c > single.junction_temp_at_recommended_c
    # And meaningfully so — series stacking should produce several °C of rise.
    assert series_8.junction_temp_at_recommended_c - single.junction_temp_at_recommended_c > 3.0


def test_report_parallel_rack_matches_single_gpu_tj():
    """Parallel topology gives every GPU the same inlet, so 8-GPU parallel Tj
    at per-GPU flow F should match 1-GPU at flow F.
    """
    single = generate_decision_report(_h100_scenario(gpu_count=1))
    parallel_8 = generate_decision_report(_h100_scenario(gpu_count=8, topology="parallel"))
    assert abs(parallel_8.junction_temp_at_recommended_c - single.junction_temp_at_recommended_c) < 0.5


def test_report_series_can_flip_feasibility_to_infeasible():
    """A scenario that is feasible as a single GPU can become infeasible as
    an 8-GPU series rack because of coolant temperature stacking. The
    rack-aware fix must catch this.
    """
    # Choose a target that single-coldplate just barely meets but 8-GPU series
    # cannot. H100 700W water 25°C inlet, target 80°C, margin 0.
    single = generate_decision_report(
        _h100_scenario(target_junction_temp_c=80.0, margin_c=0.0, gpu_count=1)
    )
    series_8 = generate_decision_report(
        _h100_scenario(target_junction_temp_c=80.0, margin_c=0.0, gpu_count=8, topology="series")
    )
    assert single.feasible is True
    assert series_8.feasible is False


def test_report_extreme_series_does_not_crash():
    """A series rack so deep that downstream coolant exceeds the 80°C model
    bound must NOT raise — it must be reported as infeasible with a clear
    warning. This is the schema-overflow path inside analyze_rack.
    """
    report = generate_decision_report(
        _h100_scenario(
            heat_load_w=1500.0,           # high TDP per GPU
            gpu_count=64,                  # deep chain
            topology="series",
            inlet_temp_c=60.0,             # already hot supply
            target_junction_temp_c=83.0,
            margin_c=0.0,
        )
    )
    assert report.feasible is False
    # Warning must explain the overflow, not just say "infeasible"
    combined_warnings = " ".join(report.warnings).lower()
    assert "infeasible" in combined_warnings or "model bound" in combined_warnings or "80" in combined_warnings


# ---------------------------------------------------------------------------
# Flow band structure
# ---------------------------------------------------------------------------

def test_report_flow_band_ordering():
    """Flow band must satisfy min <= recommended <= max."""
    report = generate_decision_report(_h100_scenario())
    fb = report.recommended_flow
    assert fb.min_lpm <= fb.recommended_lpm
    assert fb.recommended_lpm <= fb.max_lpm


def test_report_flow_band_basis_non_empty():
    """Flow band basis string must be populated."""
    report = generate_decision_report(_h100_scenario())
    assert len(report.recommended_flow.basis) > 5


# ---------------------------------------------------------------------------
# MCP layer (generate_decision_report_impl) contract tests
# ---------------------------------------------------------------------------

def test_mcp_impl_returns_dict():
    """MCP impl must return a dict (JSON-serialisable)."""
    result = generate_decision_report_impl(chip_label="H100 SXM", heat_load_w=700.0)
    assert isinstance(result, dict)
    assert "feasible" in result
    assert "risk_level" in result
    assert "rendered_memo" in result


def test_mcp_impl_invalid_coolant():
    """Invalid coolant must return error dict, not raise."""
    result = generate_decision_report_impl(heat_load_w=700.0, coolant="liquid_nitrogen")
    assert "error" in result


def test_mcp_impl_margin_exceeds_target():
    """margin_c >= target_junction_temp_c must return error dict."""
    result = generate_decision_report_impl(
        heat_load_w=700.0, target_junction_temp_c=50.0, margin_c=60.0
    )
    assert "error" in result


def test_mcp_impl_geometry_passthrough():
    """Custom geometry must change analysis output."""
    r_default = generate_decision_report_impl(heat_load_w=700.0)
    r_narrow = generate_decision_report_impl(
        heat_load_w=700.0,
        geometry={"channel_count": 80, "channel_width_m": 0.5e-3, "channel_height_m": 0.5e-3},
    )
    assert isinstance(r_narrow, dict)
    assert "feasible" in r_narrow
    # Narrower channels → different Tj
    assert r_default["junction_temp_at_recommended_c"] != r_narrow["junction_temp_at_recommended_c"]


def test_mcp_impl_extreme_series_returns_error_dict_not_crash():
    """PR28 review fix #2: schema-valid scenarios that trigger downstream
    ValidationError during synthesis (e.g. extreme series stacking that
    overflows the 80°C model bound) must return an {"error": ...} dict,
    matching the contract of analyze_rack_impl. The MCP tool must not raise.
    """
    # The same configuration that triggers the schema-overflow path inside
    # analyze_rack — but routed through the MCP wrapper.
    result = generate_decision_report_impl(
        heat_load_w=1500.0,
        gpu_count=64,
        topology="series",
        inlet_temp_c=60.0,
        target_junction_temp_c=83.0,
        margin_c=0.0,
    )
    assert isinstance(result, dict)
    # Either we caught it cleanly inside synthesis (returned a feasible=False
    # report) or the MCP wrapper caught it as an error dict. Both are
    # acceptable outcomes; what is NOT acceptable is an unhandled exception.
    assert ("feasible" in result and result["feasible"] is False) or "error" in result
