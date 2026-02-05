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
