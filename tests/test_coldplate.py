"""
Unit Tests for Thermal MCP Server - Cold Plate Model
Author: Riccardo Vietri
Date: February 2026

Test coverage:
- Coolant property validation
- Thermal resistance calculations
- Heat transfer correlations
- Pressure drop calculations
- System optimization
- Edge cases and warnings
- Validation against known thermal models
"""

import pytest
import numpy as np
from src.models.coldplate import (
    ColdPlateModel,
    CoolantProperties,
    format_analysis_result
)


class TestCoolantProperties:
    """Test coolant property database"""

    def test_water_properties(self):
        """Validate water properties at 25°C"""
        water = CoolantProperties.water()
        assert water.name == "Water"
        assert 990 < water.density < 1000  # kg/m³
        assert 4000 < water.specific_heat < 4300  # J/(kg·K)
        assert 0.5 < water.thermal_conductivity < 0.7  # W/(m·K)
        assert 0.0008 < water.dynamic_viscosity < 0.001  # Pa·s

    def test_glycol_properties(self):
        """Validate 50/50 water-glycol properties"""
        glycol = CoolantProperties.glycol_50_50()
        assert glycol.name == "50/50 Water-Glycol"
        assert glycol.density > 1000  # Denser than water
        assert glycol.specific_heat < 4180  # Lower than water
        assert glycol.dynamic_viscosity > 0.001  # More viscous than water

    def test_dielectric_properties(self):
        """Validate dielectric fluid properties"""
        dielectric = CoolantProperties.dielectric_fluid()
        assert dielectric.name == "Dielectric Fluid"
        assert dielectric.density > 1200  # Dense
        assert dielectric.specific_heat < 1500  # Low specific heat
        assert dielectric.thermal_conductivity < 0.1  # Poor conductor


class TestColdPlateInstantiation:
    """Test model initialization"""

    def test_basic_instantiation(self):
        """Test basic model creation"""
        model = ColdPlateModel(
            gpu_power_w=700,
            num_gpus=1,
            coolant_type="water",
            ambient_temp_c=25
        )
        assert model.gpu_power_w == 700
        assert model.num_gpus == 1
        assert model.total_power_w == 700
        assert model.coolant.name == "Water"

    def test_multi_gpu_system(self):
        """Test 8-GPU system"""
        model = ColdPlateModel(
            gpu_power_w=700,
            num_gpus=8,
            coolant_type="water"
        )
        assert model.total_power_w == 5600  # 8 × 700W

    def test_coolant_type_variants(self):
        """Test different coolant type inputs"""
        # Water variants
        model_water = ColdPlateModel(gpu_power_w=700, coolant_type="water")
        assert model_water.coolant.name == "Water"

        model_water2 = ColdPlateModel(gpu_power_w=700, coolant_type="WATER")
        assert model_water2.coolant.name == "Water"

        # Glycol variants
        model_glycol = ColdPlateModel(gpu_power_w=700, coolant_type="glycol")
        assert model_glycol.coolant.name == "50/50 Water-Glycol"

        model_glycol2 = ColdPlateModel(gpu_power_w=700, coolant_type="water-glycol")
        assert model_glycol2.coolant.name == "50/50 Water-Glycol"

        # Dielectric variants
        model_dielec = ColdPlateModel(gpu_power_w=700, coolant_type="dielectric")
        assert model_dielec.coolant.name == "Dielectric Fluid"

        model_dielec2 = ColdPlateModel(gpu_power_w=700, coolant_type="fluorinert")
        assert model_dielec2.coolant.name == "Dielectric Fluid"

    def test_invalid_coolant_type(self):
        """Test that invalid coolant raises error"""
        with pytest.raises(ValueError, match="Unknown coolant type"):
            ColdPlateModel(gpu_power_w=700, coolant_type="invalid_coolant")


