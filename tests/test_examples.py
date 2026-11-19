from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run_example(script: str, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / script), *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def test_quickstart_runs():
    output = _run_example("quickstart.py")
    assert "thermal-mcp-server quickstart" in output
    assert "Single H100 SXM cold plate" in output
    assert "8-GPU rack, parallel topology" in output
    assert "70.9 deg C" in output


def test_rack_sizing_example_runs():
    output = _run_example("rack_sizing_example.py")
    assert "Rack sizing example: 8 x H100 SXM" in output
    assert "series" in output
    assert "parallel" in output
    assert "79.7 C" in output
    assert "70.9 C" in output


def test_mcp_client_demo_runs():
    output = _run_example("mcp_client_demo.py")
    # Tools are advertised to the model through the MCP layer.
    assert "analyze_coldplate" in output
    assert "generate_decision_report" in output
    # Structured tool result flows back with the canonical default-case Tj.
    assert "70.91323" in output
    assert "schema version:     2" in output
    assert "evaluated flow:     8.00 LPM/GPU" in output
    assert "system hydraulics:  not_assessed" in output


def test_decision_memo_examples_run():
    output = _run_example("decision_memo_examples.py")
    assert "SCENARIO 1" in output
    assert "Side-by-Side Summary" in output
    assert "not assessed" in output


def test_compact_review_cases_run():
    output = _run_example("decision_memo_examples.py", "--review")
    lines = {
        label: next(line for line in output.splitlines() if line.startswith(label))
        for label in ("Fixed 8 LPM", "Failed thermal search", "Series candidate", "Unavailable rack")
    }
    assert "meets_target" in lines["Fixed 8 LPM"]
    assert "8.000" in lines["Fixed 8 LPM"]
    assert "70.91" in lines["Fixed 8 LPM"]
    assert "no_feasible_flow_in_search_range" in lines["Failed thermal search"]
    assert "undetermined" in lines["Series candidate"]
    assert "undetermined" in lines["Unavailable rack"]
    assert "unavailable" in lines["Unavailable rack"]


def test_make_figures_runs_and_is_deterministic(tmp_path: Path):
    # matplotlib comes from the `demo` extra, which the CI test job does not install.
    pytest.importorskip("matplotlib")
    first = tmp_path / "first"
    second = tmp_path / "second"
    output = _run_example("make_figures.py", "--out", str(first))
    assert "straight_fin_correlations.png" in output
    _run_example("make_figures.py", "--out", str(second))
    png = (first / "straight_fin_correlations.png").read_bytes()
    assert png.startswith(b"\x89PNG")
    assert png == (second / "straight_fin_correlations.png").read_bytes()
    assert "default_plate_tj_vs_flow.png" in output
    flow_png = (first / "default_plate_tj_vs_flow.png").read_bytes()
    assert flow_png.startswith(b"\x89PNG")
    assert flow_png == (second / "default_plate_tj_vs_flow.png").read_bytes()
    assert "chip_reference_case.png" in output
    case_png = (first / "chip_reference_case.png").read_bytes()
    assert case_png.startswith(b"\x89PNG")
    assert case_png == (second / "chip_reference_case.png").read_bytes()


