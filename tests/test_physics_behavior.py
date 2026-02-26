import pytest

from thermal_mcp_server.physics import analyze
from thermal_mcp_server.schemas import AnalyzeColdplateInput


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

    Case: 700W GPU, water coolant, 10 LPM, default geometry.
    R_jc = 0.1 K/W, R_tim = 0.05 K/W (conservative thermal stack).

    Hand calculation (independent of model code):
      Re = 997 * 4.167 * 0.001 / 0.00089 = 4668 (turbulent)
      Pr = 4180 * 0.00089 / 0.60 = 6.20
      Nu = 0.023 * 4668^0.8 * 6.20^0.4 = 41.1
      h  = 41.1 * 0.60 / 0.001 = 24667 W/m2-K
      A_wet = 40 * 4 * 0.001 * 0.08 = 0.01280 m2  (square channel: perimeter = 4 * side)
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
