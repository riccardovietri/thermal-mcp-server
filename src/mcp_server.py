"""
Thermal MCP Server - AI-Powered Data Center Cooling Simulation

This MCP server provides thermal analysis tools for data center liquid cooling
systems. It enables Claude AI to answer questions about GPU cooling, compare
coolant options, and optimize flow rates for thermal management.

Author: Riccardo Vietri
Date: February 2026
"""

from fastmcp import FastMCP
from typing import Literal
from src.models.coldplate import ColdPlateModel, format_analysis_result


# Initialize FastMCP server
mcp = FastMCP("thermal-cooling-server")


@mcp.tool()
def analyze_coldplate_system(
    gpu_power_w: float,
    num_gpus: int = 1,
    coolant_type: Literal["water", "glycol", "dielectric"] = "water",
    flow_rate_lpm: float = 12.0,
    ambient_temp_c: float = 25.0,
    detailed: bool = True
) -> str:
    """
    Analyze a cold plate liquid cooling system for GPU/chip cooling.

    This tool calculates thermal and hydraulic performance for a liquid-cooled
    GPU system using parallel microchannel cold plates. It provides junction
    temperatures, pressure drops, pump power requirements, and warnings.

    Args:
        gpu_power_w: Power dissipation per GPU in Watts (typical: 300-700W)
        num_gpus: Number of GPUs in the system (1-8 typical)
        coolant_type: Type of coolant fluid
            - "water": Best thermal performance, freeze point 0°C
            - "glycol": Freeze protection, slightly worse performance
            - "dielectric": Electrical isolation, poorest thermal performance
        flow_rate_lpm: Coolant flow rate in liters per minute (typical: 8-20 LPM)
        ambient_temp_c: Inlet coolant temperature in Celsius (typical: 20-30°C)
        detailed: Include detailed breakdown of thermal resistances

    Returns:
        Formatted string containing:
        - Junction temperature (target: <85°C for reliability)
        - Coolant temperature rise
        - Pressure drop through cold plate
        - Pump power requirement
        - Heat transfer coefficient
        - Reynolds number (flow regime indicator)
        - Warnings if temps/pressure/flow are outside recommended ranges
        - Detailed thermal resistance breakdown (if detailed=True)

    Example usage:
        analyze_coldplate_system(
            gpu_power_w=700,
            num_gpus=1,
            coolant_type="water",
            flow_rate_lpm=12,
            ambient_temp_c=25
        )
    """
    try:
        # Create thermal model
        model = ColdPlateModel(
            gpu_power_w=gpu_power_w,
            num_gpus=num_gpus,
            coolant_type=coolant_type,
            ambient_temp_c=ambient_temp_c
        )

        # Calculate performance
        result = model.calculate_performance(
            flow_rate_lpm=flow_rate_lpm,
            detailed=detailed
        )

        # Format and return results
        return format_analysis_result(result)

    except ValueError as e:
        return f"Error: {str(e)}\n\nPlease check input parameters."
    except Exception as e:
        return f"Unexpected error during analysis: {str(e)}"