# Expected values from docs/briefs/p4-reference-case.md (gate G1), at the printed
# precision: Tj 0.1 °C, ΔP 0.01 kPa, Re 1.
REFERENCE_CASE_EXPECTED = {
    ("H100 SXM", "A"): (80.9, 16.59, 3734),
    ("H100 SXM", "B"): (107.4, 0.89, 490),
    ("H100 SXM", "C"): (87.3, 0.71, 125),
    ("Blackwell GPU (GB200 NVL72)", "A"): (113.7, 16.59, 3734),
    ("Blackwell GPU (GB200 NVL72)", "B"): (155.7, 1.52, 840),
    ("Blackwell GPU (GB200 NVL72)", "C"): (121.2, 1.22, 214),
    ("MI300X", "A"): (84.2, 16.59, 3734),
    ("MI300X", "B"): (112.2, 0.95, 525),
    ("MI300X", "C"): (90.7, 0.76, 134),
    ("Gaudi 3 OAM (air)", "A"): (94.0, 16.59, 3734),
    ("Gaudi 3 OAM (air)", "B"): (126.7, 1.14, 630),
    ("Gaudi 3 OAM (air)", "C"): (100.9, 0.91, 160),
    ("Gaudi 3 OAM (liquid)", "A"): (113.7, 16.59, 3734),
    ("Gaudi 3 OAM (liquid)", "B"): (155.7, 1.52, 840),
    ("Gaudi 3 OAM (liquid)", "C"): (121.2, 1.22, 214),
}
REFERENCE_MIN_FLOW_EXPECTED = {
    ("H100 SXM", "default"): 6.607,
    ("H100 SXM", "reference"): 9.772,
    ("Blackwell GPU (GB200 NVL72)", "default"): None,
    ("Blackwell GPU (GB200 NVL72)", "reference"): None,
    ("MI300X", "default"): 7.331,
    ("MI300X", "reference"): 20.789,
    ("Gaudi 3 OAM (air)", "default"): None,
    ("Gaudi 3 OAM (air)", "reference"): None,
    ("Gaudi 3 OAM (liquid)", "default"): None,
    ("Gaudi 3 OAM (liquid)", "reference"): None,
}


def _import_example(monkeypatch: pytest.MonkeyPatch, name: str):
    monkeypatch.syspath_prepend(str(ROOT / "examples"))
    return importlib.import_module(name)


def test_reference_case_matches_expected_values(monkeypatch: pytest.MonkeyPatch):
    data = _import_example(monkeypatch, "reference_case").reference_case()
    points = {(p["chip"], p["config"]): p for p in data["points"]}
    assert set(points) == set(REFERENCE_CASE_EXPECTED)
    for key, (tj, dp, re) in REFERENCE_CASE_EXPECTED.items():
        p = points[key]
        assert round(p["tj_c"], 1) == tj, key
        assert round(p["dp_kpa"], 2) == dp, key
        assert round(p["reynolds"]) == re, key
        assert p["margin_c"] == pytest.approx(p["tj_limit_c"] - p["tj_c"])
        assert p["flow_lpm"] == pytest.approx(8.0 if key[1] == "A" else 1.5 * p["tdp_w"] / 1000.0)
        assert p["regime"] == ("transitional" if key[1] == "A" else "laminar"), key

    h100 = {cfg: points[("H100 SXM", cfg)]["resistances_k_per_w"]["convection"] * 1000.0 for cfg in "ABC"}
    assert round(h100["A"], 3) == 4.171
    assert round(h100["B"], 3) == 36.067
    assert round(h100["C"], 3) == 6.374

    min_flow = {(m["chip"], m["plate"]): m for m in data["min_flow"]}
    assert set(min_flow) == set(REFERENCE_MIN_FLOW_EXPECTED)
    for key, expected in REFERENCE_MIN_FLOW_EXPECTED.items():
        m = min_flow[key]
        if expected is None:
            assert m["min_flow_lpm"] is None and m["dp_kpa"] is None, key
        else:
            assert round(m["min_flow_lpm"], 3) == expected, key
            assert m["dp_kpa"] > 0, key


def test_reference_case_runs():
    output = _run_example("reference_case.py")
    assert "Reference case: water, 35 °C inlet" in output
    assert "no passing point in 0.2 to 30 LPM" in output
    assert "6.607" in output
    assert "36.067" in output


def test_real_chip_benchmarks_reference_data_unchanged(monkeypatch: pytest.MonkeyPatch):
    chips = _import_example(monkeypatch, "real_chip_benchmarks").ALL_CHIPS
    assert [(c.name, c.tdp_w, c.tj_limit_c) for c in chips] == [
        ("H100 SXM", 700, 83.0),
        ("Blackwell GPU (GB200 NVL72)", 1200, 75.0),
        ("MI300X", 750, 85.0),
        ("Gaudi 3 OAM (air)", 900, 85.0),
        ("Gaudi 3 OAM (liquid)", 1200, 85.0),
    ]


