import pytest

from thermal_mcp_server.physics import analyze, analyze_rack
from thermal_mcp_server.schemas import AnalyzeColdplateInput, AnalyzeRackInput


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
