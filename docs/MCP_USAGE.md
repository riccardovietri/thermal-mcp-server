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

## Setup for Claude Desktop

### Step 1: Install the Server

```bash
# Clone the repository
git clone https://github.com/yourusername/thermal-mcp-server.git
cd thermal-mcp-server

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Claude Desktop

Edit your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

Add the thermal server:

```json
{
  "mcpServers": {
    "thermal-cooling": {
      "command": "python",
      "args": [
        "-m",
        "src.mcp_server"
      ],
      "cwd": "/absolute/path/to/thermal-mcp-server"
    }
  }
}
```

**Important**: Replace `/absolute/path/to/thermal-mcp-server` with the actual path!

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop. The thermal tools should now be available.

### Step 4: Verify Installation

In Claude Desktop, try asking:

> "What temperature will a 700W H100 GPU reach with 12 LPM water cooling?"

Claude should use the `analyze_coldplate_system` tool to provide an answer.

---

## Setup for Claude Code (CLI)

### Step 1: Install and Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the MCP server
python -m src.mcp_server
```

### Step 2: Test with MCP Inspector

```bash
# Install MCP inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector
mcp-inspector python -m src.mcp_server
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

## Common Issues and Solutions

### Issue: Tools not appearing in Claude Desktop

**Solution**:
1. Check config file path is correct for your OS
2. Verify absolute path to thermal-mcp-server is correct
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors

### Issue: "Module not found" error

**Solution**:
```bash
# Make sure you're in the thermal-mcp-server directory
cd /path/to/thermal-mcp-server

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from src.models.coldplate import ColdPlateModel; print('OK')"
```

### Issue: Wrong results or unexpected behavior

**Solution**:
1. Verify input parameters are reasonable (700W for H100, 8-20 LPM flow, etc.)
2. Check coolant type spelling (must be exactly "water", "glycol", or "dielectric")
3. Ensure temperature and flow values are positive

---

## Testing the Server

### Manual Testing

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

### Automated Tests

```bash
# Run all tests
pytest tests/

# Test specific module
pytest tests/test_coldplate.py -v
```

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

- **Source Code**: https://github.com/yourusername/thermal-mcp-server
- **Issues**: https://github.com/yourusername/thermal-mcp-server/issues
- **Validation**: See `docs/VALIDATION.md` for published case study validation
- **Test Strategy**: See `docs/TEST_STRATEGY.md` for testing approach

---

**Author**: Riccardo Vietri
**Last Updated**: February 3, 2026
**MCP Version**: 1.0.0
