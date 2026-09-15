from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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
    assert "70.90231" in output
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
    assert "70.90" in lines["Fixed 8 LPM"]
    assert "no_feasible_flow_in_search_range" in lines["Failed thermal search"]
    assert "undetermined" in lines["Series candidate"]
    assert "undetermined" in lines["Unavailable rack"]
    assert "unavailable" in lines["Unavailable rack"]