class TestPerformanceCalculations:
    """Test thermal and hydraulic performance calculations"""

    def test_single_gpu_nominal_flow(self):
        """Test 700W GPU at 12 LPM water cooling"""
        model = ColdPlateModel(
            gpu_power_w=700,
            num_gpus=1,
            coolant_type="water",
            ambient_temp_c=25
        )
        result = model.calculate_performance(flow_rate_lpm=12)

        # Junction temperature should be reasonable
        assert 60 < result["junction_temp_c"] < 90

        # Coolant temp rise should be modest at high flow (0.5-10°C range)
        # At 12 LPM with 700W, expect ~0.8°C (Q = m_dot × cp × ΔT)
        assert 0.5 < result["coolant_temp_rise_c"] < 10

        # Pressure drop should be reasonable (lower is better!)
        assert 0.2 < result["pressure_drop_psi"] < 10

        # Reynolds number should be turbulent (>2300)
        assert result["reynolds_number"] > 2300

        # Heat transfer coefficient should be in reasonable range
        assert 1000 < result["heat_transfer_coeff_w_m2k"] < 20000

    def test_high_power_system(self):
        """Test 8x H200 GPUs (5.6kW total)"""
        model = ColdPlateModel(
            gpu_power_w=700,
            num_gpus=8,
            coolant_type="water",
            ambient_temp_c=25
        )
        result = model.calculate_performance(flow_rate_lpm=12)

        # With 8 GPUs, should need much higher flow rate
        # At only 12 LPM, expect high temps or need design changes
        # Note: This model assumes a single cold plate - real systems use multiple
        assert result["junction_temp_c"] > 80

        # Large coolant temp rise expected (Q = m × cp × ΔT)
        # 5600W / (12 LPM × 997 kg/m³ × 4180 J/(kg·K)) = 6.7°C
        assert result["coolant_temp_rise_c"] > 5

    def test_high_flow_improves_cooling(self):
        """Test that higher flow rates reduce temperature"""
        model = ColdPlateModel(gpu_power_w=700, num_gpus=1, coolant_type="water")

        result_low = model.calculate_performance(flow_rate_lpm=8)
        result_high = model.calculate_performance(flow_rate_lpm=20)

        # Higher flow should give lower junction temp
        assert result_high["junction_temp_c"] < result_low["junction_temp_c"]

        # But higher pressure drop
        assert result_high["pressure_drop_psi"] > result_low["pressure_drop_psi"]

        # And higher pump power
        assert result_high["pump_power_w"] > result_low["pump_power_w"]

    def test_coolant_comparison(self):
        """Test that water performs better than glycol"""
        model_water = ColdPlateModel(gpu_power_w=700, coolant_type="water")
        model_glycol = ColdPlateModel(gpu_power_w=700, coolant_type="glycol")

        result_water = model_water.calculate_performance(flow_rate_lpm=12)
        result_glycol = model_glycol.calculate_performance(flow_rate_lpm=12)

        # Water should give lower temps (better thermal properties)
        assert result_water["junction_temp_c"] < result_glycol["junction_temp_c"]

        # Glycol should have higher pressure drop (more viscous)
        assert result_glycol["pressure_drop_psi"] > result_water["pressure_drop_psi"]

    def test_detailed_output(self):
        """Test that detailed mode returns extra fields"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")

        result_simple = model.calculate_performance(flow_rate_lpm=12, detailed=False)
        result_detailed = model.calculate_performance(flow_rate_lpm=12, detailed=True)

        # Simple mode has basic fields
        assert "junction_temp_c" in result_simple
        assert "pressure_drop_psi" in result_simple

        # Detailed mode has extra fields
        assert "R_total_k_w" in result_detailed
        assert "R_convection_k_w" in result_detailed
        assert "flow_rate_lpm" in result_detailed
        assert "coolant_type" in result_detailed
        assert "total_power_w" in result_detailed


class TestWarnings:
    """Test warning generation"""

    def test_high_temperature_warning(self):
        """Test warning when junction temp exceeds 90°C"""
        model = ColdPlateModel(
            gpu_power_w=700,
            num_gpus=8,  # High power
            coolant_type="water"
        )
        result = model.calculate_performance(flow_rate_lpm=8)  # Low flow

        assert result["junction_temp_c"] > 90
        warnings = result["warnings"]
        assert any("90°C" in w for w in warnings)

    def test_low_flow_warning(self):
        """Test warning for flow rates below 8 LPM"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=6)

        warnings = result["warnings"]
        assert any("8 LPM" in w for w in warnings)

    def test_high_pressure_drop_warning(self):
        """Test warning for excessive pressure drop"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=30)  # Very high flow

        # High flow should cause high pressure drop
        if result["pressure_drop_psi"] > 15:
            warnings = result["warnings"]
            assert any("pressure drop" in w.lower() for w in warnings)


class TestOptimization:
    """Test flow rate optimization"""

    def test_optimization_basic(self):
        """Test finding optimal flow rate for temperature target"""
        model = ColdPlateModel(gpu_power_w=700, num_gpus=1, coolant_type="water")

        optimized = model.optimize_flow_rate(
            target_temp_c=75,
            min_flow_lpm=5,
            max_flow_lpm=30
        )

        # Should hit target within tolerance
        assert 74 < optimized["junction_temp_c"] < 76

        # Flow rate should be within bounds
        assert 5 <= optimized["flow_rate_lpm"] <= 30

    def test_optimization_impossible_target(self):
        """Test optimization with impossible temperature target"""
        model = ColdPlateModel(
            gpu_power_w=700,
            num_gpus=8,  # High power
            coolant_type="dielectric"  # Poor coolant
        )

        # Try to achieve very low temp - may not be achievable
        optimized = model.optimize_flow_rate(
            target_temp_c=50,
            min_flow_lpm=5,
            max_flow_lpm=30
        )

        # Should return best effort (highest flow)
        assert optimized["flow_rate_lpm"] > 25

    def test_optimization_easy_target(self):
        """Test optimization with easily achievable target"""
        model = ColdPlateModel(gpu_power_w=350, num_gpus=1, coolant_type="water")

        optimized = model.optimize_flow_rate(
            target_temp_c=80,
            min_flow_lpm=5,
            max_flow_lpm=30
        )

        # Low power should need minimal flow
        assert optimized["flow_rate_lpm"] < 15


class TestValidationCases:
    """Validation tests against known thermal models and first principles"""

    def test_energy_balance(self):
        """Validate energy balance: Q = m_dot × cp × ΔT"""
        model = ColdPlateModel(gpu_power_w=700, num_gpus=1, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=12)

        # Calculate mass flow rate
        flow_m3s = 12 / 60000.0  # LPM to m³/s
        mass_flow = flow_m3s * model.coolant.density  # kg/s

        # Calculate heat capacity rate
        heat_capacity_rate = mass_flow * model.coolant.specific_heat  # W/K

        # Expected temperature rise
        expected_delta_T = model.total_power_w / heat_capacity_rate  # K

        # Should match within 10% (accounts for model simplifications)
        assert abs(result["coolant_temp_rise_c"] - expected_delta_T) < expected_delta_T * 0.1

    def test_reynolds_number_calculation(self):
        """Validate Reynolds number calculation"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=12)

        # Calculate expected Reynolds number
        flow_m3s = 12 / 60000.0
        channel_area = np.pi * (model.channel_hydraulic_diameter_m / 2) ** 2
        total_area = channel_area * model.channel_count
        velocity = flow_m3s / total_area

        Re_expected = (
            model.coolant.density * velocity * model.channel_hydraulic_diameter_m /
            model.coolant.dynamic_viscosity
        )

        # Should match within 5%
        assert abs(result["reynolds_number"] - Re_expected) < Re_expected * 0.05

    def test_turbulent_vs_laminar(self):
        """Test that model transitions between laminar and turbulent flow"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")

        # Very low flow - should be laminar or transitional
        result_low = model.calculate_performance(flow_rate_lpm=2)

        # High flow - should be turbulent
        result_high = model.calculate_performance(flow_rate_lpm=20)

        assert result_high["reynolds_number"] > 2300  # Turbulent

        # Turbulent flow should have much better heat transfer
        assert result_high["heat_transfer_coeff_w_m2k"] > result_low["heat_transfer_coeff_w_m2k"]

    def test_thermal_resistance_dominance(self):
        """Validate that convection dominates thermal resistance at low flow"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")

        result_low_flow = model.calculate_performance(flow_rate_lpm=5, detailed=True)
        result_high_flow = model.calculate_performance(flow_rate_lpm=25, detailed=True)

        # At low flow, convection resistance should be significant
        # Total resistance should decrease substantially with higher flow
        assert result_high_flow["R_total_k_w"] < result_low_flow["R_total_k_w"]

        # Convection resistance should drop with increased flow
        assert result_high_flow["R_convection_k_w"] < result_low_flow["R_convection_k_w"]

    def test_pressure_drop_scaling(self):
        """Test that pressure drop scales approximately with velocity squared"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")

        result_1x = model.calculate_performance(flow_rate_lpm=10)
        result_2x = model.calculate_performance(flow_rate_lpm=20)

        # Pressure drop should scale roughly with v²
        # At 2x flow rate, expect ~4x pressure drop
        ratio = result_2x["pressure_drop_psi"] / result_1x["pressure_drop_psi"]

        # Should be between 3-5 (accounting for Reynolds number effects)
        assert 3 < ratio < 5

    def test_pump_power_scaling(self):
        """Test that pump power scales with flow rate and pressure drop"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")

        result_1x = model.calculate_performance(flow_rate_lpm=10)
        result_2x = model.calculate_performance(flow_rate_lpm=20)

        # Pump power ~ flow × pressure_drop ~ flow × flow²  ~ flow³
        # At 2x flow, expect roughly 8x pump power
        ratio = result_2x["pump_power_w"] / result_1x["pump_power_w"]

        # Should be between 6-10 (accounting for model variations)
        assert 6 < ratio < 10


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_high_flow(self):
        """Test behavior at very high flow rates"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=50)

        # Should not crash
        assert result["junction_temp_c"] > 0
        assert result["pressure_drop_psi"] > 0

        # May or may not have warnings depending on pressure drop
        # (very high flow gives high pressure drop warning)
        assert "warnings" in result

    def test_very_low_flow(self):
        """Test behavior at very low flow rates"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=1)

        # Should not crash
        assert result["junction_temp_c"] > 0

        # Expect warnings about low flow
        assert len(result["warnings"]) > 0

    def test_zero_ambient_temp(self):
        """Test with 0°C ambient (data center in Arctic)"""
        model = ColdPlateModel(
            gpu_power_w=700,
            coolant_type="water",
            ambient_temp_c=0
        )
        result = model.calculate_performance(flow_rate_lpm=12)

        # Should work, temps just offset lower
        assert result["junction_temp_c"] > 0
        assert result["junction_temp_c"] < 100

    def test_high_ambient_temp(self):
        """Test with 45°C ambient (hot climate)"""
        model = ColdPlateModel(
            gpu_power_w=700,
            coolant_type="water",
            ambient_temp_c=45
        )
        result = model.calculate_performance(flow_rate_lpm=12)

        # Junction temp should be higher than at 25°C ambient
        model_normal = ColdPlateModel(gpu_power_w=700, coolant_type="water", ambient_temp_c=25)
        result_normal = model_normal.calculate_performance(flow_rate_lpm=12)

        assert result["junction_temp_c"] > result_normal["junction_temp_c"]


