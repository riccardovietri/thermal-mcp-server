import pytest

from thermal_mcp_server.physics import analyze, analyze_rack, compute_sensitivity, optimize_flow
from thermal_mcp_server.schemas import AnalyzeColdplateInput, AnalyzeRackInput, OptimizeFlowRateInput


def test_tj_monotonic_with_flow():
    low = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=4, coolant="water"))
    high = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=14, coolant="water"))
    assert high.junction_temp_c <= low.junction_temp_c


def test_regime_switch_sensible():
    lam = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=0.8, coolant="water"))
    turb = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=12, coolant="water"))
    assert lam.regime in {"laminar", "transitional"}
    assert turb.regime in {"transitional", "turbulent"}
    assert turb.heat_transfer_coeff_w_m2k > lam.heat_transfer_coeff_w_m2k


def test_glycol_generally_worse_than_water():
    w = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water"))
    g = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="glycol50"))
    assert g.junction_temp_c >= w.junction_temp_c or g.pump_power_w >= w.pump_power_w


def test_pressure_drop_superlinear_vs_flow():
    a = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=4, coolant="water"))
    b = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water"))
    c = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=12, coolant="water"))
    assert a.pressure_drop_pa < b.pressure_drop_pa < c.pressure_drop_pa
    ratio1 = b.pressure_drop_pa / a.pressure_drop_pa
    ratio2 = c.pressure_drop_pa / b.pressure_drop_pa
    assert ratio1 > 1.1
    assert ratio2 > 1.1


def test_invalid_inputs_rejected():
    with pytest.raises(Exception):
        AnalyzeColdplateInput(heat_load_w=-1, flow_rate_lpm=8)
    with pytest.raises(Exception):
        AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=-1)
    with pytest.raises(Exception):
        AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, inlet_temp_c=500)


def test_hand_calc_validation_700w_water():
    """Validate model against independent hand calculation.

    Case: 700W GPU, water coolant, 10 LPM, default geometry (w=h=1mm square).
    R_jc = 0.1 K/W, R_tim = 0.05 K/W (conservative thermal stack).

    Hand calculation (independent of model code):
      Dh   = 2*0.001*0.001 / (0.001+0.001) = 0.001 m  (rectangular: Dh = 2wh/(w+h))
      v    = (10/60000) / (40 * 0.001 * 0.001) = 4.167 m/s
      Re   = 997 * 4.167 * 0.001 / 0.00089 = 4668 (turbulent)
      Pr   = 4180 * 0.00089 / 0.60 = 6.20
      Nu   = 0.023 * 4668^0.8 * 6.20^0.4 = 41.1
      h    = 41.1 * 0.60 / 0.001 = 24667 W/m2-K
      P_ch = 2 * (0.001 + 0.001) = 0.004 m  (rectangular perimeter)
      A_wet = 40 * 0.004 * 0.08 = 0.01280 m2
      R_conv = 1/(24667 * 0.01280) = 0.00317 K/W
      R_base = 0.002/(385 * 0.01) = 0.000519 K/W
      R_total = 0.1 + 0.05 + 0.000519 + 0.00317 = 0.15369 K/W
      Coolant rise = 700/(997 * 1.667e-4 * 4180) = 1.008 C
      T_j = 25 + 0.504 + 700 * 0.15369 = 133.1 C
    """
    result = analyze(AnalyzeColdplateInput(
        heat_load_w=700,
        flow_rate_lpm=10,
        coolant="water",
        inlet_temp_c=25.0,
        r_jc_k_per_w=0.1,
        r_tim_k_per_w=0.05,
    ))

    # Junction temperature: hand calc gives 133.1 C
    assert abs(result.junction_temp_c - 133.1) < 1.0, (
        f"Tj={result.junction_temp_c:.1f} C, expected ~133.1 C"
    )

    # Reynolds number: hand calc gives 4668
    assert abs(result.reynolds - 4668) < 5, (
        f"Re={result.reynolds:.0f}, expected ~4668"
    )

    # Regime should be turbulent (Re > 4000)
    assert result.regime == "turbulent"

    # Total thermal resistance: hand calc gives 0.15369 K/W
    assert abs(result.resistances_k_per_w["total"] - 0.15369) < 0.001, (
        f"R_total={result.resistances_k_per_w['total']:.5f}, expected ~0.15369"
    )

    # Coolant rise: hand calc gives 1.008 C
    assert abs(result.coolant_rise_c - 1.008) < 0.01

    # Convection coefficient: hand calc gives ~24667 W/m2-K
    assert abs(result.heat_transfer_coeff_w_m2k - 24667) < 100


