# MCP Server Usage Guide

## Overview

The Thermal MCP Server exposes three AI-accessible tools for thermal analysis of data center liquid cooling systems. This guide explains how to set up and use the server with Claude.

---

## Available Tools

### 1. `analyze_coldplate_system`

**Purpose**: Perform complete thermal and hydraulic analysis of a cold plate cooling system.

**Use when**:
- User asks "What temperature will my GPU run at?"
- Need complete thermal analysis with warnings
- Want to see pressure drop and pump power requirements

**Parameters**:
- `gpu_power_w` (float): GPU power in Watts (e.g., 700 for H100)
- `num_gpus` (int): Number of GPUs (default: 1)
- `coolant_type` (str): "water", "glycol", or "dielectric" (default: "water")
- `flow_rate_lpm` (float): Flow rate in liters/minute (default: 12.0)
- `ambient_temp_c` (float): Inlet coolant temp in °C (default: 25.0)
- `detailed` (bool): Include thermal resistance breakdown (default: True)

**Example prompts**:
- "I have 8 H100 GPUs at 700W each with 15 LPM water cooling. What temps will I see?"
- "Analyze a single 700W GPU with glycol at 10 LPM"
- "What's the pressure drop for my cooling system?"

**Example call**:
```python
analyze_coldplate_system(
    gpu_power_w=700,
    num_gpus=1,
    coolant_type="water",
    flow_rate_lpm=12,
    ambient_temp_c=25,
    detailed=True
)
```

---

### 2. `compare_cooling_options`

**Purpose**: Compare water, glycol, and dielectric coolants side-by-side.

**Use when**:
- User asks "Should I use water or glycol?"
- Comparing coolant options for a design decision
- Need to see trade-offs between thermal performance and other factors

**Parameters**:
- `gpu_power_w` (float): GPU power in Watts
- `num_gpus` (int): Number of GPUs (default: 1)
- `flow_rate_lpm` (float): Flow rate in liters/minute (default: 12.0)
- `ambient_temp_c` (float): Inlet coolant temp in °C (default: 25.0)
- `coolant_types` (list): Coolants to compare (default: all three)

**Example prompts**:
- "Should I use water or glycol for my data center?"
- "Compare all coolant options for 8× 700W GPUs"
- "What's the difference between water and dielectric cooling?"

**Example call**:
```python
compare_cooling_options(
    gpu_power_w=700,
    num_gpus=8,
    flow_rate_lpm=15,
    ambient_temp_c=25,
    coolant_types=["water", "glycol"]
)
```

---

### 3. `optimize_flow_rate`

**Purpose**: Find minimum flow rate needed to meet a temperature target.

**Use when**:
- User asks "What flow rate do I need?"
- Optimizing for minimum pump power
- Sizing cooling system components

**Parameters**:
- `gpu_power_w` (float): GPU power in Watts
- `num_gpus` (int): Number of GPUs (default: 1)
- `target_temp_c` (float): Max junction temperature in °C (default: 80.0)
- `coolant_type` (str): "water", "glycol", or "dielectric" (default: "water")
- `ambient_temp_c` (float): Inlet coolant temp in °C (default: 25.0)
- `min_flow_lpm` (float): Minimum flow rate to consider (default: 5.0)
- `max_flow_lpm` (float): Maximum flow rate to consider (default: 30.0)

**Example prompts**:
- "What flow rate do I need to keep my H100 under 80°C?"
- "Find the minimum flow rate for my cooling system"
- "Optimize my pump sizing to meet thermal requirements"

**Example call**:
```python
optimize_flow_rate(
    gpu_power_w=700,
    num_gpus=1,
    target_temp_c=80,
    coolant_type="water",
    ambient_temp_c=25
)
```

---

## Setup for Claude Code

### Step 1: Install the Server

```bash
# Clone the repository
git clone https://github.com/riccardovietri/thermal-mcp-server.git
cd thermal-mcp-server

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Run the MCP Server

```bash
# Start the MCP server (uses stdio for communication)
python -m src.mcp_server
```

The server starts in stdio mode and communicates with Claude Code via standard input/output. You should see no output if it starts successfully (stdio mode is silent).

### Step 3: Verify Tools Are Available

Open Claude Code and ask:

> "What thermal analysis tools do you have access to?"

Claude should list the three tools:
- `analyze_coldplate_system`
- `compare_cooling_options`
- `optimize_flow_rate`

If the tools don't appear, check the troubleshooting section below.

### Step 4: Try an Example

Ask Claude:

> "I have 8 H100 GPUs at 700W each. What flow rate do I need to keep them under 85°C with water cooling?"

Claude should use the `optimize_flow_rate` tool to calculate the answer.

---

## Troubleshooting

### Issue: Tools not available in Claude Code

**Solution**:
1. Verify the MCP server is running without errors
2. Check Python version: `python --version` (requires >=3.10)
3. Verify installation: `python -c "from src.models.coldplate import ColdPlateModel; print('✓ OK')"`
4. Restart the MCP server

### Issue: "Module not found" error

**Solution**:
```bash
# Ensure you're in the correct directory
cd thermal-mcp-server

# Reinstall dependencies
pip install -r requirements.txt

# Verify imports work
python -c "from src.mcp_server import analyze_coldplate_system; print('✓ OK')"
```

### Issue: Wrong results or unexpected behavior

**Solution**:
1. Verify input parameters are reasonable:
   - GPU power: 300-1000W typical
   - Flow rate: 5-30 LPM typical
   - Coolant type: exactly "water", "glycol", or "dielectric"
2. Check that temperatures are positive
3. Run validation: `python examples/validation_nvidia_h100.py`

---

## Testing the Server (Advanced)

### Manual Testing with Python

```bash
# Start Python interpreter
python

