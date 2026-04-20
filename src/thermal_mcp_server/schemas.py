"""Typed request/response schemas for thermal analysis tools."""

from __future__ import annotations

from enum import Enum
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


class SensitivityOutput(BaseModel):
    """Finite-difference sensitivity coefficients and engineering uncertainty bounds.

    All derivatives are computed by perturbing each parameter by a small amount
    while holding everything else constant. See docs/physics.md Section H for
    derivation and interpretation.

    Useful for understanding which parameters dominate Tj uncertainty:
    - R_jc has ±20% manufacturing variation (NVIDIA does not publish tolerances).
    - R_tim typically doubles over 2–3 years of pump-out degradation.
    - TDP creep (heat_load_w) of 5–10% is common over GPU product lifetime.
    """

    dtj_dq_c_per_w: float = Field(
        description="∂Tj/∂Q_heat [°C/W] — junction temp rise per additional watt of chip heat"
    )
    dtj_dr_tim_c_per_kw: float = Field(
        description="∂Tj/∂R_tim [°C per K/W] — junction temp rise per unit TIM resistance increase"
    )
    dtj_dt_inlet_dimensionless: float = Field(
        description="∂Tj/∂T_inlet [°C/°C] — should be ~1.0; confirms inlet shifts Tj 1-for-1"
    )
    r_jc_uncertainty_pm_c: float = Field(
        description="±°C Tj spread from ±20% R_jc manufacturing variation"
    )
    r_tim_aged_delta_c: float = Field(
        description="Tj rise [°C] if R_tim doubles — models TIM pump-out degradation after 2–3 years"
    )


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
    sensitivity: SensitivityOutput | None = None


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
    margin_c: float = Field(
        default=0.0,
        ge=0.0,
        description=(
            "Safety margin [°C]. The optimizer targets (max_junction_temp_c − margin_c) "
            "as the effective ceiling. Use ≥5°C to account for R_jc manufacturing variation "
            "and TIM degradation."
        ),
    )
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
        if self.margin_c >= self.max_junction_temp_c:
            raise ValueError("margin_c must be less than max_junction_temp_c")
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
    ambient_temp_c: float | None = Field(
        default=None,
        ge=-40.0,
        le=80.0,
        description="Optional ambient reference temperature in °C. If omitted, defaults to cdu_supply_temp_c during rack analysis.",
    )
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


# ---------------------------------------------------------------------------
# Decision report schemas
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FlowBand(BaseModel):
    """Recommended coolant flow operating band for a given scenario."""

    min_lpm: float = Field(description="Minimum flow that meets the thermal target with margin")
    recommended_lpm: float = Field(description="Recommended operating point (15% above minimum)")
    max_lpm: float = Field(description="Upper bound used in search (50% above minimum)")
    basis: str = Field(description="Human-readable explanation of how the band was derived")


class DecisionScenario(BaseModel):
    """Input for a first-pass cooling decision report.

    Describes a single GPU or rack scenario to be analyzed and synthesized into
    an engineering recommendation memo. Physics parameters default to H100 SXM
    reference values; override as needed.
    """

    model_config = ConfigDict(extra="forbid")

    chip_label: str = Field(
        default="GPU",
        description="Display label for the chip/scenario (e.g. 'H100 SXM'). Not validated against any database.",
    )
    heat_load_w: float = Field(default=700.0, gt=0, description="Chip thermal design power in watts")
    gpu_count: int = Field(default=1, ge=1, le=256, description="Number of GPUs in the rack (1 = single cold plate)")
    topology: RackTopology = Field(
        default="parallel",
        description="Rack plumbing topology (only used when gpu_count > 1)",
    )
    target_junction_temp_c: float = Field(
        default=83.0,
        gt=0,
        lt=200,
        description="Maximum allowable junction temperature in °C",
    )
    margin_c: float = Field(
        default=5.0,
        ge=0.0,
        description=(
            "Safety margin in °C. Optimizer targets (target_junction_temp_c - margin_c). "
            "Recommended ≥5°C to cover R_jc manufacturing variation and TIM aging."
        ),
    )
    coolant: CoolantName = "water"
    inlet_temp_c: float = Field(default=25.0, ge=-20.0, le=80.0, description="Coolant supply temperature in °C")
    flow_rate_lpm: float | None = Field(
        default=None,
        gt=0,
        description="Coolant flow rate per GPU in L/min. If None, auto-optimized to meet target.",
    )
    geometry: Geometry | None = Field(
        default=None,
        description="Cold plate geometry overrides. If None, uses standard defaults.",
    )
    r_jc_k_per_w: float = Field(default=0.04, ge=0, description="Junction-to-case thermal resistance in K/W")
    r_tim_k_per_w: float = Field(default=0.02, ge=0, description="TIM resistance in K/W")

    @model_validator(mode="after")
    def margin_less_than_target(self) -> "DecisionScenario":
        if self.margin_c >= self.target_junction_temp_c:
            raise ValueError("margin_c must be less than target_junction_temp_c")
        return self


class DecisionReport(BaseModel):
    """Structured first-pass cooling decision memo.

    Synthesizes single-point analysis, flow optimization, rack modeling, and
    sensitivity outputs into an actionable engineering recommendation. The
    rendered_memo field always contains a human-readable markdown summary.

    Model blind spots are always populated from documented limitations — never
    suppressed. See docs/physics.md for full scope.
    """

    scenario_label: str
    feasible: bool = Field(description="True if target Tj can be met within the search flow range")
    risk_level: RiskLevel = Field(
        description="LOW: >10°C margin remaining; MEDIUM: 5–10°C; HIGH: <5°C or infeasible"
    )
    recommended_flow: FlowBand
    recommended_supply_temp_c: float
    junction_temp_at_recommended_c: float
    margin_remaining_c: float = Field(
        description="Headroom to the actual hard limit: target_junction_temp_c - Tj_at_recommended_flow"
    )
    topology_recommendation: str = Field(description="Topology rationale (populated when gpu_count > 1)")
    uncertainty_section: dict[str, float] = Field(
        description="Uncertainty contributors in °C, keyed by source"
    )
    warnings: list[str]
    blind_spots: list[str] = Field(description="Model limitations always reported to the caller")
    rendered_memo: str = Field(description="Markdown-formatted engineering memo")
