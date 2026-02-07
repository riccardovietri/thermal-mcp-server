# Thermal MCP Server

**A Model Context Protocol server that provides thermal analysis for liquid-cooled electronics.**

Estimates junction temperature, thermal resistances, and hydraulic requirements for cold plate cooling systems using first-principles heat transfer calculations.

## Technical approach
- Thermal path: junction → case → TIM → copper base → convection → coolant → ambient
- Regime-aware convection (laminar/transitional/turbulent based on Reynolds number)
- Pressure drop from Darcy-Weisbach correlation
- All parameters are explicit with documented defaults

See [docs/physics.md](docs/physics.md) for equations and assumptions.

## Quick run (copy/paste)
See [QUICKSTART.md](QUICKSTART.md) for the shortest path.

```bash
git clone https://github.com/riccardovietri/thermal-mcp-server.git
cd thermal-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m thermal_mcp_server
```

## Claude Desktop integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "thermal": {
      "command": "python",
      "args": ["-m", "thermal_mcp_server"],
      "cwd": "/absolute/path/to/thermal-mcp-server"
    }
  }
}
```

Then ask Claude: *"I have 8 H100 GPUs at 700W each with water cooling at 10 LPM. What's the junction temperature?"*

## Available tools
1. **analyze_coldplate** — Calculate junction temperature and pressure drop for given conditions
2. **compare_coolants** — Compare water vs glycol performance side-by-side
3. **optimize_flow_rate** — Find minimum flow rate to meet temperature target

See [docs/mcp.md](docs/mcp.md) for tool schemas and usage.

## Testing
Test suite covers thermal behavior, regime transitions, and input validation.

Run tests:
```bash
pytest
```

## Current limitations
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
