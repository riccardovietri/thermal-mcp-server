"""Minimal runnable example for thermal-mcp-server.

Run:
    python examples/quickstart.py
"""

from __future__ import annotations

from thermal_mcp_server.physics import analyze, analyze_rack
from thermal_mcp_server.schemas import AnalyzeColdplateInput, AnalyzeRackInput


def main() -> None:
    chip_limit_c = 83.0

    single = analyze(
        AnalyzeColdplateInput(
            heat_load_w=700.0,
            flow_rate_lpm=8.0,
            inlet_temp_c=25.0,
            coolant="water",
        )
    )

    rack = analyze_rack(
        AnalyzeRackInput(
            gpu_count=8,
            topology="parallel",
            heat_load_per_gpu_w=700.0,
            total_flow_lpm=64.0,
            cdu_supply_temp_c=25.0,
            coolant="water",
        )
    )

    print("thermal-mcp-server quickstart")
    print()
    print("Single H100 SXM cold plate")
    print(f"  Heat load:        700 W")
    print(f"  Flow rate:        8.0 LPM water")
    print(f"  Inlet temp:       25.0 deg C")
    print(f"  Junction temp:    {single.junction_temp_c:.1f} deg C")
    print(f"  Margin to 83 C:   {chip_limit_c - single.junction_temp_c:.1f} deg C")
    print(f"  Pressure drop:    {single.pressure_drop_pa / 1000:.1f} kPa")
    print(f"  Flow regime:      {single.regime}")
    print()
    print("8-GPU rack, parallel topology")
    print(f"  Rack heat load:   {rack.total_heat_load_w / 1000:.1f} kW")
    print(f"  Total CDU flow:   64.0 LPM")
    print(f"  Max junction:     {rack.max_junction_temp_c:.1f} deg C")
    print(f"  CDU return temp:  {rack.cdu_outlet_temp_c:.1f} deg C")
    print(f"  Cold-plate dP:    {rack.total_pressure_drop_pa / 1000:.1f} kPa")


if __name__ == "__main__":
    main()