@mcp.tool()
def compare_cooling_options(
    gpu_power_w: float,
    num_gpus: int = 1,
    flow_rate_lpm: float = 12.0,
    ambient_temp_c: float = 25.0,
    coolant_types: list[str] = None
) -> str:
    """
    Compare different coolant options side-by-side for the same thermal load.

    This tool helps select the optimal coolant by comparing water, glycol, and
    dielectric fluids for a given cooling scenario. It shows trade-offs between
    thermal performance, freeze protection, and electrical isolation.

    Args:
        gpu_power_w: Power dissipation per GPU in Watts
        num_gpus: Number of GPUs in the system
        flow_rate_lpm: Coolant flow rate in liters per minute
        ambient_temp_c: Inlet coolant temperature in Celsius
        coolant_types: List of coolants to compare (default: all three)
            Options: ["water", "glycol", "dielectric"]

    Returns:
        Formatted comparison table showing:
        - Junction temperatures for each coolant
        - Coolant temperature rise
        - Pressure drops (affects pump selection)
        - Pump power requirements
        - Recommendations based on requirements

    Example usage:
        compare_cooling_options(
            gpu_power_w=700,
            num_gpus=8,
            flow_rate_lpm=15,
            coolant_types=["water", "glycol"]
        )
    """
    try:
        # Default to comparing all coolants
        if coolant_types is None:
            coolant_types = ["water", "glycol", "dielectric"]

        # Validate coolant types
        valid_coolants = {"water", "glycol", "dielectric"}
        for coolant in coolant_types:
            if coolant.lower() not in valid_coolants:
                return f"Error: Unknown coolant type '{coolant}'. Valid options: water, glycol, dielectric"

        results = {}
        for coolant in coolant_types:
            model = ColdPlateModel(
                gpu_power_w=gpu_power_w,
                num_gpus=num_gpus,
                coolant_type=coolant.lower(),
                ambient_temp_c=ambient_temp_c
            )
            results[coolant] = model.calculate_performance(flow_rate_lpm=flow_rate_lpm)

        # Format comparison
        output = []
        output.append("=" * 80)
        output.append("COOLANT COMPARISON")
        output.append("=" * 80)
        output.append(f"System: {num_gpus}× {gpu_power_w}W GPUs = {num_gpus * gpu_power_w}W total")
        output.append(f"Flow Rate: {flow_rate_lpm} LPM")
        output.append(f"Inlet Temp: {ambient_temp_c}°C")
        output.append("")

        # Create comparison table
        output.append(f"{'Metric':<30} " + " ".join(f"{c.capitalize():>15}" for c in coolant_types))
        output.append("-" * 80)

        metrics = [
            ("Junction Temp", "junction_temp_c", "°C"),
            ("Coolant Temp Rise", "coolant_temp_rise_c", "°C"),
            ("Pressure Drop", "pressure_drop_psi", "psi"),
            ("Pump Power", "pump_power_w", "W"),
            ("Heat Transfer Coeff", "heat_transfer_coeff_w_m2k", "W/m²·K"),
        ]

        for label, key, unit in metrics:
            values = [f"{results[c][key]:.1f}" for c in coolant_types]
            output.append(f"{label:<30} " + " ".join(f"{v:>15}" for v in values))

        # Add recommendations
        output.append("")
        output.append("=" * 80)
        output.append("RECOMMENDATIONS")
        output.append("=" * 80)

        # Find best option for each criteria
        best_temp = min(coolant_types, key=lambda c: results[c]["junction_temp_c"])
        best_pressure = min(coolant_types, key=lambda c: results[c]["pressure_drop_psi"])
        best_efficiency = min(coolant_types, key=lambda c: results[c]["pump_power_w"])

        output.append(f"Best Thermal Performance: {best_temp.capitalize()}")
        output.append(f"  → Junction temp: {results[best_temp]['junction_temp_c']:.1f}°C")
        output.append("")
        output.append(f"Lowest Pressure Drop: {best_pressure.capitalize()}")
        output.append(f"  → Pressure: {results[best_pressure]['pressure_drop_psi']:.2f} psi")
        output.append("")
        output.append(f"Most Efficient (Pump Power): {best_efficiency.capitalize()}")
        output.append(f"  → Pump power: {results[best_efficiency]['pump_power_w']:.1f} W")
        output.append("")

        # Add selection guidance
        output.append("SELECTION GUIDE:")
        output.append("• Water: Best performance, lowest cost (use if no freeze risk)")
        output.append("• Glycol: Freeze protection for outdoor/cold climates (<0°C)")
        output.append("• Dielectric: Electrical isolation (immersion or direct contact)")

        # Check for warnings
        has_warnings = any(results[c]["warnings"] for c in coolant_types)
        if has_warnings:
            output.append("")
            output.append("⚠️  WARNINGS:")
            for coolant in coolant_types:
                if results[coolant]["warnings"]:
                    output.append(f"\n{coolant.capitalize()}:")
                    for warning in results[coolant]["warnings"]:
                        output.append(f"  • {warning}")

        return "\n".join(output)

    except ValueError as e:
        return f"Error: {str(e)}\n\nPlease check input parameters."
    except Exception as e:
        return f"Unexpected error during comparison: {str(e)}"