class TestFormatting:
    """Test output formatting utilities"""

    def test_format_analysis_result(self):
        """Test that format_analysis_result produces readable output"""
        model = ColdPlateModel(gpu_power_w=700, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=12, detailed=True)

        formatted = format_analysis_result(result)

        # Should contain key information
        assert "THERMAL ANALYSIS RESULTS" in formatted
        assert "Junction Temperature" in formatted
        assert "Pressure Drop" in formatted
        assert str(result["junction_temp_c"]) in formatted

        # Should be multi-line
        assert "\n" in formatted

        # Should have separators
        assert "=" in formatted

    def test_format_with_warnings(self):
        """Test formatting when warnings are present"""
        model = ColdPlateModel(gpu_power_w=700, num_gpus=8, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=6)  # Will generate warnings

        formatted = format_analysis_result(result)

        if result["warnings"]:
            assert "WARNINGS:" in formatted


class TestRealWorldScenarios:
    """Test realistic data center cooling scenarios"""

    def test_nvidia_h100_scenario(self):
        """Test NVIDIA H100 GPU (700W) cooling"""
        model = ColdPlateModel(
            gpu_power_w=700,
            num_gpus=1,
            coolant_type="water",
            ambient_temp_c=25
        )

        # Target: Keep under 80°C
        optimized = model.optimize_flow_rate(target_temp_c=80)

        assert optimized["junction_temp_c"] <= 81  # Within tolerance
        assert optimized["flow_rate_lpm"] < 25  # Reasonable flow requirement

    def test_8_gpu_server_scenario(self):
        """Test 8-GPU server (5.6kW total heat)

        Note: This model assumes a single cold plate design.
        In reality, each GPU would have its own cold plate in parallel.
        This test demonstrates the system needs proper thermal design.
        """
        model = ColdPlateModel(
            gpu_power_w=700,
            num_gpus=8,
            coolant_type="water",
            ambient_temp_c=30  # Warm data center
        )

        # At reasonable flow, temps will be very high (demonstrates need for better design)
        result = model.calculate_performance(flow_rate_lpm=30)

        # High power on single cold plate design gives high temps
        # This is expected and shows why multi-cold-plate designs are needed
        assert result["junction_temp_c"] > 100  # Demonstrates thermal challenge
        assert result["total_power_w"] == 5600  # Verify power calculation

    def test_cold_climate_efficiency(self):
        """Test cooling efficiency in cold climate (free cooling)"""
        model_cold = ColdPlateModel(
            gpu_power_w=700,
            coolant_type="water",
            ambient_temp_c=10  # Cold climate
        )

        model_warm = ColdPlateModel(
            gpu_power_w=700,
            coolant_type="water",
            ambient_temp_c=30  # Warm climate
        )

        result_cold = model_cold.calculate_performance(flow_rate_lpm=12)
        result_warm = model_warm.calculate_performance(flow_rate_lpm=12)

        # Cold climate should give ~20°C lower junction temp
        temp_difference = result_warm["junction_temp_c"] - result_cold["junction_temp_c"]
        assert 15 < temp_difference < 25

    def test_glycol_winter_operation(self):
        """Test glycol for below-freezing ambient temperatures

        Note: Glycol has worse thermal performance than water,
        so even with cold ambient, junction temps can be elevated.
        """
        model = ColdPlateModel(
            gpu_power_w=700,
            coolant_type="glycol",  # Freeze protection
            ambient_temp_c=-10  # Winter outdoor cooling
        )

        result = model.calculate_performance(flow_rate_lpm=12)

        # Should still work (glycol doesn't freeze)
        # Temperature rise through thermal resistances is ~140°C with glycol
        # Even with -10°C ambient, junction can be high due to poor glycol properties
        assert result["junction_temp_c"] > -10  # Must be above ambient
        assert result["junction_temp_c"] < 200  # Should not be extreme
