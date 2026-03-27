# Portfolio Note

## thermal-mcp-server — What This Project Demonstrates

This is a production-quality Python library and MCP server for liquid-cooled GPU thermal analysis. It is not a demo or a tutorial project. It has a test suite with hand-calculation validation, a daily regression CI canary, and documented physics limitations.

**The engineering problem it solves:**

GPU power density has grown roughly 3× in two generations — H100 SXM at 700 W, B200 at 1,200 W. An NVL72 rack dissipates 86.4 kW. Liquid cooling is mandatory at this scale, and the sizing decisions — CDU flow rate, cold plate ΔP, series vs. parallel manifold topology — have direct consequences for both capital cost and thermal throttle risk. The tooling available to engineers making these decisions hasn't kept up with the hardware.

**What I built:**

A first-principles thermal resistance model (`physics.py`) validated against published chip specs, exposed as an MCP server (`mcp_server.py`) that an AI assistant can call in response to natural-language questions. The physics handles single cold plates (1D resistance network, Dittus-Boelter with laminar/turbulent blending, Darcy-Weisbach pressure drop) and racks of N identical GPUs in series or parallel topology. The MCP layer is a thin validation wrapper — all physics stays in the testable Python API.

**What makes it credible:**

- **Hand-calculation validation:** The canonical H100 case (700 W, 8 LPM, 25°C → Tj = 70.9°C) is independently derived from first principles in `tests/test_physics_behavior.py`. Every intermediate value — Reynolds number, Nusselt number, convection coefficient, pressure drop — is checked against manual calculation. This test is treated as a locked invariant; relaxing its tolerance requires explicit justification.
- **Honest limitations:** The model's known gaps — no manifold losses, no flow maldistribution, steady-state only, single-point fluid properties — are documented in `docs/physics.md` and surfaced in the README. These are acknowledged bounds, not papering over omissions.
- **Daily regression CI:** A GitHub Actions workflow runs the hand-calculation tests daily and opens a labeled issue automatically on failure. Silent physics drift from dependency updates is caught before it affects users.
- **Documented assumptions:** The B200 analysis uses engineering estimates for cold plate geometry and package resistance (NVIDIA does not publish these). Every non-published value is labeled as an estimate with a rationale.

**The AI tooling angle:**

The MCP protocol is how AI assistants acquire domain-specific tools. This project treats liquid cooling as a first-class engineering domain that AI assistants should be able to reason about correctly — with physics backing up the answers, not retrieval or pattern matching. It's an example of what engineering AI tooling looks like when built by someone who knows both the domain and the tooling layer.

**Stack:** Python 3.10+, FastMCP, Pydantic v2, pytest. Published on PyPI (`pip install thermal-mcp-server`). 34 tests. CI on every commit, daily physics regression.

**GitHub:** [github.com/riccardovietri/thermal-mcp-server](https://github.com/riccardovietri/thermal-mcp-server)