@mcp.tool()
def optimize_flow_rate(
    gpu_power_w: float,
    num_gpus: int = 1,
    target_temp_c: float = 80.0,
    coolant_type: Literal["water", "glycol", "dielectric"] = "water",
    ambient_temp_c: float = 25.0,
    min_flow_lpm: float = 5.0,
    max_flow_lpm: float = 30.0
) -> str:
    """
    Find the minimum flow rate needed to meet a temperature target.

    This tool optimizes cooling system design by finding the lowest flow rate
    that keeps GPU junction temperature below a specified limit. Lower flow
    rates mean smaller pumps, less power consumption, and lower system cost.

    Args:
        gpu_power_w: Power dissipation per GPU in Watts
        num_gpus: Number of GPUs in the system
        target_temp_c: Maximum allowable junction temperature in Celsius
            - Typical targets: 75-85°C for reliability
            - NVIDIA recommends <85°C for H100/H200
        coolant_type: Type of coolant fluid (water, glycol, or dielectric)
        ambient_temp_c: Inlet coolant temperature in Celsius
        min_flow_lpm: Minimum flow rate to consider (default: 5 LPM)
        max_flow_lpm: Maximum flow rate to consider (default: 30 LPM)

    Returns:
        Formatted optimization results showing:
        - Optimized flow rate to meet temperature target
        - Resulting junction temperature (at or below target)
        - Pressure drop and pump power at optimized flow rate
        - System efficiency metrics
        - Warnings if target cannot be achieved within flow rate bounds

    Example usage:
        optimize_flow_rate(
            gpu_power_w=700,
            num_gpus=1,
            target_temp_c=80,
            coolant_type="water",
            ambient_temp_c=25
        )
    """
    try:
        # Create thermal model
        model = ColdPlateModel(
            gpu_power_w=gpu_power_w,
            num_gpus=num_gpus,
            coolant_type=coolant_type,
            ambient_temp_c=ambient_temp_c
        )

        # Run optimization
        result = model.optimize_flow_rate(
            target_temp_c=target_temp_c,
            min_flow_lpm=min_flow_lpm,
            max_flow_lpm=max_flow_lpm
        )

        # Format output
        output = []
        output.append("=" * 80)
        output.append("FLOW RATE OPTIMIZATION RESULTS")
        output.append("=" * 80)
        output.append(f"System: {num_gpus}× {gpu_power_w}W GPUs = {num_gpus * gpu_power_w}W total")
        output.append(f"Coolant: {coolant_type.capitalize()}")
        output.append(f"Target Temperature: ≤{target_temp_c}°C")
        output.append(f"Inlet Temperature: {ambient_temp_c}°C")
        output.append("")

        output.append("OPTIMIZED OPERATING POINT")
        output.append("-" * 80)
        output.append(f"Flow Rate:          {result['flow_rate_lpm']:.2f} LPM")
        output.append(f"Junction Temp:      {result['junction_temp_c']:.1f}°C")
        output.append(f"Coolant Temp Rise:  {result['coolant_temp_rise_c']:.1f}°C")
        output.append(f"Pressure Drop:      {result['pressure_drop_psi']:.2f} psi")
        output.append(f"Pump Power:         {result['pump_power_w']:.1f} W")
        output.append("")

        # Check if target was achieved
        if result['junction_temp_c'] <= target_temp_c + 1:  # 1°C tolerance
            output.append("✓ Target temperature achieved!")
        else:
            output.append(f"⚠️  WARNING: Target temperature not achievable within flow rate bounds")
            output.append(f"   Best achievable: {result['junction_temp_c']:.1f}°C at {max_flow_lpm} LPM")
            output.append("")
            output.append("Recommendations:")
            output.append("  • Increase max flow rate limit")
            output.append("  • Use better coolant (water > glycol > dielectric)")
            output.append("  • Lower inlet temperature (chiller/economizer)")
            output.append("  • Reduce power per GPU (underclocking/power limits)")

        # Add efficiency notes
        output.append("")
        output.append("SYSTEM EFFICIENCY")
        output.append("-" * 80)
        pue_impact = result['pump_power_w'] / (num_gpus * gpu_power_w) * 100
        output.append(f"Pump power overhead: {pue_impact:.2f}% of GPU power")
        output.append(f"Total system power:  {num_gpus * gpu_power_w + result['pump_power_w']:.0f} W")

        if pue_impact < 2:
            output.append("→ Excellent efficiency (pump power <2% overhead)")
        elif pue_impact < 5:
            output.append("→ Good efficiency (pump power <5% overhead)")
        else:
            output.append("→ High pump power - consider lower target temp or better coolant")

        # Add warnings
        if result.get("warnings"):
            output.append("")
            output.append("⚠️  WARNINGS:")
            for warning in result["warnings"]:
                output.append(f"  • {warning}")

        return "\n".join(output)

    except ValueError as e:
        return f"Error: {str(e)}\n\nPlease check input parameters."
    except Exception as e:
        return f"Unexpected error during optimization: {str(e)}"


if __name__ == "__main__":
    import sys
    print("=" * 60, file=sys.stderr)
    print("Thermal MCP Server Starting...", file=sys.stderr)
    print("Server ready and waiting for connections.", file=sys.stderr)
    print("Press Ctrl+C to stop.", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Run the MCP server
    mcp.run()
