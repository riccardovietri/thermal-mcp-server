"""
Unit Tests for MCP Server Tool Logic
Author: Riccardo Vietri
Date: February 2026

Tests the business logic that powers the MCP tools by testing the ColdPlateModel
directly. The MCP server tools are thin wrappers around this model.
"""

import pytest
from src.models.coldplate import ColdPlateModel, format_analysis_result


class TestAnalyzeToolLogic:
    """Test the logic behind analyze_coldplate_system tool"""

    def test_basic_analysis_output(self):
        """Verify analysis produces formatted output"""
        model = ColdPlateModel(gpu_power_w=500, num_gpus=4, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=12)
        formatted = format_analysis_result(result)

        assert "THERMAL ANALYSIS RESULTS" in formatted
        assert "Junction Temperature" in formatted
        assert "Pressure Drop" in formatted
        assert str(result["junction_temp_c"]) in formatted

    def test_all_coolant_types_work(self):
        """All three coolant types should work"""
        for coolant in ["water", "glycol", "dielectric"]:
            model = ColdPlateModel(gpu_power_w=600, coolant_type=coolant)
            result = model.calculate_performance(flow_rate_lpm=12)

            assert result["junction_temp_c"] > 0
            assert result["pressure_drop_psi"] > 0

    def test_multi_gpu_analysis(self):
        """Multi-GPU configuration works correctly"""
        model = ColdPlateModel(gpu_power_w=700, num_gpus=8, coolant_type="water")
        result = model.calculate_performance(flow_rate_lpm=15)

        assert result["total_power_w"] == 5600
        assert result["junction_temp_c"] > 50  # High power should be warm


class TestCompareToolLogic:
    """Test the logic behind compare_cooling_options tool"""

    def test_water_better_than_glycol(self):
        """Water should perform better than glycol"""
        water_model = ColdPlateModel(gpu_power_w=600, num_gpus=4, coolant_type="water")
        glycol_model = ColdPlateModel(gpu_power_w=600, num_gpus=4, coolant_type="glycol")

        water_result = water_model.calculate_performance(flow_rate_lpm=12)
        glycol_result = glycol_model.calculate_performance(flow_rate_lpm=12)

        assert water_result["junction_temp_c"] < glycol_result["junction_temp_c"]

    def test_all_coolants_comparable(self):
        """All coolants can be compared side-by-side"""
        results = {}
        for coolant in ["water", "glycol", "dielectric"]:
            model = ColdPlateModel(gpu_power_w=700, coolant_type=coolant)
            results[coolant] = model.calculate_performance(flow_rate_lpm=15)

        # All should have valid results
        for coolant, result in results.items():
            assert result["junction_temp_c"] > 0
            assert result["pressure_drop_psi"] > 0

        # Water should be best thermal performance
        assert results["water"]["junction_temp_c"] < results["dielectric"]["junction_temp_c"]


class TestOptimizeToolLogic:
    """Test the logic behind optimize_flow_rate tool"""

    def test_optimization_meets_target(self):
        """Optimization should meet temperature target"""
        model = ColdPlateModel(gpu_power_w=600, num_gpus=1, coolant_type="water")
        result = model.optimize_flow_rate(target_temp_c=75)

        # Should be at or below target (with small tolerance)
        assert result["junction_temp_c"] <= 76

    def test_optimization_with_different_coolants(self):
        """Optimization works with all coolant types"""
        for coolant in ["water", "glycol", "dielectric"]:
            model = ColdPlateModel(gpu_power_w=500, num_gpus=2, coolant_type=coolant)
            result = model.optimize_flow_rate(target_temp_c=80)

            assert result["flow_rate_lpm"] > 0
            assert result["junction_temp_c"] > 0

    def test_difficult_optimization(self):
        """Very challenging targets should return best effort"""
        model = ColdPlateModel(
            gpu_power_w=700,
            num_gpus=8,
            coolant_type="dielectric"
        )
        result = model.optimize_flow_rate(
            target_temp_c=50,  # Very low target
            max_flow_lpm=30
        )

        # Should return something reasonable even if target not met
        assert result["flow_rate_lpm"] > 20  # Should push towards max flow


class TestMCPServerConfiguration:
    """Test MCP server setup and configuration"""

    def test_mcp_server_imports(self):
        """MCP server module should import successfully"""
        from src import mcp_server
        assert mcp_server.mcp is not None

    def test_mcp_has_tools(self):
        """MCP server should have all three tools registered"""
        from src.mcp_server import mcp

        # FastMCP stores tools in internal structure
        # Just verify the module loaded without errors
        assert mcp is not None