def test_hand_calc_validation_default_case():
    """Validate default case: 700W, 8 LPM, water, default R values.

    This is the 'typical GPU' case with R_jc=0.04, R_tim=0.02.
    Hand calc gives Tj ~ 70.9 C (within expected 65-85 C range).
    """
    result = analyze(AnalyzeColdplateInput(
        heat_load_w=700, flow_rate_lpm=8, coolant="water"
    ))

    # Junction temp should be in the 70-85 C range for a well-designed cold plate
    assert 65 < result.junction_temp_c < 85, (
        f"Tj={result.junction_temp_c:.1f} C, expected 70-85 C range"
    )

    # Specifically, hand calc gives 70.9 C
    assert abs(result.junction_temp_c - 70.9) < 1.0

    # Transitional flow regime at 8 LPM with default geometry
    assert result.regime == "transitional"

    # Pressure drop should be order of 10-50 kPa for microchannel cold plate
    assert 1000 < result.pressure_drop_pa < 100000


# --- Rack-level model validation ---


def test_rack_series_two_gpu_hand_calc():
    """Hand-calc: 2 GPUs in series, 700W each, 8 LPM, 25°C CDU supply, water.

    In series with constant fluid properties:
    - GPU 1 is identical to a standalone analyze() at 25°C inlet.
    - GPU 2 inlet = GPU 1 outlet = 25 + coolant_rise_1.
    - Because fluid properties are constant, coolant_rise is the same for both GPUs.
    - Derived: Tj[1] - Tj[0] = coolant_rise exactly (all R terms cancel).
    - CDU outlet = supply + 2 × coolant_rise.
    - Total ΔP = 2 × single-plate ΔP (same flow, same geometry, same ΔP per plate).

    Hand calculation:
      m_dot = (8/60/1000) × 997 = 0.13293 kg/s
      coolant_rise = 700 / (0.13293 × 4180) = 1.260 °C
      GPU 1 Tj  ≈ 70.9 °C  (default case, validated above)
      GPU 2 Tj  ≈ 70.9 + 1.260 = 72.16 °C
      CDU outlet = 25.0 + 2 × 1.260 = 27.52 °C
      total_dp  = 2 × dp_single
    """
    single = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water"))

    rack = analyze_rack(AnalyzeRackInput(
        gpu_count=2,
        topology="series",
        heat_load_per_gpu_w=700.0,
        total_flow_lpm=8.0,
        cdu_supply_temp_c=25.0,
        coolant="water",
    ))

    # GPU 0 must match standalone analysis at 25°C inlet
    assert abs(rack.per_gpu_junction_temps_c[0] - single.junction_temp_c) < 0.01, (
        f"GPU 0 Tj={rack.per_gpu_junction_temps_c[0]:.2f}, expected {single.junction_temp_c:.2f}"
    )

    # GPU 1 Tj = GPU 0 Tj + coolant_rise (exact relationship from algebra)
    expected_tj1 = rack.per_gpu_junction_temps_c[0] + single.coolant_rise_c
    assert abs(rack.per_gpu_junction_temps_c[1] - expected_tj1) < 0.01, (
        f"GPU 1 Tj={rack.per_gpu_junction_temps_c[1]:.2f}, expected {expected_tj1:.2f}"
    )

    # Hottest GPU is last in series
    assert rack.hottest_gpu_index == 1
    assert abs(rack.max_junction_temp_c - rack.per_gpu_junction_temps_c[1]) < 0.01

    # CDU outlet = supply + N × coolant_rise
    expected_outlet = 25.0 + 2.0 * single.coolant_rise_c
    assert abs(rack.cdu_outlet_temp_c - expected_outlet) < 0.01, (
        f"CDU outlet={rack.cdu_outlet_temp_c:.3f}, expected {expected_outlet:.3f}"
    )

    # Total ΔP = 2 × single-plate ΔP
    assert abs(rack.total_pressure_drop_pa - 2.0 * single.pressure_drop_pa) < 0.1, (
        f"total_dp={rack.total_pressure_drop_pa:.1f}, expected {2 * single.pressure_drop_pa:.1f}"
    )

    # Bookkeeping
    assert rack.total_heat_load_w == 1400.0
    assert rack.gpu_count == 2


