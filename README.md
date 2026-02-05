# 🌡️ Thermal MCP Server

**Bring thermal simulation to Claude AI. Ask Claude questions about data center cooling, and get accurate thermal analysis powered by heat transfer physics.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/MCP-Server-green.svg)](https://modelcontextprotocol.io)

## Why This Exists

Data center liquid cooling is a **$6.6B market growing 28% annually**. Yet thermal engineers still lack fast, AI-integrated tools for analyzing cold plate systems and optimizing cooling strategies.

This server fills that gap by exposing thermal simulation capabilities to Claude via the [Model Context Protocol](https://modelcontextprotocol.io), letting you ask questions like:

- *"I have 8 H200 GPUs at 700W each with a cold plate. What flow rate do I need to keep junction temps under 80°C?"*
- *"Should I use water, glycol, or dielectric fluid for this 100kW rack?"*
- *"What's the minimum flow rate to achieve my thermal targets?"*

## Features

### Core Capabilities
- **1D Thermal Resistance Network**: Conservative, validated thermal model for cold plate cooling
- **Multiple Coolants**: Water, 50/50 water-glycol, and dielectric fluids
- **Temperature Analysis**: Junction-to-ambient thermal path with detailed breakdown
- **Flow Rate Optimization**: Find minimum flow rates for target temperatures
- **Pressure Drop Calculation**: Understand hydraulic requirements
- **System Comparison**: Compare cooling options side-by-side

### MCP Tools
Claude can use three tools:
1. **`analyze_coldplate_system`** - Thermal analysis for given operating conditions
2. **`compare_cooling_options`** - Compare different coolants/configurations
3. **`optimize_flow_rate`** - Find optimal operating points

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/riccardovietri/thermal-mcp-server.git
cd thermal-mcp-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Test the Thermal Model

```bash
# Run example calculations
python coldplate_model.py
```

You should see output showing thermal analysis results for sample GPU configurations.

### Use with Claude Code

```bash
# Start the MCP server (uses stdio for communication)
python -m src.mcp_server
```

The MCP server communicates with Claude Code via stdio. Once running, Claude will have access to three thermal analysis tools:
- `analyze_coldplate_system` - Calculate temperatures for given operating conditions
- `compare_cooling_options` - Compare different coolants side-by-side
- `optimize_flow_rate` - Find minimum flow rate for thermal targets

**Verify tools are available:**
Open Claude Code and ask: *"What thermal tools do you have access to?"*

Claude should respond with descriptions of the three tools above. If not, check that the MCP server is running without errors.

For detailed setup instructions, see [docs/MCP_USAGE.md](docs/MCP_USAGE.md).

## Examples

### Example 1: Basic System Analysis
```
User: "I have 4 GPUs at 600W each with a single cold plate, using water cooling.
What flow rate do I need for 75°C max junction temp?"

Claude calls: analyze_coldplate_system(gpu_power_w=600, num_gpus=4, coolant_type="water", flow_rate_lpm=15)

Claude: "For your 2400W system, a 15 LPM flow rate gives junction temps of ~78°C.
You're slightly over. Try 18 LPM for ~75°C."
```

### Example 2: Coolant Comparison
```
User: "Should I use water or dielectric for a 20kW data center rack?"

Claude calls: compare_cooling_options(heat_load_kw=20, coolant_types=["water", "glycol", "dielectric"])

Claude: "Water offers the best thermal performance (lowest temps) and lowest cost.
Dielectric is best for direct immersion but requires more infrastructure.
Glycol is a middle ground but adds maintenance complexity."
```

### Example 3: Flow Rate Optimization
```
User: "What's the minimum flow rate to keep my system under 80°C?"

Claude calls: optimize_flow_rate(gpu_power_w=700, num_gpus=8, max_temp_c=80, coolant_type="water")

Claude: "The minimum flow rate is 22 LPM. Below that, you'll exceed your
80°C thermal target. This requires a pump rated for ~45 PSI."
```

## Technical Details

### Thermal Model
- **1D Steady-State Analysis**: Conservative approach sufficient for design work
- **Thermal Path**: Junction → Case → TIM → Cold Plate → Coolant → Ambient
- **Turbulent Flow**: Based on Nusselt correlations for Re > 2300
- **Validation**: Cross-checked against heat transfer textbooks and field data

### Assumptions
- Uniform heat generation across GPU
- Fully-developed turbulent flow in cooling channels
- Perfect thermal contact at interfaces (conservative)
- Operating point efficiency for pump power

### Key Equations
```
Q = h × A × ΔT                    # Convective heat transfer
h = Nu × k / Dh                   # Nusselt correlation
Re = ρ × v × Dh / μ               # Reynolds number
ΔP = f × (L/Dh) × (ρ × v² / 2)   # Friction factor pressure drop
```

## Architecture

```
Claude/User Input
      ↓
MCP Server (FastMCP)
      ↓
Tool Dispatcher
      ↓
ColdPlateModel (Thermal Physics)
      ↓
CoolantProperties Database
      ↓
Results → Claude → User
```

## Roadmap

### v0.1 (Current)
- [x] 1D cold plate thermal model
- [x] FastMCP server wrapper
- [x] Three core tools
- [x] Basic documentation

### v0.2 (Planned)
- [ ] Multi-rack modeling
- [ ] Immersion cooling comparison
- [ ] Transient thermal response
- [ ] Cost/ROI calculator
- [ ] Temperature over time plots

### v0.3+
- [ ] API tier for programmatic access
- [ ] Integration with CAD tools
- [ ] Advanced optimization algorithms
- [ ] Custom model development service

## Contributing

Contributions welcome! Areas we need help:
- [ ] Additional coolant properties (fluorocarbon fluids, etc.)
- [ ] Integration examples (thermal simulation tools, CAD software)
- [ ] UI for non-technical users
- [ ] Additional cooling topologies (vapor chamber, direct-to-chip, etc.)
- [ ] Performance testing and validation

Please open an issue or PR to discuss changes.

## Support

- **Technical Questions**: Open an issue on GitHub
- **Feature Requests**: GitHub Discussions
- **Commercial Use**: Email for licensing options

## About the Author

I'm a Staff Thermal Engineer from Tesla with 4+ years of experience designing thermal systems for electric vehicles. This project brings that expertise to the data center space where thermal management is becoming critical at 1000W+ GPU power densities.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Heat transfer fundamentals: Incropera & DeWitt "Fundamentals of Heat and Mass Transfer"
- MCP Specification: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- FastMCP Framework: [GitHub/jlowin/fastmcp](https://github.com/jlowin/fastmcp)

---

**Ready to build?** Check out [QUICKSTART.md](QUICKSTART.md) for step-by-step implementation guide.

**Questions?** Open an issue or discussion thread.

**Like this project?** Consider sponsoring development! 🙏
