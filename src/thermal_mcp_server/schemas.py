"""Typed request/response schemas for thermal analysis tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CoolantName = Literal["water", "glycol50"]


class Geometry(BaseModel):
    """Cold plate geometry and material parameters.

    Assumes rectangular micro-channels. Hydraulic diameter is computed automatically:
    Dh = 2 × width × height / (width + height).
    Defaults represent a typical copper cold plate: 40 × 1 mm square channels,
    80 mm long, 2 mm base, 100 cm² contact area.
    """

    model_config = ConfigDict(extra="forbid")

    channel_count: int = Field(default=40, ge=1, description="Number of parallel coolant channels")
    channel_width_m: float = Field(default=1.0e-3, gt=0, description="Channel width in metres")
    channel_height_m: float = Field(default=1.0e-3, gt=0, description="Channel height in metres (= width for square channels)")
    channel_length_m: float = Field(default=0.08, gt=0, description="Channel flow-path length in metres")
    base_thickness_m: float = Field(default=2.0e-3, gt=0, description="Cold plate base (spreader) thickness in metres")
    contact_area_m2: float = Field(default=0.01, gt=0, description="Chip-to-cold-plate contact area in m² (default 100 cm²)")
    copper_k_w_mk: float = Field(default=385.0, gt=0, description="Base plate thermal conductivity in W/(m·K); default is pure copper")


class AnalyzeColdplateInput(BaseModel):
    """Inputs for single-point cold plate analysis."""

    heat_load_w: float = Field(default=700.0, gt=0)
    flow_rate_lpm: float = Field(default=8.0, gt=0)
    inlet_temp_c: float = Field(default=25.0, ge=-20.0, le=80.0)
    ambient_temp_c: float = Field(default=25.0, ge=-40.0, le=80.0)  # Reserved for future use (facility-level models). Not used in current cold plate analysis.
    coolant: CoolantName = "water"
    r_jc_k_per_w: float = Field(default=0.04, ge=0)
    r_tim_k_per_w: float = Field(default=0.02, ge=0)
    geometry: Geometry = Field(default_factory=Geometry)

    @model_validator(mode="after")
    def ambient_not_hotter_than_inlet(self) -> "AnalyzeColdplateInput":
        if self.ambient_temp_c > self.inlet_temp_c + 20:
            raise ValueError("ambient_temp_c is unrealistically high relative to inlet_temp_c")
        return self


class AnalyzeColdplateOutput(BaseModel):
    """Stable output schema for tool consumers."""

    coolant: CoolantName
    regime: Literal["laminar", "transitional", "turbulent"]
    reynolds: float
    nusselt: float
    heat_transfer_coeff_w_m2k: float
    pressure_drop_pa: float
    pump_power_w: float
    coolant_rise_c: float
    junction_temp_c: float
    resistances_k_per_w: dict[str, float]
    warnings: list[str]


class CompareCoolantsInput(BaseModel):
    heat_load_w: float = Field(default=700.0, gt=0)
    flow_rate_lpm: float = Field(default=8.0, gt=0)
    inlet_temp_c: float = Field(default=25.0, ge=-20.0, le=80.0)
    ambient_temp_c: float = Field(default=25.0, ge=-40.0, le=80.0)  # Reserved for future facility-level models. Not used in current cold plate analysis.
    geometry: Geometry = Field(default_factory=Geometry)
    r_jc_k_per_w: float = Field(default=0.04, ge=0)
    r_tim_k_per_w: float = Field(default=0.02, ge=0)


class OptimizeFlowRateInput(BaseModel):
    heat_load_w: float = Field(default=700.0, gt=0)
    max_junction_temp_c: float = Field(default=85.0, gt=0, lt=200)
    inlet_temp_c: float = Field(default=25.0, ge=-20.0, le=80.0)
    ambient_temp_c: float = Field(default=25.0, ge=-40.0, le=80.0)  # Reserved for future facility-level models. Not used in current cold plate analysis.
    coolant: CoolantName = "water"
    flow_min_lpm: float = Field(default=1.0, gt=0)
    flow_max_lpm: float = Field(default=40.0, gt=0)
    geometry: Geometry = Field(default_factory=Geometry)
    r_jc_k_per_w: float = Field(default=0.04, ge=0)
    r_tim_k_per_w: float = Field(default=0.02, ge=0)

    @model_validator(mode="after")
    def flow_range_valid(self) -> "OptimizeFlowRateInput":
        if self.flow_max_lpm <= self.flow_min_lpm:
            raise ValueError("flow_max_lpm must be greater than flow_min_lpm")
        return self


RackTopology = Literal["series", "parallel"]


class AnalyzeRackInput(BaseModel):
    """Inputs for rack-level thermal analysis across N identical GPU cold plates.

    Series topology: CDU supply flows through each cold plate in sequence.
    Each GPU's inlet = previous GPU's outlet. Total ΔP = N × per-plate ΔP.

    Parallel topology: CDU supply splits equally across all cold plates.
    All GPUs share the same inlet temperature. Total ΔP = per-plate ΔP at
    (total_flow_lpm / gpu_count) per branch.

    Assumptions: identical GPUs, uniform flow distribution, no manifold losses.
    See docs/physics.md Section G for full scope and limitations.
    """

    model_config = ConfigDict(extra="forbid")

    gpu_count: int = Field(default=8, ge=1, le=256, description="Number of GPU cold plates in the rack")
    topology: RackTopology = Field(default="series", description="Plumbing topology: series or parallel")
    heat_load_per_gpu_w: float = Field(default=700.0, gt=0, description="Heat dissipation per GPU in watts")
    total_flow_lpm: float = Field(default=64.0, gt=0, description="Total CDU coolant flow rate in L/min")
    cdu_supply_temp_c: float = Field(default=25.0, ge=-20.0, le=80.0, description="CDU supply (rack inlet) temperature in °C")
    coolant: CoolantName = "water"
    r_jc_k_per_w: float = Field(default=0.04, ge=0, description="Junction-to-case thermal resistance per GPU in K/W")
    r_tim_k_per_w: float = Field(default=0.02, ge=0, description="Thermal interface material resistance per GPU in K/W")
    geometry: Geometry = Field(default_factory=Geometry, description="Cold plate geometry (same for all GPUs)")


class AnalyzeRackOutput(BaseModel):
    """Rack-level thermal and hydraulic analysis results."""

    topology: RackTopology
    gpu_count: int
    total_heat_load_w: float
    max_junction_temp_c: float
    hottest_gpu_index: int  # 0-indexed; in series this is always gpu_count - 1
    cdu_outlet_temp_c: float
    total_pressure_drop_pa: float
    total_pump_power_w: float
    per_gpu_junction_temps_c: list[float]
    warnings: list[str]