# Import and test
from src.mcp_server import analyze_coldplate_system

result = analyze_coldplate_system(
    gpu_power_w=700,
    coolant_type="water",
    flow_rate_lpm=12
)
print(result)
```

### Testing with MCP Inspector

The MCP Inspector is a debugging tool for MCP servers:

```bash
# Install MCP inspector (requires Node.js)
npm install -g @modelcontextprotocol/inspector

# Run inspector
npx @modelcontextprotocol/inspector python -m src.mcp_server
```

This opens a web interface where you can manually call tools and inspect responses.

### Automated Tests

```bash
# Run all tests
pytest tests/

# Test specific module
pytest tests/test_coldplate.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## Example Conversations

### Example 1: Basic Analysis

**User**: "I have 8 H200 GPUs at 700W each. What flow rate do I need to keep them under 85°C with water cooling?"

**Claude** (uses `optimize_flow_rate`):
```
Finding optimal flow rate...

FLOW RATE OPTIMIZATION RESULTS
================================================================================
System: 8× 700W GPUs = 5600W total
Coolant: Water
Target Temperature: ≤85°C
Inlet Temperature: 25°C

OPTIMIZED OPERATING POINT
--------------------------------------------------------------------------------
Flow Rate:          24.50 LPM
Junction Temp:      84.8°C
Coolant Temp Rise:  3.3°C
Pressure Drop:      4.2 psi
Pump Power:         42.1 W

✓ Target temperature achieved!

SYSTEM EFFICIENCY
--------------------------------------------------------------------------------
Pump power overhead: 0.75% of GPU power
Total system power:  5642 W
→ Excellent efficiency (pump power <2% overhead)
```

---

### Example 2: Coolant Comparison

**User**: "Should I use water or glycol for outdoor cooling in a cold climate?"

**Claude** (uses `compare_cooling_options`):
```
Let me compare water and glycol for your outdoor cooling scenario...

COOLANT COMPARISON
================================================================================
System: 1× 700W GPUs = 700W total
Flow Rate: 12 LPM
Inlet Temp: 5°C (cold climate)

Metric                         Water          Glycol
--------------------------------------------------------------------------------
Junction Temp                   47.3°C         75.2°C
Coolant Temp Rise                0.8°C          0.8°C
Pressure Drop                   0.33 psi       0.91 psi
Pump Power                      1.4 W          4.8 W
Heat Transfer Coeff             8399 W/m²·K    4231 W/m²·K

RECOMMENDATIONS
================================================================================
Best Thermal Performance: Water
  → Junction temp: 47.3°C

Lowest Pressure Drop: Water
  → Pressure: 0.33 psi

Most Efficient (Pump Power): Water
  → Pump power: 1.4 W

SELECTION GUIDE:
• Water: Best performance, lowest cost (use if no freeze risk)
• Glycol: Freeze protection for outdoor/cold climates (<0°C)
• Dielectric: Electrical isolation (immersion or direct contact)

For outdoor cooling at 5°C, glycol is recommended for freeze protection,
even though water has better thermal performance. If you can guarantee
the system won't see freezing temps, water would be more efficient.
```

---

### Example 3: Thermal Analysis

**User**: "What's the junction temperature for a single H100 GPU at 700W with 15 LPM water cooling?"

**Claude** (uses `analyze_coldplate_system`):
```
THERMAL ANALYSIS RESULTS
================================================================================
System Configuration:
  - Power: 700 W (1 GPU × 700 W)
  - Coolant: Water
  - Flow Rate: 15.0 LPM
  - Ambient Temperature: 25.0°C

Performance:
  - Junction Temperature: 70.8°C
  - Coolant Temperature Rise: 0.7°C
  - Pressure Drop: 0.41 psi
  - Pump Power: 2.1 W

Heat Transfer:
  - Heat Transfer Coefficient: 9,234 W/(m²·K)
  - Reynolds Number: 5,218 (Turbulent Flow)

Thermal Resistance Breakdown:
  - R_junction_to_case: 0.0400 K/W
  - R_TIM: 0.0100 K/W
  - R_coldplate_conduction: 0.0050 K/W
  - R_convection: 0.0108 K/W
  - R_total: 0.0658 K/W

Temperature is well within safe operating limits (<85°C). No warnings.
```

---

## Tool Selection Guidelines

**When to use each tool:**

| User Question | Recommended Tool | Why |
|--------------|------------------|-----|
| "What temp will I see?" | `analyze_coldplate_system` | Complete analysis with warnings |
| "What flow rate do I need?" | `optimize_flow_rate` | Finds minimum flow for target |
| "Water or glycol?" | `compare_cooling_options` | Shows trade-offs side-by-side |
| "Size my pump" | `optimize_flow_rate` | Provides pressure drop and power |
| "Is my design safe?" | `analyze_coldplate_system` | Includes warnings and checks |
| "Compare coolants" | `compare_cooling_options` | Direct comparison table |


---

## Performance

- **Tool execution time**: <100ms typical
- **Memory usage**: <50MB
- **Concurrent requests**: Not thread-safe (use separate processes if needed)

---

## Security Considerations

- All calculations run locally (no external API calls)
- No sensitive data is stored or transmitted
- Input validation prevents unreasonable values
- Safe for use in air-gapped environments

---

## Support and Documentation

- **Source Code**: https://github.com/riccardovietri/thermal-mcp-server
- **Issues**: https://github.com/riccardovietri/thermal-mcp-server/issues
- **Validation**: See `docs/VALIDATION.md` for published case study validation
- **Test Strategy**: See `docs/TEST_STRATEGY.md` for testing approach

---

**Author**: Riccardo Vietri
**Last Updated**: February 3, 2026
**MCP Version**: 1.0.0