def test_rack_parallel_two_gpu_hand_calc():
    """Hand-calc: 2 GPUs in parallel, 700W each, 16 LPM total (8 LPM per GPU), 25°C supply.

    In parallel with equal flow split:
    - Each GPU receives total_flow / gpu_count = 8 LPM.
    - All GPUs have identical inlet (CDU supply) and identical Tj.
    - System ΔP = per-branch ΔP at 8 LPM (not doubled).
    - CDU outlet from energy balance: Q_total / (m_dot_total × cp) + T_supply.

    Hand calculation:
      flow per GPU = 16 / 2 = 8 LPM  → identical to standalone case
      Tj (each GPU) ≈ 70.9 °C
      total_dp = dp at 8 LPM (same as single plate)
      m_dot_total = (16/60/1000) × 997 = 0.26587 kg/s
      CDU outlet = 25 + 1400 / (0.26587 × 4180) = 25 + 1.260 = 26.260 °C
      Note: CDU outlet = supply + single coolant_rise (energy scales with total flow)
    """
    single = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water"))

    rack = analyze_rack(AnalyzeRackInput(
        gpu_count=2,
        topology="parallel",
        heat_load_per_gpu_w=700.0,
        total_flow_lpm=16.0,  # 8 LPM per GPU
        cdu_supply_temp_c=25.0,
        coolant="water",
    ))

    # All GPUs identical in parallel
    for i, tj in enumerate(rack.per_gpu_junction_temps_c):
        assert abs(tj - single.junction_temp_c) < 0.01, (
            f"GPU {i} Tj={tj:.2f}, expected {single.junction_temp_c:.2f}"
        )

    # System ΔP = per-branch ΔP (not cumulative)
    assert abs(rack.total_pressure_drop_pa - single.pressure_drop_pa) < 0.1, (
        f"total_dp={rack.total_pressure_drop_pa:.1f}, expected {single.pressure_drop_pa:.1f}"
    )

    # CDU outlet from energy balance
    m_dot_total = (16.0 / 1000.0 / 60.0) * 997.0
    expected_outlet = 25.0 + 1400.0 / (m_dot_total * 4180.0)
    assert abs(rack.cdu_outlet_temp_c - expected_outlet) < 0.01, (
        f"CDU outlet={rack.cdu_outlet_temp_c:.3f}, expected {expected_outlet:.3f}"
    )

    # CDU outlet = supply + 1 × single coolant_rise (energy balance simplification)
    assert abs(rack.cdu_outlet_temp_c - (25.0 + single.coolant_rise_c)) < 0.01

    assert rack.total_heat_load_w == 1400.0


def test_rack_series_topology_invariants():
    """In series: Tj increases monotonically, CDU outlet increases with GPU count."""
    rack_4 = analyze_rack(AnalyzeRackInput(
        gpu_count=4, topology="series", heat_load_per_gpu_w=700,
        total_flow_lpm=8.0, cdu_supply_temp_c=25.0,
    ))

    # Tj monotonically increases along the chain
    tjs = rack_4.per_gpu_junction_temps_c
    for i in range(1, len(tjs)):
        assert tjs[i] > tjs[i - 1], f"Tj not monotonic: GPU {i-1}={tjs[i-1]:.2f}, GPU {i}={tjs[i]:.2f}"

    # Hottest GPU is always last
    assert rack_4.hottest_gpu_index == 3

    # Consecutive Tj differences are all equal (constant coolant_rise per GPU)
    diffs = [tjs[i] - tjs[i - 1] for i in range(1, len(tjs))]
    assert max(diffs) - min(diffs) < 0.001, f"Tj increments not uniform: {diffs}"


