"""Typed request/response schemas for thermal analysis tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


CoolantName = Literal["water", "glycol50"]


class Geometry(BaseModel):
    """Cold plate geometry and material parameters.

    Assumes square micro-channels (channel_width_m == hydraulic_diameter_m).
    Defaults represent a typical copper cold plate: 40 × 1 mm square channels,
    80 mm long, 2 mm base, 100 cm² contact area.
    """

    channel_count: int = Field(default=40, ge=1, description="Number of parallel coolant channels")
    hydraulic_diameter_m: float = Field(default=1.0e-3, gt=0, description="Channel hydraulic diameter in metres (= side length for square channels)")
    channel_length_m: float = Field(default=0.08, gt=0, description="Channel flow-path length in metres")
    channel_width_m: float = Field(default=1.0e-3, gt=0, description="Channel width in metres; must equal hydraulic_diameter_m for the square-channel assumption to hold")
    base_thickness_m: float = Field(default=2.0e-3, gt=0, description="Cold plate base (spreader) thickness in metres")
    contact_area_m2: float = Field(default=0.01, gt=0, description="Chip-to-cold-plate contact area in m² (default 100 cm²)")
    copper_k_w_mk: float = Field(default=385.0, gt=0, description="Base plate thermal conductivity in W/(m·K); default is pure copper")

    @model_validator(mode="after")
    def square_channel_assumption(self) -> "Geometry":
        """Enforce square-channel constraint: width must equal hydraulic diameter.

        The physics engine uses area = count × width × Dh and
        wetted perimeter = count × 4 × width × length, both of which are only
        correct when width == Dh (square cross-section). Passing mismatched values
        produces silently wrong Tj and ΔP results.
        """
        ratio = abs(self.channel_width_m - self.hydraulic_diameter_m) / self.hydraulic_diameter_m
        if ratio > 0.01:
            raise ValueError(
                f"channel_width_m ({self.channel_width_m*1e3:.3f} mm) must equal "
                f"hydraulic_diameter_m ({self.hydraulic_diameter_m*1e3:.3f} mm). "
                "The physics model assumes square channels. For rectangular channels "
                "set both to the hydraulic diameter of your geometry: "
                "Dh = 2*w*h / (w+h)."
            )
        return self


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
