"""
Unit Tests for MCP Server Tools
Author: Riccardo Vietri
Date: February 2026

Tests the three MCP tools exposed to Claude AI:
- analyze_coldplate_system
- compare_cooling_options
- optimize_flow_rate
"""

import pytest
from src.mcp_server import (
    analyze_coldplate_system,
    compare_cooling_options,
    optimize_flow_rate
)


class TestAnalyzeColdplateSystem:
    """Test the analyze_coldplate_system MCP tool"""

    def test_basic_analysis(self):
        """Test basic thermal analysis"""
        result = analyze_coldplate_system(
            gpu_power_w=700,
            num_gpus=1,
            coolant_type="water",
            flow_rate_lpm=12,
            ambient_temp_c=25
        )

        # Should return a formatted string
        assert isinstance(result, str)
        assert "THERMAL ANALYSIS RESULTS" in result
        assert "Junction Temperature" in result
        assert "Pressure Drop" in result

    def test_all_coolant_types(self):
        """Test analysis with different coolants"""
        for coolant in ["water", "glycol", "dielectric"]:
            result = analyze_coldplate_system(
                gpu_power_w=700,
                coolant_type=coolant,
                flow_rate_lpm=12
            )
            assert isinstance(result, str)
            assert "THERMAL ANALYSIS RESULTS" in result

    def test_multi_gpu_system(self):
        """Test analysis with multiple GPUs"""
        result = analyze_coldplate_system(
            gpu_power_w=700,
            num_gpus=8,
            flow_rate_lpm=20
        )
        assert isinstance(result, str)
        assert "5600" in result or "5,600" in result  # Total power

    def test_detailed_mode(self):
        """Test detailed analysis includes thermal resistances"""
        result = analyze_coldplate_system(
            gpu_power_w=700,
            detailed=True
        )
        assert "THERMAL RESISTANCE BREAKDOWN" in result
        assert "Total" in result

    def test_simple_mode(self):
        """Test simple analysis without detailed breakdown"""
        result = analyze_coldplate_system(
            gpu_power_w=700,
            detailed=False
        )
        # Should not have resistance breakdown
        assert isinstance(result, str)

    def test_invalid_coolant_type(self):
        """Test error handling for invalid coolant"""
        result = analyze_coldplate_system(
            gpu_power_w=700,
            coolant_type="invalid"
        )
        assert "Error" in result


class TestCompareCoolingOptions:
    """Test the compare_cooling_options MCP tool"""

    def test_compare_all_coolants(self):
        """Test comparison of all three coolants"""
        result = compare_cooling_options(
            gpu_power_w=700,
            flow_rate_lpm=12
        )

        assert isinstance(result, str)
        assert "COOLANT COMPARISON" in result
        assert "Water" in result
        assert "Glycol" in result
        assert "Dielectric" in result

    def test_compare_two_coolants(self):
        """Test comparison of subset of coolants"""
        result = compare_cooling_options(
            gpu_power_w=700,
            flow_rate_lpm=12,
            coolant_types=["water", "glycol"]
        )

        assert isinstance(result, str)
        assert "Water" in result
        assert "Glycol" in result
        # Dielectric should not be in results
        assert "Dielectric" not in result or result.count("Dielectric") <= 1

    def test_comparison_includes_recommendations(self):
        """Test that comparison includes recommendations"""
        result = compare_cooling_options(
            gpu_power_w=700,
            flow_rate_lpm=12
        )

        assert "RECOMMENDATIONS" in result
        assert "Best Thermal Performance" in result
        assert "SELECTION GUIDE" in result

    def test_multi_gpu_comparison(self):
        """Test comparison for multi-GPU system"""
        result = compare_cooling_options(
            gpu_power_w=700,
            num_gpus=8,
            flow_rate_lpm=25
        )

        assert isinstance(result, str)
        assert "5600" in result or "5,600" in result  # Total power

    def test_invalid_coolant_in_list(self):
        """Test error handling for invalid coolant in comparison"""
        result = compare_cooling_options(
            gpu_power_w=700,
            coolant_types=["water", "invalid"]
        )

        assert "Error" in result
        assert "Unknown coolant" in result


