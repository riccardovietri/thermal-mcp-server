# Validation Walkthrough (toy but honest)

Scenario: 700 W chip, water, 25 C inlet, default geometry.

## Inputs
- `heat_load_w=700`
- `flow_rate_lpm=8`
- `coolant=water`

## Example run
```python
from thermal_mcp_server.physics import analyze
from thermal_mcp_server.schemas import AnalyzeColdplateInput

result = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water"))
print(result.model_dump())
```

## Sanity checks
1. **Sign check:** pressure drop is positive.
2. **Order of magnitude:** `h` is in the low-thousands `W/m^2-K` range for internal forced convection in mm channels.
3. **Sensitivity:** increasing flow from `8 -> 12 LPM` should reduce `Tj` and increase `deltaP`.

## Quick sensitivity snippet
```python
for f in [8, 12]:
    r = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=f, coolant="water"))
    print(f, r.junction_temp_c, r.pressure_drop_pa)
```
Expected trend:
- `Tj(12 LPM) <= Tj(8 LPM)`
- `deltaP(12 LPM) > deltaP(8 LPM)`
