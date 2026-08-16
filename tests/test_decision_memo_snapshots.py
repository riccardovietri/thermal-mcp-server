import pytest
from thermal_mcp_server.schemas import DecisionScenario
from thermal_mcp_server.decision_report import generate_decision_report

def test_h100_series_snapshot(snapshot):
    scenario_series = DecisionScenario(
        chip_label="H100 (SXM proxy)",
        heat_load_w=700.0,
        gpu_count=8,
        inlet_temp_c=25.0,
        coolant="water",
        topology="series",
        target_junction_temp_c=83.0,
        margin_c=5.0,
    )
    report = generate_decision_report(scenario_series)
    # the dictionary matches exactly across executions
    assert report.model_dump(exclude={"rendered_memo"}) == snapshot

def test_h100_parallel_snapshot(snapshot):
    scenario_parallel = DecisionScenario(
        chip_label="H100 (SXM proxy)",
        heat_load_w=700.0,
        gpu_count=8,
        inlet_temp_c=25.0,
        coolant="water",
        topology="parallel",
        target_junction_temp_c=83.0,
        margin_c=5.0,
    )
    report = generate_decision_report(scenario_parallel)
    assert report.model_dump(exclude={"rendered_memo"}) == snapshot

def test_b200_proxy_snapshot(snapshot):
    scenario_b200 = DecisionScenario(
        chip_label="B200 (Proxy)",
        heat_load_w=1000.0,
        gpu_count=8,
        inlet_temp_c=25.0,
        coolant="water",
        topology="parallel",
        target_junction_temp_c=83.0,
        margin_c=3.0,
    )
    report = generate_decision_report(scenario_b200)
    assert report.model_dump(exclude={"rendered_memo"}) == snapshot

def test_glycol50_snapshot(snapshot):
    scenario_pg = DecisionScenario(
        chip_label="H100 (PG50)",
        heat_load_w=700.0,
        gpu_count=8,
        inlet_temp_c=25.0,
        coolant="glycol50",
        topology="parallel",
        target_junction_temp_c=83.0,
        margin_c=5.0,
    )
    report = generate_decision_report(scenario_pg)
    assert report.model_dump(exclude={"rendered_memo"}) == snapshot

def test_blind_spots_invariant(snapshot):
    # Blind spots must contain all known limitations.
    scenario_series = DecisionScenario(
        chip_label="H100 (SXM proxy)",
        heat_load_w=700.0,
        gpu_count=8,
        inlet_temp_c=25.0,
        coolant="water",
        topology="series",
        target_junction_temp_c=83.0,
        margin_c=5.0,
    )
    report = generate_decision_report(scenario_series)
    assert len(report.blind_spots) == 6
    assert report.blind_spots == snapshot