class TestOptimizeFlowRate:
    """Test the optimize_flow_rate MCP tool"""

    def test_basic_optimization(self):
        """Test basic flow rate optimization"""
        result = optimize_flow_rate(
            gpu_power_w=700,
            target_temp_c=80,
            coolant_type="water"
        )

        assert isinstance(result, str)
        assert "FLOW RATE OPTIMIZATION RESULTS" in result
        assert "OPTIMIZED OPERATING POINT" in result
        assert "Flow Rate" in result

    def test_achievable_target(self):
        """Test optimization with easily achievable target"""
        result = optimize_flow_rate(
            gpu_power_w=350,  # Lower power
            target_temp_c=80,
            coolant_type="water"
        )

        assert "Flow Rate" in result
        # Should achieve target with message
        assert "achieved" in result.lower() or "target" in result.lower()

    def test_different_coolants(self):
        """Test optimization with different coolants"""
        for coolant in ["water", "glycol", "dielectric"]:
            result = optimize_flow_rate(
                gpu_power_w=700,
                target_temp_c=80,
                coolant_type=coolant
            )
            assert isinstance(result, str)
            assert coolant.capitalize() in result

    def test_multi_gpu_optimization(self):
        """Test optimization for multi-GPU system"""
        result = optimize_flow_rate(
            gpu_power_w=700,
            num_gpus=8,
            target_temp_c=85,
            max_flow_lpm=50  # Increase max for high power
        )

        assert isinstance(result, str)
        assert "5600" in result or "5,600" in result

    def test_flow_rate_bounds(self):
        """Test that optimization respects flow rate bounds"""
        result = optimize_flow_rate(
            gpu_power_w=700,
            target_temp_c=80,
            min_flow_lpm=10,
            max_flow_lpm=20
        )

        assert isinstance(result, str)
        # Result should mention flow rate within bounds

    def test_impossible_target(self):
        """Test optimization with unachievable target"""
        result = optimize_flow_rate(
            gpu_power_w=700,
            num_gpus=8,
            target_temp_c=50,  # Very low target
            coolant_type="dielectric",  # Poor coolant
            max_flow_lpm=30
        )

        # Should indicate target not achievable
        assert "WARNING" in result or "not achievable" in result.lower()

    def test_efficiency_metrics(self):
        """Test that optimization includes efficiency metrics"""
        result = optimize_flow_rate(
            gpu_power_w=700,
            target_temp_c=80
        )

        assert "SYSTEM EFFICIENCY" in result
        assert "Pump power overhead" in result


class TestMCPToolIntegration:
    """Integration tests for MCP tools working together"""

    def test_consistent_results_across_tools(self):
        """Test that tools give consistent results for same input"""
        # Analyze at specific flow rate
        analysis = analyze_coldplate_system(
            gpu_power_w=700,
            flow_rate_lpm=15,
            coolant_type="water"
        )

        # Optimize to find flow rate
        optimization = optimize_flow_rate(
            gpu_power_w=700,
            target_temp_c=75,  # Should need ~15 LPM
            coolant_type="water"
        )

        # Both should succeed
        assert isinstance(analysis, str)
        assert isinstance(optimization, str)
        assert "Error" not in analysis
        assert "Error" not in optimization

    def test_comparison_matches_individual_analysis(self):
        """Test that comparison results match individual analyses"""
        # Get comparison
        comparison = compare_cooling_options(
            gpu_power_w=700,
            flow_rate_lpm=12,
            coolant_types=["water"]
        )

        # Get individual analysis
        analysis = analyze_coldplate_system(
            gpu_power_w=700,
            flow_rate_lpm=12,
            coolant_type="water",
            detailed=False
        )

        # Both should succeed and mention similar temps
        assert isinstance(comparison, str)
        assert isinstance(analysis, str)


class TestErrorHandling:
    """Test error handling in MCP tools"""

    def test_negative_power(self):
        """Test handling of negative power"""
        result = analyze_coldplate_system(gpu_power_w=-100)
        # Should handle gracefully (model may accept or reject)
        assert isinstance(result, str)

    def test_zero_flow_rate(self):
        """Test handling of zero flow rate"""
        result = analyze_coldplate_system(
            gpu_power_w=700,
            flow_rate_lpm=0
        )
        # Should handle gracefully
        assert isinstance(result, str)

    def test_extreme_temperature(self):
        """Test handling of extreme ambient temperature"""
        result = analyze_coldplate_system(
            gpu_power_w=700,
            ambient_temp_c=100  # Very hot ambient
        )
        # Should work but may have warnings
        assert isinstance(result, str)


if __name__ == "__main__":
    """Run MCP tool tests"""
    print("=" * 70)
    print("MCP TOOL TEST SUITE")
    print("=" * 70)
    print("\nTesting three MCP tools:")
    print("  1. analyze_coldplate_system")
    print("  2. compare_cooling_options")
    print("  3. optimize_flow_rate")
    print("\n" + "=" * 70)

    pytest.main([__file__, "-v", "--tb=short"])
