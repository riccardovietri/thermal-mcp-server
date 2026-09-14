"""Contract and behavior tests for the schema-v2 decision report."""

from __future__ import annotations

import pytest

from thermal_mcp_server.decision_report import KNOWN_LIMITATIONS, generate_decision_report
from thermal_mcp_server.mcp_server import generate_decision_report_impl
from thermal_mcp_server.physics import analyze
from thermal_mcp_server.schemas import (
    AnalyzeColdplateInput,
    DecisionScenario,
    DecisionStatus,
    EvaluationMode,
)


def _scenario(**overrides) -> DecisionScenario:
    values = {
        "chip_label": "Illustrative 700 W accelerator",
        "heat_load_w": 700.0,
        "gpu_count": 1,
        "target_junction_temp_c": 83.0,
        "margin_c": 5.0,
        "coolant": "water",
        "inlet_temp_c": 25.0,
    }
    values.update(overrides)
    return DecisionScenario(**values)


def test_fixed_flow_is_evaluated_unchanged():
    report = generate_decision_report(_scenario(flow_rate_lpm=8.0))
    direct = analyze(
        AnalyzeColdplateInput(
            heat_load_w=700.0,
            flow_rate_lpm=8.0,
            inlet_temp_c=25.0,
            coolant="water",
        )
    )

    assert report.status == DecisionStatus.MEETS_TARGET
    assert report.evaluation_mode == EvaluationMode.FIXED_FLOW
    assert report.attempted_flow_lpm_per_gpu == 8.0
    assert report.flow_search is None
    assert report.evaluated_point is not None
    assert report.evaluated_point.role == "fixed_input"
    assert report.evaluated_point.flow_lpm_per_gpu == 8.0
    assert report.evaluated_point.junction_temp_c == pytest.approx(direct.junction_temp_c)
    assert report.evaluated_point.margin_to_limit_c == pytest.approx(83.0 - direct.junction_temp_c)
    assert report.evaluated_point.margin_to_criterion_c == pytest.approx(78.0 - direct.junction_temp_c)


def test_fixed_flow_failure_is_scoped_to_that_point():
    report = generate_decision_report(_scenario(flow_rate_lpm=0.5, target_junction_temp_c=40.0, margin_c=0.0))

    assert report.status == DecisionStatus.FAILS_AT_EVALUATED_FLOW
    assert report.evaluated_point is not None
    assert report.evaluated_point.role == "fixed_input"
    assert report.evaluated_point.meets_thermal_target is False
    assert any("another flow may work" in warning for warning in report.warnings)


def test_successful_single_plate_search_reports_model_minimum_without_multiplier():
    report = generate_decision_report(_scenario())

    assert report.status == DecisionStatus.MEETS_TARGET
    assert report.evaluation_mode == EvaluationMode.THERMAL_SEARCH
    assert report.flow_search is not None
    assert report.flow_search.scope == "single_plate"
    assert report.flow_search.minimum_feasible_lpm_per_gpu is not None
    assert report.evaluated_point is not None
    assert report.evaluated_point.role == "thermal_search_result"
    assert report.evaluated_point.flow_lpm_per_gpu == pytest.approx(report.flow_search.minimum_feasible_lpm_per_gpu)
    assert report.evaluated_point.meets_thermal_target is True


def test_failed_search_has_no_invented_recommendation():
    report = generate_decision_report(_scenario(heat_load_w=1200.0, target_junction_temp_c=75.0))

    assert report.status == DecisionStatus.NO_FEASIBLE_FLOW_IN_SEARCH_RANGE
    assert report.flow_search is not None
    assert report.flow_search.min_lpm_per_gpu == 0.5
    assert report.flow_search.max_lpm_per_gpu == 60.0
    assert report.flow_search.minimum_feasible_lpm_per_gpu is None
    assert report.evaluated_point is not None
    assert report.evaluated_point.role == "search_bound_diagnostic"
    assert report.evaluated_point.flow_lpm_per_gpu == 60.0
    assert report.evaluated_point.meets_thermal_target is False


