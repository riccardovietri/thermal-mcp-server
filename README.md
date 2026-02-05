# Thermal MCP Server (portfolio v0)

One-sentence summary: **This MCP server runs a transparent first-principles cold-plate model to estimate junction temperature and hydraulic cost for a given heat load.**

## Why this is credible
- Explicit thermal path: junction → case → TIM → copper base conduction → convection to coolant → bulk coolant rise → ambient reference. See [docs/physics.md](docs/physics.md).
- Regime-aware convection: laminar / transitional / turbulent handling from Reynolds number.
- Pressure drop from Darcy–Weisbach with regime-dependent friction factor.
- All defaults and assumptions are explicit and overrideable.

## Quick run (copy/paste)
See [QUICKSTART.md](QUICKSTART.md) for the shortest path.

```bash
git clone https://github.com/riccardovietri/thermal-mcp-server.git
cd thermal-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m thermal_mcp_server.mcp_server
```

## MCP tools (exactly three)
1. `analyze_coldplate`
2. `compare_coolants`
3. `optimize_flow_rate`

Tool details and schemas: [docs/mcp.md](docs/mcp.md)

## Proof it works
- Test suite for monotonic thermal behavior, regime switching, coolant ordering, pressure-drop scaling, and input validation.
- Validation example in [`examples/validation_walkthrough.md`](examples/validation_walkthrough.md).

Run tests:
```bash
pytest
```

## Intentionally out of scope (v0 honesty)
- 2D/3D spreading resistance and non-uniform heat flux
- Channel maldistribution/manifold losses
- Boiling/two-phase flow and cavitation
- Transient capacitance (steady-state only)
- Contact-resistance aging / TIM pump-out dynamics

## Repository map
- `src/thermal_mcp_server/`: model + MCP server
- `docs/physics.md`: assumptions, equations, limits, engineering notes
- `docs/mcp.md`: tool contracts and MCP usage
- `examples/validation_walkthrough.md`: sanity-check example
- `.github/workflows/ci.yml`: pytest on push/PR
