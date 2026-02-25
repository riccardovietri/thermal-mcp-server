# Contributing

## Running tests

```bash
pip install -e .[dev]
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
- Source for property values (temperature, reference)
- Note whether properties are for aqueous mixture or neat fluid
- Update the `CoolantName` literal in `src/thermal_mcp_server/schemas.py`

## Code style

- Type hints on all public functions
- `# ASSUMPTION:` comments on any non-obvious modeling choices
- Conventional commits: `fix:`, `feat:`, `docs:`, `examples:`, `test:`
