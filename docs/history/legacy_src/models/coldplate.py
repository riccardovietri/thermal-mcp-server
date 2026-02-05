"""
Thermal MCP Server - Core Cold Plate Model
Author: Riccardo (Staff Thermal Engineer, Tesla)
Date: February 2026

This module implements a 1D thermal resistance network for GPU cold plate cooling.
Used for rapid thermal analysis of data center liquid cooling systems.

References:
- Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer"
- Based on 4 years of thermal simulation experience at Tesla
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class CoolantProperties:
    """Thermophysical properties of cooling fluids"""
    name: str
    density: float  # kg/m³
    specific_heat: float  # J/(kg·K)
    thermal_conductivity: float  # W/(m·K)
    dynamic_viscosity: float  # Pa·s
    
    @classmethod
    def water(cls, temp_c: float = 25.0):
        """Water properties at given temperature"""
        # TODO: Add temperature-dependent properties
        return cls(
            name="Water",
            density=997.0,
            specific_heat=4180.0,
            thermal_conductivity=0.607,
            dynamic_viscosity=0.000891
        )
    
    @classmethod
    def glycol_50_50(cls, temp_c: float = 25.0):
        """50/50 Water-Glycol properties"""
        # TODO: Add temperature-dependent properties
        return cls(
            name="50/50 Water-Glycol",
            density=1070.0,
            specific_heat=3400.0,
            thermal_conductivity=0.415,
            dynamic_viscosity=0.00390
        )
    
    @classmethod
    def dielectric_fluid(cls, temp_c: float = 25.0):
        """Typical dielectric fluid (e.g., 3M Novec)"""
        return cls(
            name="Dielectric Fluid",
            density=1520.0,
            specific_heat=1100.0,
            thermal_conductivity=0.065,
            dynamic_viscosity=0.00064
        )


class ColdPlateModel:
    """
    1D Thermal Resistance Network for GPU Cold Plate Cooling
    
    Thermal path: GPU Junction → Case → TIM → Cold Plate → Coolant → Ambient
    
    Key assumptions:
    - Steady-state operation
    - Uniform heat generation
    - 1D heat transfer (conservative)
    - Turbulent flow in channels (Re > 2300)
    """
    
    def __init__(
        self,
        gpu_power_w: float,
        num_gpus: int = 1,
        coolant_type: str = "water",
        ambient_temp_c: float = 25.0
    ):
        """
        Initialize cold plate thermal model
        
        Args:
            gpu_power_w: Power dissipation per GPU (W)
            num_gpus: Number of GPUs on this cold plate
            coolant_type: "water", "glycol", or "dielectric"
            ambient_temp_c: Ambient/inlet coolant temperature (°C)
        """
        self.gpu_power_w = gpu_power_w
        self.num_gpus = num_gpus
        self.total_power_w = gpu_power_w * num_gpus
        self.ambient_temp_c = ambient_temp_c
        
        # Get coolant properties
        if coolant_type.lower() == "water":
            self.coolant = CoolantProperties.water()
        elif coolant_type.lower() in ["glycol", "water-glycol"]:
            self.coolant = CoolantProperties.glycol_50_50()
        elif coolant_type.lower() in ["dielectric", "fluorinert"]:
            self.coolant = CoolantProperties.dielectric_fluid()
        else:
            raise ValueError(f"Unknown coolant type: {coolant_type}")
        
        # Typical thermal resistances (K/W) - for high-power GPUs with liquid cooling
        # These values reflect modern data center GPU designs (H100, H200 class)
        self.R_junction_to_case = 0.03  # GPU internal (improved die-to-IHS path)
        self.R_tim = 0.015  # High-performance thermal interface material
        self.R_coldplate_conduction = 0.005  # Cold plate base conduction (Cu/Al)
        
        # Cold plate geometry (typical values)
        self.channel_hydraulic_diameter_m = 0.003  # 3mm channels
        self.channel_length_m = 0.15  # 150mm flow path
        self.channel_count = 20  # Parallel channels
        
    def calculate_performance(
        self,
        flow_rate_lpm: float,
        detailed: bool = True
    ) -> Dict[str, float]:
        """
        Calculate thermal and hydraulic performance
        
        Args:
            flow_rate_lpm: Total coolant flow rate (liters per minute)
            detailed: If True, return detailed breakdown
            
        Returns:
            Dictionary with performance metrics
        """
        # Convert flow rate to SI units
        flow_rate_m3s = flow_rate_lpm / 60000.0  # LPM to m³/s
        
        # Calculate convective heat transfer coefficient
        h_convection, reynolds_num = self._calculate_heat_transfer_coefficient(
            flow_rate_m3s
        )
        
        # Calculate convection thermal resistance
        # Scale contact area by number of GPUs (each GPU ~100 cm²)
        contact_area_per_gpu_m2 = 0.01  # 100 cm² typical GPU cold plate
        total_contact_area_m2 = contact_area_per_gpu_m2 * self.num_gpus
        R_convection = 1.0 / (h_convection * total_contact_area_m2)

        # Total thermal resistance from junction to coolant
        # For multi-GPU systems, junction-to-case and TIM are per-GPU (parallel paths)
        # while coldplate conduction and convection are already scaled above
        R_junction_effective = self.R_junction_to_case / self.num_gpus
        R_tim_effective = self.R_tim / self.num_gpus
        R_coldplate_effective = self.R_coldplate_conduction / self.num_gpus

        R_total = (
            R_junction_effective +
            R_tim_effective +
            R_coldplate_effective +
            R_convection
        )
        
        # Junction temperature rise
        delta_T_junction = self.total_power_w * R_total
        
        # Coolant temperature rise (energy balance)
        mass_flow_rate = flow_rate_m3s * self.coolant.density
        delta_T_coolant = self.total_power_w / (
            mass_flow_rate * self.coolant.specific_heat
        )
        
        # Average coolant temperature
        T_coolant_avg = self.ambient_temp_c + delta_T_coolant / 2
        
        # Junction temperature
        T_junction = T_coolant_avg + delta_T_junction
        
        # Calculate pressure drop
        pressure_drop_pa, pressure_drop_psi = self._calculate_pressure_drop(
            flow_rate_m3s, reynolds_num
        )
        
        # Required pump power (assuming 50% pump efficiency)
        pump_efficiency = 0.50
        pump_power_w = (flow_rate_m3s * pressure_drop_pa) / pump_efficiency
        
        # Performance metrics
        result = {
            "junction_temp_c": round(T_junction, 1),
            "coolant_temp_rise_c": round(delta_T_coolant, 1),
            "pressure_drop_psi": round(pressure_drop_psi, 2),
            "pump_power_w": round(pump_power_w, 1),
            "reynolds_number": round(reynolds_num, 0),
            "heat_transfer_coeff_w_m2k": round(h_convection, 0),
        }
        
        if detailed:
            result.update({
                "R_total_k_w": round(R_total, 4),
                "R_convection_k_w": round(R_convection, 4),
                "flow_rate_lpm": flow_rate_lpm,
                "coolant_type": self.coolant.name,
                "total_power_w": self.total_power_w,
            })
        
        # Add warnings
        warnings = []
        if T_junction > 90:
            warnings.append("⚠️ Junction temperature exceeds 90°C - increase flow rate")
        if flow_rate_lpm < 8:
            warnings.append("⚠️ Flow rate below 8 LPM - may have flow instability")
        if pressure_drop_psi > 15:
            warnings.append("⚠️ High pressure drop - consider manifold redesign")
        
        result["warnings"] = warnings
        
        return result
    
    def _calculate_heat_transfer_coefficient(
        self,
        flow_rate_m3s: float
    ) -> Tuple[float, float]:
        """
        Calculate convective heat transfer coefficient using Dittus-Boelter correlation
        
        Returns:
            (h_convection, reynolds_number)
        """
        # Flow velocity in channels
        channel_area_m2 = np.pi * (self.channel_hydraulic_diameter_m / 2) ** 2
        total_channel_area_m2 = channel_area_m2 * self.channel_count
        velocity_ms = flow_rate_m3s / total_channel_area_m2
        
        # Reynolds number
        Re = (
            self.coolant.density * velocity_ms * self.channel_hydraulic_diameter_m /
            self.coolant.dynamic_viscosity
        )
        
        # Prandtl number
        Pr = (
            self.coolant.specific_heat * self.coolant.dynamic_viscosity /
            self.coolant.thermal_conductivity
        )
        
        # Nusselt number (Dittus-Boelter for turbulent flow)
        if Re > 2300:  # Turbulent
            Nu = 0.023 * (Re ** 0.8) * (Pr ** 0.4)
        else:  # Laminar (conservative estimate)
            Nu = 4.36  # Fully developed laminar flow in circular tube
        
        # Heat transfer coefficient
        h = Nu * self.coolant.thermal_conductivity / self.channel_hydraulic_diameter_m
        
        return h, Re
    
    def _calculate_pressure_drop(
        self,
        flow_rate_m3s: float,
        reynolds_num: float
    ) -> Tuple[float, float]:
        """
        Calculate pressure drop using Darcy-Weisbach equation
        
        Returns:
            (pressure_drop_pa, pressure_drop_psi)
        """
        # Flow velocity
        channel_area_m2 = np.pi * (self.channel_hydraulic_diameter_m / 2) ** 2
        total_channel_area_m2 = channel_area_m2 * self.channel_count
        velocity_ms = flow_rate_m3s / total_channel_area_m2
        
        # Friction factor (Haaland approximation for turbulent flow)
        if reynolds_num > 2300:
            # Assuming smooth channels (typical for machined cold plates)
            f = 0.316 * (reynolds_num ** -0.25)  # Blasius correlation
        else:
            # Laminar flow
            f = 64 / reynolds_num
        
        # Pressure drop (Darcy-Weisbach)
        pressure_drop_pa = f * (
            self.channel_length_m / self.channel_hydraulic_diameter_m
        ) * (self.coolant.density * velocity_ms ** 2) / 2
        
        # Add minor losses (fittings, manifolds) - typically 20% of major losses
        pressure_drop_pa *= 1.2
        
        # Convert to PSI
        pressure_drop_psi = pressure_drop_pa / 6894.76
        
        return pressure_drop_pa, pressure_drop_psi
    
    def optimize_flow_rate(
        self,
        target_temp_c: float,
        min_flow_lpm: float = 5.0,
        max_flow_lpm: float = 30.0
    ) -> Dict[str, float]:
        """
        Find minimum flow rate to meet temperature target
        
        Args:
            target_temp_c: Maximum allowable junction temperature
            min_flow_lpm: Minimum flow rate to consider
            max_flow_lpm: Maximum flow rate to consider
            
        Returns:
            Optimized performance dictionary
        """
        # Binary search for optimal flow rate
        flow_low = min_flow_lpm
        flow_high = max_flow_lpm
        tolerance = 0.1  # °C
        
        for _ in range(20):  # Max iterations
            flow_mid = (flow_low + flow_high) / 2
            result = self.calculate_performance(flow_mid, detailed=False)
            
            if abs(result["junction_temp_c"] - target_temp_c) < tolerance:
                return self.calculate_performance(flow_mid, detailed=True)
            
            if result["junction_temp_c"] > target_temp_c:
                flow_low = flow_mid  # Need more flow
            else:
                flow_high = flow_mid  # Can reduce flow
        
        # Return result at midpoint
        return self.calculate_performance(flow_mid, detailed=True)


def format_analysis_result(result: Dict[str, float]) -> str:
    """Format analysis results for display"""
    output = []
    output.append("=" * 60)
    output.append("THERMAL ANALYSIS RESULTS")
    output.append("=" * 60)
    output.append(f"Coolant Type: {result.get('coolant_type', 'N/A')}")
    output.append(f"Total Heat Load: {result.get('total_power_w', 0):.0f} W")
    output.append(f"Flow Rate: {result.get('flow_rate_lpm', 0):.1f} LPM")
    output.append("")
    output.append("TEMPERATURES:")
    output.append(f"  Junction Temperature: {result['junction_temp_c']:.1f}°C")
    output.append(f"  Coolant Temperature Rise: {result['coolant_temp_rise_c']:.1f}°C")
    output.append("")
    output.append("HYDRAULICS:")
    output.append(f"  Pressure Drop: {result['pressure_drop_psi']:.2f} psi")
    output.append(f"  Pump Power: {result['pump_power_w']:.1f} W")
    output.append(f"  Reynolds Number: {result['reynolds_number']:.0f}")
    output.append("")

    # Add detailed thermal resistance breakdown if available
    if "R_total_k_w" in result:
        output.append("THERMAL RESISTANCE BREAKDOWN:")
        output.append(f"  Junction-to-Case: {result.get('R_junction_to_case_k_w', 0):.4f} K/W")
        output.append(f"  TIM: {result.get('R_tim_k_w', 0):.4f} K/W")
        output.append(f"  Cold Plate Conduction: {result.get('R_coldplate_cond_k_w', 0):.4f} K/W")
        output.append(f"  Convection: {result.get('R_convection_k_w', 0):.4f} K/W")
        output.append(f"  Total: {result['R_total_k_w']:.4f} K/W")
        output.append("")

    if result.get("warnings"):
        output.append("WARNINGS:")
        for warning in result["warnings"]:
            output.append(f"  {warning}")
        output.append("")

    output.append("=" * 60)
    return "\n".join(output)


# Example usage
if __name__ == "__main__":
    # Example: 8x NVIDIA H200 GPUs
    model = ColdPlateModel(
        gpu_power_w=700,
        num_gpus=8,
        coolant_type="water",
        ambient_temp_c=25
    )
    
    # Analyze at 12 LPM
    result = model.calculate_performance(flow_rate_lpm=12)
    print(format_analysis_result(result))
    
    # Optimize for 80°C target
    print("\nOPTIMIZATION FOR 80°C TARGET:")
    optimized = model.optimize_flow_rate(target_temp_c=80)
    print(format_analysis_result(optimized))
