"""Steady-state thermal resistance model for liquid-cooled cold plate analysis.

Implements a 1D resistance network (R_jc -> R_tim -> R_base -> R_conv) with
Dittus-Boelter convection and Darcy-Weisbach pressure drop. All assumptions
are documented inline. See docs/physics.md for full derivation and scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

from .schemas import AnalyzeColdplateInput, AnalyzeColdplateOutput, OptimizeFlowRateInput


@dataclass(frozen=True)
class CoolantProperties:
    density_kg_m3: float
    cp_j_kgk: float
    k_w_mk: float
    mu_pa_s: float


COOLANTS: dict[str, CoolantProperties] = {
    "water": CoolantProperties(997.0, 4180.0, 0.60, 0.00089),
    # Ethylene glycol 50% by volume, nominal 25°C properties.
    # For propylene glycol (lower toxicity), viscosity is ~60-80% higher at 25°C.
    "glycol50": CoolantProperties(1060.0, 3400.0, 0.40, 0.00480),
}


def _flow_quantities(inp: AnalyzeColdplateInput) -> tuple[float, float, float, float]:
    geom = inp.geometry
    props = COOLANTS[inp.coolant]
    flow_m3s = inp.flow_rate_lpm / 1000.0 / 60.0
    # ASSUMPTION: square channel cross-section (side = channel_width). For rectangular channels, replace with width × height.
    area_total = geom.channel_count * geom.channel_width_m * geom.hydraulic_diameter_m
    velocity = flow_m3s / area_total
    re = props.density_kg_m3 * velocity * geom.hydraulic_diameter_m / props.mu_pa_s
    pr = props.cp_j_kgk * props.mu_pa_s / props.k_w_mk
    return flow_m3s, velocity, re, pr


def _nusselt(re: float, pr: float) -> tuple[float, str]:
    if re < 2300:
        return 4.36, "laminar"
    if re > 4000:
        return 0.023 * re**0.8 * pr**0.4, "turbulent"
    nu_lam = 4.36
    nu_turb = 0.023 * 4000**0.8 * pr**0.4
    blend = (re - 2300) / (4000 - 2300)
    return nu_lam * (1 - blend) + nu_turb * blend, "transitional"


def _friction_factor(re: float) -> float:
    if re < 2300:
        return 64.0 / max(re, 1e-6)
    if re > 4000:
        return 0.3164 * re ** (-0.25)
    # Transition regime: linear blend matching Nusselt treatment (Re 2300–4000)
    f_lam = 64.0 / 2300.0
    f_turb = 0.3164 * 4000 ** (-0.25)
    blend = (re - 2300) / (4000 - 2300)
    return f_lam * (1 - blend) + f_turb * blend


def analyze(inp: AnalyzeColdplateInput) -> AnalyzeColdplateOutput:
    props = COOLANTS[inp.coolant]
    geom = inp.geometry
    flow_m3s, velocity, re, pr = _flow_quantities(inp)

    nu, regime = _nusselt(re, pr)
    h = nu * props.k_w_mk / geom.hydraulic_diameter_m

    # Square channel: wetted perimeter = 4 * side = 4 * Dh (since Dh = side for a square channel).
    # Consistent with cross-section assumption above (area = channel_width * Dh = side^2).
    wetted_area = geom.channel_count * 4 * geom.channel_width_m * geom.channel_length_m
    r_conv = 1.0 / (h * wetted_area)
    r_base = geom.base_thickness_m / (geom.copper_k_w_mk * geom.contact_area_m2)
    r_total = inp.r_jc_k_per_w + inp.r_tim_k_per_w + r_base + r_conv

    m_dot = flow_m3s * props.density_kg_m3
    coolant_rise = inp.heat_load_w / (m_dot * props.cp_j_kgk)
    t_bulk = inp.inlet_temp_c + 0.5 * coolant_rise
    t_j = t_bulk + inp.heat_load_w * r_total

    f = _friction_factor(re)
    dp = f * (geom.channel_length_m / geom.hydraulic_diameter_m) * (props.density_kg_m3 * velocity**2 / 2)
    # ASSUMPTION: 50% pump efficiency (typical centrifugal pump at partial load). Adjust for specific pump curve.
    pump_power = dp * flow_m3s / 0.5

    warnings: list[str] = []
    # H100 SXM throttle onset is 83°C per NVIDIA thermal guidelines; 85°C used as conservative design ceiling
    if t_j > 85:
        warnings.append("junction temperature exceeds 85C")
    if re < 500:
        warnings.append("very low Reynolds number; risk of poor flow distribution")

    return AnalyzeColdplateOutput(
        coolant=inp.coolant,
        regime=regime,
        reynolds=re,
        nusselt=nu,
        heat_transfer_coeff_w_m2k=h,
        pressure_drop_pa=dp,
        pump_power_w=pump_power,
        coolant_rise_c=coolant_rise,
        junction_temp_c=t_j,
        resistances_k_per_w={
            "junction_to_case": inp.r_jc_k_per_w,
            "tim": inp.r_tim_k_per_w,
            "base_conduction": r_base,
            "convection": r_conv,
            "total": r_total,
        },
        warnings=warnings,
    )


def optimize_flow(inp: OptimizeFlowRateInput, max_iter: int = 40) -> tuple[float, AnalyzeColdplateOutput | None]:
    """Binary search for minimum flow rate meeting the junction temperature target.

    Returns (minimum_flow_lpm, analysis_at_minimum_flow). If no flow rate in
    [flow_min_lpm, flow_max_lpm] meets the target, returns (flow_max_lpm, None).
    """
    lo, hi = inp.flow_min_lpm, inp.flow_max_lpm
    best: AnalyzeColdplateOutput | None = None
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        result = analyze(
            AnalyzeColdplateInput(
                heat_load_w=inp.heat_load_w,
                flow_rate_lpm=mid,
                inlet_temp_c=inp.inlet_temp_c,
                ambient_temp_c=inp.ambient_temp_c,
                coolant=inp.coolant,
                r_jc_k_per_w=inp.r_jc_k_per_w,
                r_tim_k_per_w=inp.r_tim_k_per_w,
                geometry=inp.geometry,
            )
        )
        if result.junction_temp_c <= inp.max_junction_temp_c:
            hi = mid
            best = result
        else:
            lo = mid
    return hi, best