# Expected values from docs/briefs/p4b-package-band.md (gate G1), configuration C,
# at the printed precision: R_jc, R_tim and sum 0.001 mK/W, Tj 0.01 °C.
PACKAGE_BAND_EXPECTED = {
    ("H100 SXM", "bare die", "low"): (5.035, 4.914, 9.949, 52.25),
    ("H100 SXM", "bare die", "high"): (8.056, 14.742, 22.798, 61.24),
    ("H100 SXM", "lidded", "low"): (12.647, 4.914, 17.561, 57.58),
    ("H100 SXM", "lidded", "high"): (23.771, 14.742, 38.513, 72.24),
    ("Blackwell GPU (GB200 NVL72)", "bare die", "low"): (2.627, 2.564, 5.191, 55.43),
    ("Blackwell GPU (GB200 NVL72)", "bare die", "high"): (4.203, 7.692, 11.896, 63.48),
    ("Blackwell GPU (GB200 NVL72)", "lidded", "low"): (6.599, 2.564, 9.163, 60.20),
    ("Blackwell GPU (GB200 NVL72)", "lidded", "high"): (12.404, 7.692, 20.096, 73.32),
}


def test_package_band_matches_expected_values(monkeypatch: pytest.MonkeyPatch):
    module = _import_example(monkeypatch, "reference_case")
    assert module.DIE_AREA_M2 == {"H100 SXM": pytest.approx(8.14e-4), "Blackwell GPU (GB200 NVL72)": pytest.approx(15.6e-4)}
    data = module.reference_case()
    band = {(b["chip"], b["build"], b["end"]): b for b in data["package_band"]}
    generic = {key: b for key, b in band.items() if key[1] == "generic"}
    assert set(band) - set(generic) == set(PACKAGE_BAND_EXPECTED)
    for key, (r_jc, r_tim, total, tj) in PACKAGE_BAND_EXPECTED.items():
        b = band[key]
        assert round(b["r_jc_k_per_w"] * 1000.0, 3) == r_jc, key
        assert round(b["r_tim_k_per_w"] * 1000.0, 3) == r_tim, key
        assert round((b["r_jc_k_per_w"] + b["r_tim_k_per_w"]) * 1000.0, 3) == total, key
        assert round(b["tj_c"], 2) == tj, key
        assert b["margin_c"] == pytest.approx(b["tj_limit_c"] - b["tj_c"])
        assert b["config"] == "C" and b["flow_lpm"] == pytest.approx(1.5 * b["tdp_w"] / 1000.0)
        assert (b["r_jc_k_per_w"], b["r_tim_k_per_w"]) == pytest.approx(module.package_resistances(b["die_area_m2"], key[1], key[2]))

    # The generic case in the band is the existing configuration C point.
    points = {(p["chip"], p["config"]): p for p in data["points"]}
    assert {key[0] for key in generic} == {"H100 SXM", "Blackwell GPU (GB200 NVL72)"}
    for (chip, _, _), b in generic.items():
        assert (b["r_jc_k_per_w"], b["r_tim_k_per_w"]) == (0.04, 0.02)
        assert b["tj_c"] == pytest.approx(points[(chip, "C")]["tj_c"])


def test_package_resistances_rejects_unknown_build(monkeypatch: pytest.MonkeyPatch):
    module = _import_example(monkeypatch, "reference_case")
    with pytest.raises(ValueError):
        module.package_resistances(8.14e-4, "soldered", "low")


def test_reference_case_prints_package_band():
    output = _run_example("reference_case.py")
    assert "Package band, configuration C" in output
    assert "no hotspot factor" in output
    assert "not a measured die area" in output
    assert "MI300X: generic package only (die area not published)" in output
    assert "72.24" in output
    assert "73.32" in output
