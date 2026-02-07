# Contributing to Thermal MCP Server

Thank you for your interest in contributing! This guide will help you get set up and understand the project structure.

## Quick Start (Fresh Setup)

### Prerequisites
- Python 3.10 or higher
- Git
- Claude Code (for testing MCP integration)

### Installation

```bash
# Clone the repository
git clone https://github.com/riccardovietri/thermal-mcp-server.git
cd thermal-mcp-server

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation - run tests
python -m pytest tests/ -v

# Test the thermal model
python src/models/coldplate.py
```

You should see thermal analysis output for an 8-GPU system.

## Project Structure

```
thermal-mcp-server/
├── src/
│   ├── models/
│   │   ├── coldplate.py       # Core thermal resistance model
│   │   └── __init__.py
│   ├── mcp_server.py           # FastMCP server implementation
│   └── __init__.py
├── tests/
│   ├── test_coldplate.py       # Thermal model unit tests
│   ├── test_mcp_tools.py       # MCP tool logic tests
│   ├── test_validation.py      # First principles validation
│   └── test_published_case_studies.py  # Literature validation
├── docs/                       # Documentation
│   ├── MCP_USAGE.md           # Detailed MCP setup and usage
│   ├── VALIDATION.md          # Model validation documentation
│   └── TEST_STRATEGY.md       # Testing approach
├── examples/                   # Usage examples
│   └── validation_nvidia_h100.py  # H100 validation example
├── README.md                   # Project overview
├── CONTRIBUTING.md             # This file
├── QUICKSTART.md               # User quick start guide
├── DEVELOPER_GUIDE.md          # Implementation guide
├── pyproject.toml              # Package metadata for PyPI
└── requirements.txt            # Python dependencies
```

## Running the MCP Server

### Standalone Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Run the server (will start in stdio mode)
python -m src.mcp_server
```

The server runs in stdio mode and waits for MCP protocol messages. Press Ctrl+C to stop.

### Claude Code Integration

```bash
# Start the MCP server
python -m src.mcp_server
```

Once running, open Claude Code and the thermal tools will be available. Test by asking:

> "I have 8 H100 GPUs at 700W each. What flow rate do I need for 85°C max junction temp?"

Claude should use the `optimize_flow_rate` tool to answer.

## Development Workflow

### 1. Make Changes

Edit files in `src/` or add new features.

### 2. Write Tests

Add tests in `tests/` to cover your changes:
- Thermal model changes → `test_coldplate.py`
- MCP tool changes → `test_mcp_tools.py`
- Validation cases → `test_validation.py`

### 3. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_coldplate.py -v

# Run specific test
python -m pytest tests/test_coldplate.py::TestCoolantProperties::test_water_properties -v
```

### 4. Check Code Style (Optional)

```bash
# Format code
black src/ tests/

# Lint code
pylint src/
```

### 5. Commit Changes

```bash
git add .
git commit -m "Your descriptive commit message"
```

### 6. Push and Create PR

```bash
git push origin your-branch-name
```

Then create a pull request on GitHub.

## Testing Your Changes

### Thermal Model Changes

If you modify `src/models/coldplate.py`:

1. **Run unit tests**: `python -m pytest tests/test_coldplate.py -v`
2. **Run validation tests**: `python -m pytest tests/test_validation.py -v`
3. **Check published case studies**: `python -m pytest tests/test_published_case_studies.py -v`
4. **Manual verification**: `python src/models/coldplate.py`

### MCP Server Changes

If you modify `src/mcp_server.py`:

1. **Run MCP tool tests**: `python -m pytest tests/test_mcp_tools.py -v`
2. **Test server startup**: `python -m src.mcp_server` (should start without errors)
3. **Test with Claude Code**: Ask Claude to use the tools to verify they work correctly

## Adding New Features

### Adding a New Coolant Type

1. Add properties in `src/models/coldplate.py`:
```python
@classmethod
def new_coolant(cls, temp_c: float = 25.0):
    return cls(
        name="New Coolant",
        density=1000.0,  # kg/m³
        specific_heat=4000.0,  # J/(kg·K)
        thermal_conductivity=0.5,  # W/(m·K)
        dynamic_viscosity=0.001  # Pa·s
    )
```

2. Update `__init__` to recognize it:
```python
elif coolant_type.lower() == "new_coolant":
    self.coolant = CoolantProperties.new_coolant()
```

3. Add tests in `tests/test_coldplate.py`
4. Update documentation

### Adding a New MCP Tool

1. Add tool function in `src/mcp_server.py`:
```python
@mcp.tool()
def your_new_tool(
    param1: float,
    param2: str
) -> str:
    """
    Tool description for Claude.

    Args:
        param1: Description
        param2: Description

    Returns:
        Formatted result string
    """
    # Implementation
    return result
```

2. Add tests in `tests/test_mcp_tools.py`
3. Update README with usage example

## Troubleshooting

### "Module not found" errors

Make sure you're in the virtual environment and have installed dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Tests fail with import errors

Run tests from the project root directory:
```bash
cd /path/to/thermal-mcp-server
python -m pytest tests/
```

### MCP server tools not available in Claude Code

1. Verify the server starts without errors: `python -m src.mcp_server`
2. Check Python version: `python --version` (requires >=3.10)
3. Verify dependencies are installed: `pip list | grep fastmcp`
4. Restart the MCP server

### Thermal model gives unexpected results

1. Check your input values are in the correct units (W, LPM, °C)
2. Run the validation tests: `python -m pytest tests/test_validation.py -v`
3. Compare against published case studies: `python -m pytest tests/test_published_case_studies.py -v`

## Getting Help

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check README.md and QUICKSTART.md

## Code of Conduct

- Be respectful and constructive in all interactions
- Focus on technical merit and engineering principles
- Help others learn and contribute

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