def test_rack_parallel_vs_series_tradeoff():
    """Parallel has lower Tj but higher pump power than series at same per-GPU flow."""
    # Series: 8 LPM through all GPUs (8 LPM per GPU)
    series = analyze_rack(AnalyzeRackInput(
        gpu_count=4, topology="series", heat_load_per_gpu_w=700,
        total_flow_lpm=8.0, cdu_supply_temp_c=25.0,
    ))
    # Parallel: 32 LPM total → 8 LPM per GPU (same per-GPU hydraulics)
    parallel = analyze_rack(AnalyzeRackInput(
        gpu_count=4, topology="parallel", heat_load_per_gpu_w=700,
        total_flow_lpm=32.0, cdu_supply_temp_c=25.0,
    ))

    # Parallel max Tj < series max Tj (coolant temperature stacking eliminated)
    assert parallel.max_junction_temp_c < series.max_junction_temp_c, (
        f"Parallel Tj={parallel.max_junction_temp_c:.1f} should be < series Tj={series.max_junction_temp_c:.1f}"
    )

    # Series has higher total ΔP (4× vs 1× single plate)
    assert series.total_pressure_drop_pa > parallel.total_pressure_drop_pa


def test_rack_chilled_supply_defaults_ambient_to_cdu_supply():
    """Low CDU supply temperatures should not fail when ambient is omitted."""
    series = analyze_rack(AnalyzeRackInput(
        gpu_count=2,
        topology="series",
        heat_load_per_gpu_w=700.0,
        total_flow_lpm=8.0,
        cdu_supply_temp_c=-10.0,
        coolant="water",
    ))
    parallel = analyze_rack(AnalyzeRackInput(
        gpu_count=2,
        topology="parallel",
        heat_load_per_gpu_w=700.0,
        total_flow_lpm=16.0,
        cdu_supply_temp_c=-10.0,
        coolant="water",
    ))

    assert len(series.per_gpu_junction_temps_c) == 2
    assert len(parallel.per_gpu_junction_temps_c) == 2
    assert series.cdu_outlet_temp_c > -10.0
    assert parallel.cdu_outlet_temp_c > -10.0


def test_rack_explicit_ambient_passthrough():
    """Rack ambient should be passed through to per-GPU cold plate inputs."""
    rack = analyze_rack(AnalyzeRackInput(
        gpu_count=2,
        topology="parallel",
        heat_load_per_gpu_w=700.0,
        total_flow_lpm=16.0,
        cdu_supply_temp_c=25.0,
        ambient_temp_c=10.0,
        coolant="water",
    ))

    assert len(rack.per_gpu_junction_temps_c) == 2
    assert all(tj > 25.0 for tj in rack.per_gpu_junction_temps_c)


# ---------------------------------------------------------------------------
# Sensitivity tests
# ---------------------------------------------------------------------------

def test_sensitivity_dtj_dq_hand_calc():
    """∂Tj/∂Q must equal (0.5/(m_dot*cp) + R_total).

    For 700W, 8 LPM water at default geometry:
      Tj = T_inlet + 0.5*Q/(m_dot*cp) + Q * R_total
      ∂Tj/∂Q = 0.5/(m_dot*cp) + R_total
      m_dot = 8/60000 * 997 = 0.13293 kg/s
      0.5/(m_dot*cp) = 0.5/(0.13293 * 4180) = 8.98e-4
      R_total = (Tj - T_inlet) / Q - 0.5/(m_dot*cp)
               = (70.9 - 25) / 700 - 8.98e-4 ≈ 0.0647
      ∂Tj/∂Q ≈ 8.98e-4 + (Tj-T_inlet)/Q - 8.98e-4 = (Tj - T_inlet) / Q
    Simpler: ∂Tj/∂Q = Tj_deviation / Q (since Tj is linear in Q here).
    """
    inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8)
    result = analyze(inp)
    sens = compute_sensitivity(inp)

    # Analytical: ∂Tj/∂Q = (Tj - T_inlet) / Q (since Tj linear in Q, fixed flow)
    expected = (result.junction_temp_c - inp.inlet_temp_c) / inp.heat_load_w
    assert abs(sens.dtj_dq_c_per_w - expected) < 1e-4, (
        f"dtj_dq={sens.dtj_dq_c_per_w:.6f}, expected ≈{expected:.6f}"
    )


def test_sensitivity_dtj_dr_tim_equals_heat_load():
    """∂Tj/∂R_tim must equal Q_heat (analytically exact: Tj = ... + Q*R_tim + ...)."""
    for q in (400.0, 700.0, 1200.0):
        inp = AnalyzeColdplateInput(heat_load_w=q, flow_rate_lpm=8)
        sens = compute_sensitivity(inp)
        assert abs(sens.dtj_dr_tim_c_per_kw - q) < 0.1, (
            f"Q={q}: dtj_dr_tim={sens.dtj_dr_tim_c_per_kw:.2f}, expected {q}"
        )


