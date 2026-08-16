[![CI](https://github.com/riccardovietri/thermal-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/riccardovietri/thermal-mcp-server/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/thermal-mcp-server)](https://pypi.org/project/thermal-mcp-server/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/thermal-mcp-server)](https://pypi.org/project/thermal-mcp-server/)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/riccardovietri/thermal-mcp-server/blob/main/examples/interactive_sizing.ipynb)

# thermal-mcp-server

A Python package and MCP server that exposes simplified liquid-cooled accelerator thermal models as AI-callable tools for rack-level cooling analysis.

## What It Models

- Steady-state 1D thermal-resistance networks for GPU cold plates.
- Coolant heat pickup from energy balance.
- Darcy-Weisbach pressure drop with simple laminar, transition, and turbulent handling.
- Water and 50/50 glycol comparisons using fixed nominal properties.
- Identical-GPU racks in series or parallel topology.
- First-pass CDU flow, pressure-drop, return-temperature, and junction-temperature sizing.
- Public accelerator reference cases with explicit source and estimate labels.

## What It Does Not Model

- It is not a CFD solver or vendor thermal-design substitute.
- It is not validated against proprietary test data.
- It does not model manifold/header pressure losses, pump curves, fouling, transient/two-phase behavior, 2D spreading, detailed cold-plate geometry, or flow maldistribution.
- It does not support heterogeneous racks; each rack analysis assumes identical GPUs and cold plates.
- Financial and ROI modeling belongs outside this package.

## Quickstart

```bash
git clone https://github.com/riccardovietri/thermal-mcp-server.git
cd thermal-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
python examples/quickstart.py
```

Expected output from `python examples/quickstart.py`:

```text
thermal-mcp-server quickstart

Single H100 SXM cold plate
  Heat load:        700 W
  Flow rate:        8.0 LPM water
  Inlet temp:       25.0 deg C
  Junction temp:    70.9 deg C
  Margin to 83 C:   12.1 deg C
  Pressure drop:    16.8 kPa
  Flow regime:      transitional

8-GPU rack, parallel topology
  Rack heat load:   5.6 kW
  Total CDU flow:   64.0 LPM
  Max junction:     70.9 deg C
  CDU return temp:  26.3 deg C
  Cold-plate dP:    16.8 kPa
```

For a series-vs-parallel rack comparison:

```bash
python examples/rack_sizing_example.py
```

## MCP Usage

Install the package:

```bash
pip install thermal-mcp-server
```

Add the server to an MCP client:

```json
{
  "mcpServers": {
    "thermal": {
      "command": "python",
      "args": ["-m", "thermal_mcp_server"]
    }
  }
}
```

If your MCP client does not inherit your shell `PATH`, use the absolute path to
the Python executable inside the environment where `thermal-mcp-server` is
installed.

Example MCP client run:

<img width="1768" height="1750" alt="MCP client answering a liquid-cooling question by calling thermal-mcp-server tools" src="https://github.com/user-attachments/assets/7e3fb436-38d2-477b-a4dd-e5a2a740d463" />

The client calls `analyze_coldplate` through the MCP server, receives the
thermal result, and interprets the output in the conversation.

To reproduce this locally without a separate client, run the in-memory demo —
it drives the same MCP server in-process (no network, no API key) and prints the
exact request/response payloads a model sees:

```bash
python examples/mcp_client_demo.py
```

## Tools

| Tool | Purpose |
|------|---------|
| `analyze_coldplate` | Single cold-plate thermal and hydraulic analysis |
| `compare_coolants` | Water vs 50/50 glycol comparison at identical conditions |
| `optimize_flow_rate` | Minimum flow search for a junction-temperature target |
| `analyze_rack` | Identical-GPU rack analysis in series or parallel topology |
| `generate_decision_report` | First-pass sizing memo with flow band, risk, uncertainty, and model blind spots |

See [`docs/mcp.md`](docs/mcp.md) for tool contracts.

## Physics Assumptions

The model uses:

```text
T_junction = T_inlet + 0.5 * coolant_rise + Q * R_total
R_total = R_jc + R_tim + R_base + R_conv
coolant_rise = Q / (m_dot * cp)
```

Heat transfer uses Dittus-Boelter for turbulent flow, Nu = 4.36 for laminar
flow, and a linear blend in transition. Pressure drop uses Darcy-Weisbach with
the same regime split.

Read the concise model notes in [`docs/model_overview.md`](docs/model_overview.md)
and [`docs/assumptions.md`](docs/assumptions.md). The detailed derivation and
hand-calculation references are in [`docs/physics.md`](docs/physics.md).

## Public Reference Cases

The examples include H100 SXM, B200 / GB200 NVL72-style, MI300X, and Gaudi 3 cases.
Only H100 TDP and thermal limit are treated as vendor-published values in the
default examples. Other limits, package resistances, and high-power cold-plate
geometry are marked as estimates or proxies where vendors do not publish them.

See [`docs/public_specs.md`](docs/public_specs.md) and
[`examples/real_chip_benchmarks.py`](examples/real_chip_benchmarks.py).

## Tests

The current suite has 75 tests:

- Physics behavior and hand-calculation checks.
- MCP wrapper contracts and error envelopes.
- Decision report behavior, including rack-aware feasibility.
- Smoke tests for `examples/quickstart.py`, `examples/rack_sizing_example.py`,
  and `examples/mcp_client_demo.py`.

Run:

```bash
pytest
```

## Development

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv build
uv run python examples/quickstart.py
uv run python examples/rack_sizing_example.py
```

These mirror the CI gate; all must pass before a PR can merge.

## Roadmap

- Pump-curve support as an explicit input instead of a fixed pump-efficiency estimate.
- Transient thermal-capacitance model.
- More public reference cases with clearly labeled source quality.
- Interactive notebook polish for Colab use.
- Cold-plate optimization only as a separate experimental module or package.

## Why This Exists

This project started as a way to explore how AI assistants can call lightweight
engineering models directly instead of only producing static text. The package
exposes simplified liquid-cooling calculations through Python and MCP tools,
making it possible to ask design-tradeoff questions about accelerator cooling,
rack-level CDU sizing, and coolant topology in a reproducible way.
