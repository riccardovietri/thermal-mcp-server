"""Typed request/response schemas for thermal analysis tools."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CoolantName = Literal["water", "glycol50"]
FlowRegime = Literal["laminar", "transitional", "turbulent"]


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
    """Finite-difference sensitivity coefficients and illustrative perturbations.

    All derivatives are computed by perturbing each parameter by a small amount
    while holding everything else constant. See docs/physics.md Section H for
    derivation and interpretation.

    Useful for understanding which parameters most affect the modeled Tj:
    - R_jc is perturbed by an illustrative ±20%.
    - R_tim is doubled as an illustrative scenario.
    These are not measured tolerances or service-life predictions.
    """

    dtj_dq_c_per_w: float = Field(description="∂Tj/∂Q_heat [°C/W] — junction temp rise per additional watt of chip heat")
    dtj_dr_tim_c_per_kw: float = Field(description="∂Tj/∂R_tim [°C per K/W] — junction temp rise per unit TIM resistance increase")
    dtj_dt_inlet_dimensionless: float = Field(description="∂Tj/∂T_inlet [°C/°C] — should be ~1.0; confirms inlet shifts Tj 1-for-1")
    r_jc_uncertainty_pm_c: float = Field(description="±°C Tj change for an illustrative ±20% R_jc perturbation")
    r_tim_aged_delta_c: float = Field(description="Tj rise [°C] if R_tim doubles; an illustrative scenario, not a lifetime model")


class AnalyzeColdplateOutput(BaseModel):
    """Stable output schema for tool consumers."""

    coolant: CoolantName
    regime: FlowRegime
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
            "as the effective ceiling. Select the guardband from component and operating evidence; "
            "no universal margin is inferred."
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


class StressScenarioInputs(BaseModel):
    """Magnitudes for five separately evaluated illustrative stress cases."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    r_jc_variation_fraction: float = Field(default=0.20, ge=0.0, le=1.0, description="Positive relative package-resistance variation")
    r_tim_multiplier: float = Field(default=2.0, ge=0.0, description="TIM resistance multiplier")
    heat_load_delta_w: float = Field(default=10.0, description="Signed heat-load change in watts")
    supply_temp_delta_c: float = Field(default=1.0, description="Signed supply-temperature change in °C")


