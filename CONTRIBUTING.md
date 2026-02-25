# Contributing

## Setup

```bash
git clone https://github.com/riccardovietri/thermal-mcp-server.git
cd thermal-mcp-server
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

## Running tests

```bash
pytest
```

## Physics changes

All physics modifications require:

1. A documented justification in `docs/physics.md`
2. A corresponding test in `tests/test_physics_behavior.py`
3. If changing default geometry or correlation constants, a hand-calculation
   validation showing the new expected output

## Adding coolants

Add to the `COOLANTS` dict in `src/thermal_mcp_server/physics.py` with:

- Source for property values (temperature, concentration, reference)
- Note whether properties are for aqueous mixture or neat fluid
- Update the `CoolantName` literal in `src/thermal_mcp_server/schemas.py`

## Code style

- Type hints on all public functions
- `# ASSUMPTION:` comments on any non-obvious modeling choices
- Conventional commits: `fix:`, `feat:`, `docs:`, `examples:`, `test:`
