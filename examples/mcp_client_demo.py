"""Call the thermal MCP tools the way an AI client would.

This is the runnable counterpart to the screenshot in the README: it drives the
same FastMCP server an MCP client (Claude Desktop, etc.) would connect to, but
in-process — no network, no separate server, no API keys. It shows the exact
request/response shape a model sees when it calls these tools.

Run:
    python examples/mcp_client_demo.py
"""

from __future__ import annotations

import asyncio
import json

from fastmcp import Client

from thermal_mcp_server.mcp_server import mcp


def _show(title: str, payload: dict) -> None:
    print(title)
    print(json.dumps(payload, indent=2, sort_keys=True))
    print()


async def main() -> None:
    # `Client(mcp)` connects to the server object in-memory — the same transport
    # an MCP client uses over stdio, minus the process boundary.
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("thermal-mcp-server — MCP client demo")
        print()
        print("Tools advertised to the model:")
        for tool in tools:
            print(f"  - {tool.name}")
        print()

        # 1) Single cold-plate analysis — the canonical 700 W / 8 LPM water case.
        analyze = await client.call_tool(
            "analyze_coldplate",
            {
                "heat_load_w": 700.0,
                "flow_rate_lpm": 8.0,
                "inlet_temp_c": 25.0,
                "coolant": "water",
            },
        )
        _show("call analyze_coldplate(700 W, 8 LPM, water) ->", analyze.data)

        # 2) Fixed-flow screening — preserves the same 8 LPM/GPU operating point.
        report = await client.call_tool(
            "generate_decision_report",
            {
                "chip_label": "H100 SXM",
                "heat_load_w": 700.0,
                "gpu_count": 8,
                "topology": "parallel",
                "target_junction_temp_c": 83.0,
                "coolant": "water",
                "flow_rate_lpm": 8.0,
            },
        )
        data = report.data
        print("call generate_decision_report(8x H100 SXM, parallel) ->")
        print(f"  schema version:     {data['report_schema_version']}")
        print(f"  status:             {data['status']}")
        point = data["evaluated_point"]
        if point is None:
            print("  evaluated point:    unavailable")
        else:
            print(f"  evaluated flow:     {point['flow_lpm_per_gpu']:.2f} LPM/GPU")
            print(f"  evaluated Tj:       {point['junction_temp_c']:.1f} deg C")
            print(f"  guarded margin:     {point['margin_to_criterion_c']:.1f} deg C")
        print(f"  system hydraulics:  {data['system_hydraulic_feasibility']}")
        print(f"  blind spots listed: {len(data['blind_spots'])}")


if __name__ == "__main__":
    asyncio.run(main())
