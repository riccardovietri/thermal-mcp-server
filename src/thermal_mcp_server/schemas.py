"""Typed request/response schemas for thermal analysis tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


CoolantName = Literal["water", "glycol50"]


class Geometry(BaseModel):
    """Cold plate geometry and material parameters."""

    channel_count: int = Field(default=40, ge=1)
    hydraulic_diameter_m: float = Field(default=1.0e-3, gt=0)
    channel_length_m: float = Field(default=0.08, gt=0)
    channel_width_m: float = Field(default=1.0e-3, gt=0)
    base_thickness_m: float = Field(default=2.0e-3, gt=0)
    contact_area_m2: float = Field(default=0.01, gt=0)
    copper_k_w_mk: float = Field(default=385.0, gt=0)


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
    ambient_temp_c: float = Field(default=25.0, ge=-40.0, le=80.0)
    geometry: Geometry = Field(default_factory=Geometry)
    r_jc_k_per_w: float = Field(default=0.04, ge=0)
    r_tim_k_per_w: float = Field(default=0.02, ge=0)


class OptimizeFlowRateInput(BaseModel):
    heat_load_w: float = Field(default=700.0, gt=0)
    max_junction_temp_c: float = Field(default=85.0, gt=0, lt=200)
    inlet_temp_c: float = Field(default=25.0, ge=-20.0, le=80.0)
    ambient_temp_c: float = Field(default=25.0, ge=-40.0, le=80.0)
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
