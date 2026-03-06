"""Steady-state thermal resistance model for liquid-cooled cold plate analysis.

Implements a 1D resistance network (R_jc -> R_tim -> R_base -> R_conv) with
Dittus-Boelter convection and Darcy-Weisbach pressure drop. All assumptions
are documented inline. See docs/physics.md for full derivation and scope.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import (
    AnalyzeColdplateInput,
    AnalyzeColdplateOutput,
    AnalyzeRackInput,
    AnalyzeRackOutput,
    OptimizeFlowRateInput,
)


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


def _flow_quantities(inp: AnalyzeColdplateInput) -> tuple[float, float, float, float, float]:
    geom = inp.geometry
    props = COOLANTS[inp.coolant]
    flow_m3s = inp.flow_rate_lpm / 1000.0 / 60.0
    w, h = geom.channel_width_m, geom.channel_height_m
    # Rectangular cross-section; Dh = 4A/P = 2wh/(w+h)
    dh = 2 * w * h / (w + h)
    area_total = geom.channel_count * w * h
    velocity = flow_m3s / area_total
    re = props.density_kg_m3 * velocity * dh / props.mu_pa_s
    pr = props.cp_j_kgk * props.mu_pa_s / props.k_w_mk
    return flow_m3s, velocity, re, pr, dh


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
    flow_m3s, velocity, re, pr, dh = _flow_quantities(inp)

    nu, regime = _nusselt(re, pr)
    h = nu * props.k_w_mk / dh

    # Rectangular channel: wetted perimeter = 2 * (width + height) per channel.
    wetted_area = geom.channel_count * 2 * (geom.channel_width_m + geom.channel_height_m) * geom.channel_length_m
    r_conv = 1.0 / (h * wetted_area)
    r_base = geom.base_thickness_m / (geom.copper_k_w_mk * geom.contact_area_m2)
    r_total = inp.r_jc_k_per_w + inp.r_tim_k_per_w + r_base + r_conv

    m_dot = flow_m3s * props.density_kg_m3
    coolant_rise = inp.heat_load_w / (m_dot * props.cp_j_kgk)
    t_bulk = inp.inlet_temp_c + 0.5 * coolant_rise
    t_j = t_bulk + inp.heat_load_w * r_total

    f = _friction_factor(re)
    dp = f * (geom.channel_length_m / dh) * (props.density_kg_m3 * velocity**2 / 2)
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


def analyze_rack(inp: AnalyzeRackInput) -> AnalyzeRackOutput:
    """Rack-level thermal analysis for N identical GPU cold plates.

    Series topology: CDU supply flows through each cold plate in sequence.
    Each GPU's inlet = previous GPU's outlet. Total ΔP = N × per-plate ΔP.
    With constant fluid properties, Tj increases by exactly one coolant_rise
    per GPU, so the last GPU is always the hottest.

    Parallel topology: CDU supply splits equally across all cold plates.
    All GPUs share the same inlet temperature. Total ΔP = per-plate ΔP at
    flow_per_gpu = total_flow_lpm / gpu_count. CDU outlet temperature is
    computed from an energy balance over the full rack.

    Assumptions (documented in docs/physics.md Section G):
    - Identical GPUs: same TDP, cold plate geometry, and thermal resistances.
    - Uniform flow distribution: no maldistribution between parallel branches.
    - No manifold or header pressure losses: cold plate ΔP only.
    """
    props = COOLANTS[inp.coolant]
    flow_m3s = inp.total_flow_lpm / 1000.0 / 60.0
    per_gpu_warnings: list[str] = []

    if inp.topology == "series":
        flow_per_gpu_lpm = inp.total_flow_lpm
        tj_list: list[float] = []
        current_inlet = inp.cdu_supply_temp_c
        dp_single: float = 0.0

        for i in range(inp.gpu_count):
            gpu_inp = AnalyzeColdplateInput(
                heat_load_w=inp.heat_load_per_gpu_w,
                flow_rate_lpm=flow_per_gpu_lpm,
                inlet_temp_c=current_inlet,
                coolant=inp.coolant,
                r_jc_k_per_w=inp.r_jc_k_per_w,
                r_tim_k_per_w=inp.r_tim_k_per_w,
                geometry=inp.geometry,
            )
            result = analyze(gpu_inp)
            tj_list.append(result.junction_temp_c)
            if i == 0:
                # ΔP identical for all GPUs in series: same flow, same geometry,
                # constant fluid properties (no temperature dependence).
                dp_single = result.pressure_drop_pa
            current_inlet += result.coolant_rise_c
            for w in result.warnings:
                per_gpu_warnings.append(f"GPU {i}: {w}")

        # Total system ΔP: cold plates in series add ΔP directly.
        total_dp = dp_single * inp.gpu_count
        cdu_outlet_temp = current_inlet  # temperature after exiting last GPU

    else:  # parallel
        flow_per_gpu_lpm = inp.total_flow_lpm / inp.gpu_count
        gpu_inp = AnalyzeColdplateInput(
            heat_load_w=inp.heat_load_per_gpu_w,
            flow_rate_lpm=flow_per_gpu_lpm,
            inlet_temp_c=inp.cdu_supply_temp_c,
            coolant=inp.coolant,
            r_jc_k_per_w=inp.r_jc_k_per_w,
            r_tim_k_per_w=inp.r_tim_k_per_w,
            geometry=inp.geometry,
        )
        result = analyze(gpu_inp)
        tj_list = [result.junction_temp_c] * inp.gpu_count

        # Parallel branches: system ΔP equals branch ΔP (not cumulative).
        total_dp = result.pressure_drop_pa

        # CDU outlet from energy balance: Q_total = m_dot_total × cp × ΔT_cdu
        m_dot_total = flow_m3s * props.density_kg_m3
        total_q = inp.heat_load_per_gpu_w * inp.gpu_count
        cdu_outlet_temp = inp.cdu_supply_temp_c + total_q / (m_dot_total * props.cp_j_kgk)

        # All GPUs are identical in parallel; report unique warnings once.
        for w in result.warnings:
            per_gpu_warnings.append(f"all GPUs: {w}")

    # ASSUMPTION: 50% pump efficiency (same assumption as single cold plate model).
    total_pump_power = total_dp * flow_m3s / 0.5

    max_tj = max(tj_list)
    hottest_idx = tj_list.index(max_tj)

    warnings: list[str] = []
    if max_tj > 85:
        warnings.append(
            f"GPU {hottest_idx} (0-indexed) junction temperature {max_tj:.1f}°C exceeds 85°C design ceiling"
        )
    warnings.extend(per_gpu_warnings)

    return AnalyzeRackOutput(
        topology=inp.topology,
        gpu_count=inp.gpu_count,
        total_heat_load_w=inp.heat_load_per_gpu_w * inp.gpu_count,
        max_junction_temp_c=max_tj,
        hottest_gpu_index=hottest_idx,
        cdu_outlet_temp_c=cdu_outlet_temp,
        total_pressure_drop_pa=total_dp,
        total_pump_power_w=total_pump_power,
        per_gpu_junction_temps_c=tj_list,
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