def test_series_candidate_failure_is_undetermined_not_infeasible():
    report = generate_decision_report(_scenario(gpu_count=8, topology="series"))

    assert report.status == DecisionStatus.UNDETERMINED
    assert report.flow_search is not None
    assert report.flow_search.scope == "single_plate_candidate_for_series"
    assert report.flow_search.minimum_feasible_lpm_per_gpu is None
    assert report.evaluated_point is not None
    assert report.evaluated_point.role == "series_candidate"
    assert report.evaluated_point.meets_thermal_target is False
    assert any("no rack-wide search" in warning for warning in report.warnings)


def test_passing_series_candidate_does_not_claim_minimum_rack_flow():
    report = generate_decision_report(_scenario(gpu_count=2, topology="series", target_junction_temp_c=150.0))

    assert report.status == DecisionStatus.MEETS_TARGET
    assert report.evaluated_point is not None
    assert report.evaluated_point.role == "series_candidate"
    assert report.evaluated_point.meets_thermal_target is True
    assert report.flow_search is not None
    assert report.flow_search.minimum_feasible_lpm_per_gpu is None


def test_unsupported_series_rack_has_no_placeholder_point():
    report = generate_decision_report(_scenario(gpu_count=256, topology="series", flow_rate_lpm=8.0))

    assert report.status == DecisionStatus.UNDETERMINED
    assert report.attempted_flow_lpm_per_gpu == 8.0
    assert report.evaluated_point is None
    assert report.flow_search is None
    assert any("downstream inlet" in warning for warning in report.warnings)
    assert any("No temperature or thermal margin" in warning for warning in report.warnings)


def test_parallel_search_uses_per_gpu_flow_and_rack_point():
    report = generate_decision_report(_scenario(gpu_count=8, topology="parallel"))

    assert report.status == DecisionStatus.MEETS_TARGET
    assert report.flow_search is not None
    assert report.flow_search.scope == "parallel_rack"
    assert report.evaluated_point is not None
    assert report.evaluated_point.cdu_outlet_temp_c is not None
    assert report.evaluated_point.meets_thermal_target is True


def test_stress_scenarios_are_signed_independent_model_deltas():
    report = generate_decision_report(_scenario(flow_rate_lpm=8.0))
    stresses = {stress.name: stress for stress in report.stress_scenarios}

    assert set(stresses) == {
        "r_jc_minus_variation",
        "r_jc_plus_variation",
        "r_tim_multiplier",
        "heat_load_delta",
        "supply_temp_delta",
    }
    assert all(stress.status == "evaluated" for stress in stresses.values())
    assert stresses["r_jc_minus_variation"].signed_junction_delta_c == pytest.approx(-5.6)
    assert stresses["r_jc_plus_variation"].signed_junction_delta_c == pytest.approx(5.6)
    assert stresses["r_tim_multiplier"].signed_junction_delta_c == pytest.approx(14.0)
    assert stresses["supply_temp_delta"].signed_junction_delta_c == pytest.approx(1.0)


def test_stress_scenarios_are_unavailable_without_a_valid_point():
    report = generate_decision_report(_scenario(gpu_count=256, topology="series", flow_rate_lpm=8.0))

    assert report.stress_scenarios
    assert all(stress.status == "unavailable" for stress in report.stress_scenarios)
    assert all(stress.signed_junction_delta_c is None for stress in report.stress_scenarios)
    assert all(stress.changed_parameter is not None for stress in report.stress_scenarios)
    assert all(stress.base_value is not None for stress in report.stress_scenarios)
    assert all(stress.perturbed_value is not None for stress in report.stress_scenarios)
    assert all(stress.units is not None for stress in report.stress_scenarios)


def test_report_does_not_claim_system_hydraulic_feasibility_or_overall_risk():
    report = generate_decision_report(_scenario(flow_rate_lpm=8.0))

    assert report.system_hydraulic_feasibility == "not_assessed"
    assert report.risk_assessment == "not_assessed"
    assert report.evaluated_point is not None
    assert report.evaluated_point.pressure_drop_pa is not None


def test_report_carries_model_identity_and_validation_boundary():
    report = generate_decision_report(_scenario(flow_rate_lpm=8.0))

    assert report.report_schema_version == 2
    assert report.model.validation_state == "unvalidated"
    notices = " ".join(report.model.applicability_notices).lower()
    assert "transition" in notices
    assert "rectangular" in notices
    assert "measured" in notices