class DecisionScenario(BaseModel):
    """Input for a first-pass cooling decision report.

    Describes a single GPU or rack scenario to be analyzed and synthesized into
    a thermal screening report. Defaults are illustrative scenario inputs, not
    vendor-verified component properties.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

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
        description=("Caller-supplied guardband in °C; the thermal criterion is target_junction_temp_c minus margin_c."),
    )
    coolant: CoolantName = "water"
    inlet_temp_c: float = Field(default=25.0, ge=-20.0, le=80.0, description="Coolant supply temperature in °C")
    flow_rate_lpm: float | None = Field(
        default=None,
        gt=0,
        description="Fixed flow in L/min per GPU, or None for thermal search (series uses a single-plate candidate only).",
    )
    geometry: Geometry | None = Field(
        default=None,
        description="Cold plate geometry overrides. If None, uses standard defaults.",
    )
    r_jc_k_per_w: float = Field(default=0.04, ge=0, description="Junction-to-case thermal resistance in K/W")
    r_tim_k_per_w: float = Field(default=0.02, ge=0, description="TIM resistance in K/W")
    input_source_notes: dict[str, str] = Field(
        default_factory=dict,
        description="Optional caller-provided source notes keyed by scenario or leaf input path",
    )
    stress_scenarios: StressScenarioInputs = Field(
        default_factory=StressScenarioInputs,
        description="Caller-configurable magnitudes for the independent stress cases",
    )

    @model_validator(mode="after")
    def margin_less_than_target(self) -> "DecisionScenario":
        if self.margin_c >= self.target_junction_temp_c:
            raise ValueError("margin_c must be less than target_junction_temp_c")
        return self


class DecisionStatus(str, Enum):
    """Scope-aware result state for a decision report."""

    MEETS_TARGET = "meets_target"
    FAILS_AT_EVALUATED_FLOW = "fails_at_evaluated_flow"
    NO_FEASIBLE_FLOW_IN_SEARCH_RANGE = "no_feasible_flow_in_search_range"
    UNDETERMINED = "undetermined"


class EvaluationMode(str, Enum):
    FIXED_FLOW = "fixed_flow"
    THERMAL_SEARCH = "thermal_search"


FlowSearchScope = Literal[
    "single_plate",
    "parallel_rack",
    "single_plate_candidate_for_series",
]
EvaluatedPointRole = Literal[
    "fixed_input",
    "thermal_search_result",
    "series_candidate",
    "search_bound_diagnostic",
]


class FlowSearch(BaseModel):
    """Thermal search scope and result, when an optimization was attempted."""

    model_config = ConfigDict(allow_inf_nan=False)

    scope: FlowSearchScope
    min_lpm_per_gpu: float = Field(gt=0)
    max_lpm_per_gpu: float = Field(gt=0)
    minimum_feasible_lpm_per_gpu: float | None = Field(default=None, gt=0)
    lower_bound_limited: bool = False

    @model_validator(mode="after")
    def bounds_are_ordered(self) -> "FlowSearch":
        if self.max_lpm_per_gpu <= self.min_lpm_per_gpu:
            raise ValueError("max_lpm_per_gpu must exceed min_lpm_per_gpu")
        if self.minimum_feasible_lpm_per_gpu is not None and not (self.min_lpm_per_gpu <= self.minimum_feasible_lpm_per_gpu <= self.max_lpm_per_gpu):
            raise ValueError("minimum_feasible_lpm_per_gpu must lie within the search interval")
        return self


class EvaluatedPoint(BaseModel):
    """One explicitly evaluated operating point, selected or diagnostic."""

    model_config = ConfigDict(allow_inf_nan=False)

    role: EvaluatedPointRole
    flow_lpm_per_gpu: float = Field(gt=0)
    supply_temp_c: float
    junction_temp_c: float
    margin_to_limit_c: float
    margin_to_criterion_c: float
    meets_thermal_target: bool
    pressure_drop_pa: float | None = Field(default=None, ge=0, description="Cold-plate-only pressure drop; excludes system losses")
    pump_power_w: float | None = Field(default=None, ge=0)
    cdu_outlet_temp_c: float | None = None


class StressScenarioResult(BaseModel):
    """Result for one stress scenario, or an explicit unavailable state."""

    model_config = ConfigDict(allow_inf_nan=False)

    name: str
    status: Literal["evaluated", "unavailable"]
    changed_parameter: str | None = None
    base_value: float | None = None
    perturbed_value: float | None = None
    units: str | None = None
    signed_junction_delta_c: float | None = None
    flow_lpm_per_gpu: float | None = None
    junction_temp_c: float | None = None
    margin_to_limit_c: float | None = None
    margin_to_criterion_c: float | None = None
    reason: str | None = None


class ModelMetadata(BaseModel):
    """Model identity and validity disclosures carried with every report."""

    package_version: str
    model_name: str = "steady_state_1d_coldplate"
    validation_state: Literal["unvalidated"] = "unvalidated"
    coolant_property_reference_temp_c: float = 25.0
    applicability_notices: list[str]


class DecisionReport(BaseModel):
    """Version 2 structured cooling decision report.

    The report distinguishes evaluated points from recommendations and uses
    explicit unknown states. It does not assess system hydraulic feasibility or
    overall engineering risk without head/loss constraints and validation data.
    """

    model_config = ConfigDict(allow_inf_nan=False)

    report_schema_version: Literal[2] = 2
    scenario_label: str
    status: DecisionStatus
    evaluation_mode: EvaluationMode
    attempted_flow_lpm_per_gpu: float | None = Field(default=None, gt=0)
    evaluated_point: EvaluatedPoint | None = None
    flow_search: FlowSearch | None = None
    system_hydraulic_feasibility: Literal["not_assessed"] = "not_assessed"
    risk_assessment: Literal["not_assessed"] = "not_assessed"
    topology_assessment: str
    stress_scenarios: list[StressScenarioResult]
    resolved_scenario: dict[str, Any]
    input_provenance: dict[str, dict[str, str | None]]
    model: ModelMetadata
    warnings: list[str]
    blind_spots: list[str] = Field(description="Model limitations always reported to the caller")
    rendered_memo: str = Field(description="Markdown-formatted engineering memo")
