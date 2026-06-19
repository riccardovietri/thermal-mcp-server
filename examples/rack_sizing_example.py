"""Series vs parallel rack sizing example.

Run:
    python examples/rack_sizing_example.py
"""

from __future__ import annotations

from thermal_mcp_server.physics import analyze_rack
from thermal_mcp_server.schemas import AnalyzeRackInput

GPU_COUNT = 8
HEAT_LOAD_PER_GPU_W = 700.0
TJ_LIMIT_C = 83.0
PER_GPU_FLOW_LPM = 8.0
CDU_SUPPLY_C = 25.0


def _run(topology: str) -> object:
    total_flow_lpm = PER_GPU_FLOW_LPM if topology == "series" else PER_GPU_FLOW_LPM * GPU_COUNT
    return analyze_rack(
        AnalyzeRackInput(
            gpu_count=GPU_COUNT,
            topology=topology,
            heat_load_per_gpu_w=HEAT_LOAD_PER_GPU_W,
            total_flow_lpm=total_flow_lpm,
            cdu_supply_temp_c=CDU_SUPPLY_C,
            coolant="water",
        )
    )


def main() -> None:
    series = _run("series")
    parallel = _run("parallel")

    print("Rack sizing example: 8 x H100 SXM")
    print(f"Heat load: {GPU_COUNT * HEAT_LOAD_PER_GPU_W / 1000:.1f} kW")
    print(f"CDU supply: {CDU_SUPPLY_C:.1f} deg C")
    print(f"Per-GPU flow basis: {PER_GPU_FLOW_LPM:.1f} LPM")
    print()
    print("Topology     CDU flow   Max Tj   Margin   dP      CDU return")
    print("-------------------------------------------------------------")

    for name, result in (("series", series), ("parallel", parallel)):
        margin_c = TJ_LIMIT_C - result.max_junction_temp_c
        total_flow_lpm = PER_GPU_FLOW_LPM if name == "series" else PER_GPU_FLOW_LPM * GPU_COUNT
        print(
            f"{name:<11} {total_flow_lpm:>7.1f} LPM"
            f" {result.max_junction_temp_c:>7.1f} C"
            f" {margin_c:>7.1f} C"
            f" {result.total_pressure_drop_pa / 1000:>6.1f} kPa"
            f" {result.cdu_outlet_temp_c:>9.1f} C"
        )

    print()
    if series.max_junction_temp_c <= TJ_LIMIT_C:
        print("Series is thermally viable here, but has less junction margin.")
    else:
        print("Series exceeds the junction limit; use parallel or change conditions.")
    print("Parallel keeps each GPU at CDU supply temperature and has more margin.")


if __name__ == "__main__":
    main()
