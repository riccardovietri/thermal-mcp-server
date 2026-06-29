from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_example(script: str) -> str:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / script)],
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
    assert "blind spots listed: 6" in output
