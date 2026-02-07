# QUICKSTART

## 1) Setup
```bash
git clone https://github.com/riccardovietri/thermal-mcp-server.git
cd thermal-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2) Run MCP server
```bash
python -m thermal_mcp_server.mcp_server
```

## 3) Smoke test model in Python
```bash
python - <<'PY'
from thermal_mcp_server.schemas import AnalyzeColdplateInput
from thermal_mcp_server.physics import analyze

out = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water"))
print(out.model_dump())
PY
```

## 4) Run tests
```bash
pytest
```

For tool schemas and prompts: `docs/mcp.md`.
