# Quick Start - Thermal MCP Server

Get started with AI-powered thermal analysis in 5 minutes.

## 1. Install (2 min)

```bash
# Clone repository
git clone https://github.com/riccardovietri/thermal-mcp-server.git
cd thermal-mcp-server

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e .
```

## 2. Run MCP Server (1 min)

```bash
python -m src.mcp_server
```

The server is now running and ready to receive requests from Claude Code via stdio communication.

## 3. Connect to Claude Code (1 min)

In Claude Code, the MCP server will be automatically discovered. You can now ask thermal questions like:

> "I have 8 H100 GPUs at 700W each. What flow rate do I need to keep them under 85°C with water cooling?"

Claude will use the thermal analysis tools to answer.

## 4. Try the Validation Example (1 min)

```bash
python examples/validation_nvidia_h100.py
```

This reproduces published NVIDIA H100 thermal specifications to verify the model accuracy.

## 5. Next Steps

- Read [MCP_USAGE.md](docs/MCP_USAGE.md) for detailed tool documentation
- See [examples/README.md](examples/README.md) for more usage examples
- Check [CONTRIBUTING.md](CONTRIBUTING.md) if you want to extend the tool
- Read [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for implementation details

## Troubleshooting

**MCP server doesn't start:**
- Verify installation: `pip list | grep fastmcp`
- Check Python version: `python --version` (requires >=3.10)

**Tools not available in Claude Code:**
- Ensure MCP server is running
- Check for error messages in server output
- See [MCP_USAGE.md](docs/MCP_USAGE.md) for detailed setup

**Need help?**
- Open an issue: https://github.com/riccardovietri/thermal-mcp-server/issues
- Read the docs: [README.md](README.md)