def test_report_always_carries_material_blind_spots():
    report = generate_decision_report(_scenario(flow_rate_lpm=8.0))

    assert report.blind_spots == KNOWN_LIMITATIONS
    combined = " ".join(report.blind_spots).lower()
    assert "manifold" in combined
    assert "temperature" in combined or "fluid properties" in combined
    assert "transient" in combined


def test_resolved_scenario_includes_complete_geometry():
    report = generate_decision_report(_scenario(flow_rate_lpm=8.0, geometry={"channel_count": 20}))

    geometry = report.resolved_scenario["geometry"]
    assert geometry["channel_count"] == 20
    assert geometry["channel_width_m"] == 1.0e-3


def test_leaf_provenance_distinguishes_supplied_and_defaulted_values():
    report = generate_decision_report(
        DecisionScenario(
            flow_rate_lpm=8.0,
            heat_load_w=700.0,
            geometry={"channel_count": 40},
            input_source_notes={"heat_load_w": "illustrative public scenario"},
        )
    )

    assert report.input_provenance["heat_load_w"] == {
        "origin": "supplied",
        "source_note": "illustrative public scenario",
    }
    assert report.input_provenance["inlet_temp_c"]["origin"] == "defaulted"
    assert report.input_provenance["geometry.channel_count"]["origin"] == "supplied"
    assert report.input_provenance["geometry.channel_width_m"]["origin"] == "defaulted"


def test_stress_provenance_tracks_supplied_leaf_and_source_note():
    report = generate_decision_report(
        DecisionScenario(
            flow_rate_lpm=8.0,
            stress_scenarios={"heat_load_delta_w": 25.0},
            input_source_notes={"stress_scenarios.heat_load_delta_w": "owner stress case"},
        )
    )

    assert report.input_provenance["stress_scenarios.heat_load_delta_w"] == {
        "origin": "supplied",
        "source_note": "owner stress case",
    }
    assert report.input_provenance["stress_scenarios.r_tim_multiplier"]["origin"] == "defaulted"


def test_v2_dump_omits_removed_authority_bearing_fields():
    dumped = generate_decision_report(_scenario(flow_rate_lpm=8.0)).model_dump()

    for removed in (
        "feasible",
        "recommended_flow",
        "recommended_supply_temp_c",
        "junction_temp_at_recommended_c",
        "margin_remaining_c",
        "risk_level",
        "uncertainty_section",
        "topology_recommendation",
    ):
        assert removed not in dumped


def test_rendered_memo_matches_structured_status_and_boundaries():
    report = generate_decision_report(_scenario(flow_rate_lpm=8.0))
    memo = report.rendered_memo

    assert "# Thermal Decision Memo" in memo
    assert "`meets_target`" in memo
    assert "Evaluated Point (fixed_input)" in memo
    assert "not assessed" in memo
    assert "Model Blind Spots" in memo
    assert "Recommended Operating Point" not in memo


def test_report_is_deterministic():
    scenario = _scenario(flow_rate_lpm=8.0)

    assert generate_decision_report(scenario).model_dump() == generate_decision_report(scenario).model_dump()


def test_larger_guardband_requires_at_least_as_much_searched_flow():
    low = generate_decision_report(_scenario(margin_c=0.0))
    high = generate_decision_report(_scenario(margin_c=10.0))

    assert low.flow_search is not None
    assert high.flow_search is not None
    assert low.flow_search.minimum_feasible_lpm_per_gpu is not None
    assert high.flow_search.minimum_feasible_lpm_per_gpu is not None
    assert high.flow_search.minimum_feasible_lpm_per_gpu >= low.flow_search.minimum_feasible_lpm_per_gpu


@pytest.mark.parametrize(
    "kwargs",
    [
        {"coolant": "liquid_nitrogen"},
        {"target_junction_temp_c": 50.0, "margin_c": 60.0},
        {"stress_scenarios": {"service_life_years": 3}},
    ],
)
def test_mcp_impl_returns_error_envelope_for_invalid_report_inputs(kwargs):
    result = generate_decision_report_impl(**kwargs)

    assert "error" in result