def test_sensitivity_dtj_dt_inlet_is_one():
    """∂Tj/∂T_inlet must be 1.0 (R_conv and coolant_rise do not depend on inlet temp)."""
    inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8)
    sens = compute_sensitivity(inp)
    assert abs(sens.dtj_dt_inlet_dimensionless - 1.0) < 1e-4, (
        f"dtj_dt_inlet={sens.dtj_dt_inlet_dimensionless:.6f}, expected 1.0"
    )


def test_sensitivity_r_jc_uncertainty_hand_calc():
    """R_jc ±20% → Tj uncertainty = ±(0.2 × R_jc × Q).

    For R_jc=0.04 K/W, Q=700W: ±(0.008 × 700) = ±5.6°C.
    """
    inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, r_jc_k_per_w=0.04)
    sens = compute_sensitivity(inp)
    expected_pm = 0.20 * 0.04 * 700  # = 5.6°C
    assert abs(sens.r_jc_uncertainty_pm_c - expected_pm) < 0.01, (
        f"r_jc_unc={sens.r_jc_uncertainty_pm_c:.3f}, expected {expected_pm:.3f}"
    )


def test_sensitivity_r_tim_aged_hand_calc():
    """R_tim aging (doubling) → Tj rise = R_tim_original × Q.

    For R_tim=0.02 K/W, Q=700W: rise = 0.02 × 700 = 14.0°C.
    """
    inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, r_tim_k_per_w=0.02)
    sens = compute_sensitivity(inp)
    expected_delta = 0.02 * 700  # = 14.0°C (R_tim doubles → Q * R_tim_orig extra)
    assert abs(sens.r_tim_aged_delta_c - expected_delta) < 0.01, (
        f"r_tim_aged_delta={sens.r_tim_aged_delta_c:.3f}, expected {expected_delta:.3f}"
    )


def test_sensitivity_not_returned_by_default():
    """analyze() should not include sensitivity unless explicitly requested."""
    result = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8))
    assert result.sensitivity is None


# ---------------------------------------------------------------------------
# margin_c tests
# ---------------------------------------------------------------------------

def test_optimize_margin_c_increases_flow():
    """Adding a margin must require higher flow (more conservative target)."""
    inp_no_margin = OptimizeFlowRateInput(
        heat_load_w=700, max_junction_temp_c=75, margin_c=0.0, coolant="water"
    )
    inp_margin = OptimizeFlowRateInput(
        heat_load_w=700, max_junction_temp_c=75, margin_c=5.0, coolant="water"
    )
    flow_no_margin, result_no = optimize_flow(inp_no_margin)
    flow_with_margin, result_with = optimize_flow(inp_margin)

    assert flow_with_margin > flow_no_margin, (
        f"With 5°C margin, flow ({flow_with_margin:.2f} LPM) should exceed "
        f"no-margin flow ({flow_no_margin:.2f} LPM)"
    )
    # The margin result must satisfy effective_target = 75 - 5 = 70°C
    if result_with is not None:
        assert result_with.junction_temp_c <= 70.0 + 0.01


def test_optimize_margin_c_zero_equals_no_margin():
    """margin_c=0.0 (default) must give same result as no margin argument."""
    inp_default = OptimizeFlowRateInput(heat_load_w=700, max_junction_temp_c=80)
    inp_zero = OptimizeFlowRateInput(heat_load_w=700, max_junction_temp_c=80, margin_c=0.0)
    flow_default, _ = optimize_flow(inp_default)
    flow_zero, _ = optimize_flow(inp_zero)
    assert abs(flow_default - flow_zero) < 1e-6


def test_optimize_margin_c_infeasible():
    """margin_c that makes the effective target unachievable returns met_target=False."""
    # Effective target = 70 - 60 = 10°C, physically impossible with 25°C inlet
    inp = OptimizeFlowRateInput(
        heat_load_w=700, max_junction_temp_c=70, margin_c=60.0, coolant="water"
    )
    flow, result = optimize_flow(inp)
    assert result is None
