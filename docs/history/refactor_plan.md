```text
Refactor plan (implemented)

New tree:
- src/thermal_mcp_server/
  - mcp_server.py
  - physics.py
  - schemas.py
- docs/
  - physics.md
  - mcp.md
- examples/
  - validation_walkthrough.md
- tests/
  - test_physics_behavior.py
  - test_mcp_tools.py
- .github/workflows/ci.yml

Checklist:
[x] package layout under src/thermal_mcp_server
[x] python -m thermal_mcp_server.mcp_server entrypoint
[x] exactly 3 tools with stable output shape
[x] explicit thermal path + assumptions + correlations + dp model
[x] portfolio-grade README and crisp QUICKSTART
[x] validation example
[x] pytest coverage for monotonicity/regime/coolant/dp/input validation
[x] CI on push/PR
```
