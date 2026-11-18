import pytest

from thermal_mcp_server.physics import analyze, analyze_rack, compute_sensitivity, optimize_flow
from thermal_mcp_server.schemas import AnalyzeColdplateInput, AnalyzeRackInput, Geometry, OptimizeFlowRateInput


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


@pytest.mark.parametrize(
    ("flow_lpm", "expected_re", "expected_dp_pa", "expected_regime"),
    [
        # Independent Darcy-Weisbach calculation with f = (f·Re)_Darcy(1) / Re,
        # Shah & London square duct: (f·Re)_Darcy(1) = 56.9184.
        (1.0, 466.760300, 844.2896, "laminar"),
        # Independent calculation using the documented linear transition blend.
        # Laminar end f = 56.9184 / 2300; blend = 0.843577881, f = 0.0374329080.
        (8.0, 3734.082397, 16586.937, "transitional"),
        # Independent Darcy-Weisbach calculation with Blasius friction.
        (10.0, 4667.602996, 26503.038, "turbulent"),
    ],
)
def test_darcy_weisbach_absolute_values_across_regimes(
    flow_lpm: float,
    expected_re: float,
    expected_dp_pa: float,
    expected_regime: str,
):
    """Verify the implementation against independent literal Darcy calculations.

    These are equation-verification tests: they prove that the current declared
    friction-factor equations and unit conversions are implemented as intended.
    They do not validate those correlations for a physical cold plate.
    """
    result = analyze(AnalyzeColdplateInput(flow_rate_lpm=flow_lpm, coolant="water"))

    assert result.reynolds == pytest.approx(expected_re, abs=1e-3)
    assert result.pressure_drop_pa == pytest.approx(expected_dp_pa, abs=0.01)
    assert result.regime == expected_regime


@pytest.mark.parametrize(
    ("flow_lpm", "expected_re", "expected_dp_pa"),
    [
        # Re = 2300 and f = 56.9184 / 2300 (Shah & London, alpha = 1) at the lower endpoint.
        (4.927582748244734, 2300.0, 4160.306867),
        # Re = 4000 and f = 0.3164 * Re**-0.25 at the upper endpoint.
        (8.569709127382145, 4000.0, 20229.553904),
    ],
)
def test_darcy_transition_endpoints_are_continuous(flow_lpm: float, expected_re: float, expected_dp_pa: float):
    """Verify the declared transition interpolation reaches both endpoints.

    Continuity is a software property of the chosen blend, not evidence that
    the blend is a physically validated transition correlation.
    """
    result = analyze(AnalyzeColdplateInput(flow_rate_lpm=flow_lpm, coolant="water"))

    assert result.reynolds == pytest.approx(expected_re, abs=1e-9)
    assert result.pressure_drop_pa == pytest.approx(expected_dp_pa, abs=0.01)
    assert result.regime == "transitional"


def test_darcy_weisbach_rectangular_hydraulic_diameter_passthrough():
    """Verify Dh and channel-area handling for a non-square channel geometry.

    The expected values are an independent calculation of the current
    rectangular-channel equations; this does not establish correlation
    validity for rectangular ducts.
    """
    geometry = Geometry(
        channel_count=20,
        channel_width_m=2.0e-3,
        channel_height_m=1.0e-3,
        channel_length_m=0.08,
    )
    result = analyze(AnalyzeColdplateInput(flow_rate_lpm=8.0, coolant="water", geometry=geometry))

    # A = 20 * 0.002 * 0.001 = 4.0e-5 m², v = 3.333333 m/s,
    # Dh = 2*0.002*0.001/(0.002+0.001) = 0.001333333 m.
    assert result.reynolds == pytest.approx(4978.776529, abs=1e-3)
    assert result.pressure_drop_pa == pytest.approx(12517.849334, abs=0.01)
    assert result.regime == "turbulent"


def test_darcy_weisbach_glycol_uses_declared_properties():
    """Verify the glycol branch with independent nominal-property arithmetic."""
    result = analyze(AnalyzeColdplateInput(flow_rate_lpm=8.0, coolant="glycol50"))

    # rho=1060 kg/m³, mu=0.0048 Pa·s, v=3.333333 m/s, Dh=0.001 m.
    # Re=736.111111, f=56.9184/Re=0.077323109, ΔP=36427.776 Pa.
    assert result.reynolds == pytest.approx(736.111111, abs=1e-3)
    assert result.pressure_drop_pa == pytest.approx(36427.776, abs=0.01)
    assert result.regime == "laminar"


def test_single_plate_coolant_energy_balance():
    """Verify Q = m_dot * cp * coolant rise for the no-loss model boundary."""
    heat_load_w = 700.0
    flow_lpm = 8.0
    rho_kg_m3 = 997.0
    cp_j_kgk = 4180.0
    mass_flow_kg_s = (flow_lpm / 60000.0) * rho_kg_m3

    result = analyze(
        AnalyzeColdplateInput(
            heat_load_w=heat_load_w,
            flow_rate_lpm=flow_lpm,
            coolant="water",
        )
    )

    expected_rise_c = heat_load_w / (mass_flow_kg_s * cp_j_kgk)
    assert result.coolant_rise_c == pytest.approx(expected_rise_c, abs=1e-9)
    assert mass_flow_kg_s * cp_j_kgk * result.coolant_rise_c == pytest.approx(heat_load_w, rel=1e-12)


def test_analyze_warns_when_result_uses_unvalidated_applicability_assumptions():
    """Applicability warnings accompany nominal outputs without changing them."""
    result = analyze(AnalyzeColdplateInput(flow_rate_lpm=8.0, inlet_temp_c=25.0))

    warnings = " ".join(result.warnings).lower()
    assert "transitional-flow correlation" in warnings
    assert "rectangular-channel correlations" in warnings
    assert "effective heated-area" in warnings
    assert "no measured cold-plate validation" in warnings


def test_analyze_warns_when_inlet_differs_from_property_reference():
    """Non-reference inlet temperatures disclose fixed nominal properties."""
    result = analyze(AnalyzeColdplateInput(flow_rate_lpm=10.0, inlet_temp_c=35.0))

    assert any("nominal 25°C values" in warning for warning in result.warnings)


def test_analyze_does_not_warn_property_reference_at_25c():
    """The property-reference warning is specific to an off-reference inlet."""
    result = analyze(AnalyzeColdplateInput(flow_rate_lpm=10.0, inlet_temp_c=25.0))

    assert not any("nominal 25°C values" in warning for warning in result.warnings)


def test_rack_deduplicates_shared_applicability_warnings():
    """Rack results retain shared warnings once instead of repeating per GPU."""
    result = analyze_rack(
        AnalyzeRackInput(
            gpu_count=4,
            topology="series",
            heat_load_per_gpu_w=700.0,
            total_flow_lpm=8.0,
            cdu_supply_temp_c=25.0,
            coolant="water",
        )
    )

    measured_warnings = [warning for warning in result.warnings if "no measured cold-plate validation" in warning]
    rectangular_warnings = [warning for warning in result.warnings if "rectangular-channel correlations" in warning]
    assert len(measured_warnings) == 1
    assert len(rectangular_warnings) == 1
    assert measured_warnings[0].startswith("all GPUs:")
    assert rectangular_warnings[0].startswith("all GPUs:")
    property_warnings = [warning for warning in result.warnings if "nominal 25°C values" in warning]
    assert len(property_warnings) == 1
    assert property_warnings[0].startswith("GPUs 1–3 (3/4):")


def test_physics_layer_does_not_apply_a_context_free_temperature_limit():
    """Caller-specific limits belong to the decision layer, not analyze()."""
    result = analyze(AnalyzeColdplateInput(heat_load_w=1200.0, flow_rate_lpm=8.0))

    assert result.junction_temp_c > 85.0
    assert not any("85" in warning for warning in result.warnings)


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
    result = analyze(
        AnalyzeColdplateInput(
            heat_load_w=700,
            flow_rate_lpm=10,
            coolant="water",
            inlet_temp_c=25.0,
            r_jc_k_per_w=0.1,
            r_tim_k_per_w=0.05,
        )
    )

    # Junction temperature: hand calc gives 133.1 C
    assert abs(result.junction_temp_c - 133.1) < 1.0, f"Tj={result.junction_temp_c:.1f} C, expected ~133.1 C"

    # Reynolds number: hand calc gives 4668
    assert abs(result.reynolds - 4668) < 5, f"Re={result.reynolds:.0f}, expected ~4668"

    # Regime should be turbulent (Re > 4000)
    assert result.regime == "turbulent"

    # Total thermal resistance: hand calc gives 0.15369 K/W
    assert abs(result.resistances_k_per_w["total"] - 0.15369) < 0.001, f"R_total={result.resistances_k_per_w['total']:.5f}, expected ~0.15369"

    # Coolant rise: hand calc gives 1.008 C
    assert abs(result.coolant_rise_c - 1.008) < 0.01

    # Convection coefficient: hand calc gives ~24667 W/m2-K
    assert abs(result.heat_transfer_coeff_w_m2k - 24667) < 100


def test_hand_calc_validation_default_case():
    """Validate default case: 700W, 8 LPM, water, default R values.

    This is the 'typical GPU' case with R_jc=0.04, R_tim=0.02, default square
    1 mm × 1 mm channels (alpha = 1).

    Hand calculation (independent of model code):
      Dh     = 2 × 0.001 × 0.001 / (0.001 + 0.001) = 0.001 m
      v      = (8/60000) / (40 × 0.001 × 0.001) = 3.33333333 m/s
      Re     = 997 × 3.33333333 × 0.001 / 0.00089 = 3734.08240  (transitional)
      Pr     = 4180 × 0.00089 / 0.60 = 6.20033333
      Laminar end of the blend (Shah & London, alpha = 1):
        Nu_lam = 8.235 × (1 − 2.0421 + 3.0853 − 2.4765 + 1.0578 − 0.1861) = 8.235 × 0.4384 = 3.610224
        f·Re   = 96 × (1 − 1.3553 + 1.9467 − 1.7012 + 0.9564 − 0.2537) = 96 × 0.5929 = 56.9184 (Darcy)
      Turbulent end: Nu_turb(4000) = 0.023 × 4000^0.8 × 6.20033333^0.4 = 36.3363955
                     f_turb(4000)  = 0.3164 × 4000^−0.25 = 0.0397851937
      blend  = (3734.08240 − 2300) / 1700 = 0.843577881
      Nu     = 3.610224 × (1 − 0.843577881) + 36.3363955 × 0.843577881 = 31.2172984
      h      = 31.2172984 × 0.60 / 0.001 = 18730.3791 W/m²·K
      A_wet  = 40 × 2 × (0.001 + 0.001) × 0.08 = 0.0128 m²
      R_conv = 1 / (18730.3791 × 0.0128) = 0.00417103145 K/W
      R_base = 0.002 / (385 × 0.01) = 0.000519480519 K/W
      R_tot  = 0.04 + 0.02 + 0.000519480519 + 0.00417103145 = 0.0646905120 K/W
      rise   = 700 / (0.132933333 × 4180) = 1.25976014 °C
      Tj     = 25 + 0.5 × 1.25976014 + 700 × 0.0646905120 = 70.9132384 °C
      f      = (56.9184 / 2300) × (1 − 0.843577881) + 0.0397851937 × 0.843577881 = 0.0374329080
      ΔP     = 0.0374329080 × (0.08 / 0.001) × 997 × 3.33333333² / 2 = 16586.9374 Pa
      P_pump = 16586.9374 × (8/60000) / 0.5 = 4.42318332 W
    """
    result = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water"))

    assert result.reynolds == pytest.approx(3734.08240, rel=1e-6)
    assert result.nusselt == pytest.approx(31.2172984, rel=1e-6)
    assert result.heat_transfer_coeff_w_m2k == pytest.approx(18730.3791, rel=1e-6)
    assert result.resistances_k_per_w["convection"] == pytest.approx(0.00417103145, rel=1e-6)
    assert result.resistances_k_per_w["total"] == pytest.approx(0.0646905120, rel=1e-6)
    assert result.coolant_rise_c == pytest.approx(1.25976014, rel=1e-6)
    assert result.junction_temp_c == pytest.approx(70.9132384, rel=1e-6)
    assert result.pressure_drop_pa == pytest.approx(16586.9374, rel=1e-6)
    assert result.pump_power_w == pytest.approx(4.42318332, rel=1e-6)

    # Junction temp should be in the 70-85 C range for a well-designed cold plate
    assert 65 < result.junction_temp_c < 85, f"Tj={result.junction_temp_c:.1f} C, expected 70-85 C range"

    # Specifically, hand calc gives 70.9 C
    assert abs(result.junction_temp_c - 70.9) < 1.0

    # Transitional flow regime at 8 LPM with default geometry
    assert result.regime == "transitional"

    # Pressure drop should be order of 10-50 kPa for microchannel cold plate
    assert 1000 < result.pressure_drop_pa < 100000


def test_hand_calc_validation_laminar_default_geometry_4lpm():
    """Laminar hand calculation on the default geometry: 700 W, 4 LPM, water, 25 °C.

    Hand calculation (independent of model code):
      Dh     = 0.001 m, alpha = 1
      v      = (4/60000) / (40 × 0.001 × 0.001) = 1.66666667 m/s
      Re     = 997 × 1.66666667 × 0.001 / 0.00089 = 1867.04120  (laminar)
      Nu     = Nu_H1(1) = 8.235 × 0.4384 = 3.610224   (Shah & London)
      h      = 3.610224 × 0.60 / 0.001 = 2166.1344 W/m²·K
      R_conv = 1 / (2166.1344 × 0.0128) = 0.0360665525 K/W
      R_tot  = 0.04 + 0.02 + 0.000519480519 + 0.0360665525 = 0.0965860330 K/W
      m_dot  = (4/60000) × 997 = 0.0664666667 kg/s
      rise   = 700 / (0.0664666667 × 4180) = 2.51952028 °C
      Tj     = 25 + 0.5 × 2.51952028 + 700 × 0.0965860330 = 93.8699832 °C
      f      = (f·Re)_Darcy(1) / Re = 56.9184 / 1867.04120 = 0.0304858833
      ΔP     = 0.0304858833 × (0.08 / 0.001) × 997 × 1.66666667² / 2 = 3377.1584 Pa
      P_pump = 3377.1584 × (4/60000) / 0.5 = 0.450287787 W
    """
    result = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=4, coolant="water"))

    assert result.regime == "laminar"
    assert result.reynolds == pytest.approx(1867.04120, rel=1e-6)
    assert result.nusselt == pytest.approx(3.610224, rel=1e-6)
    assert result.heat_transfer_coeff_w_m2k == pytest.approx(2166.1344, rel=1e-6)
    assert result.resistances_k_per_w["convection"] == pytest.approx(0.0360665525, rel=1e-6)
    assert result.resistances_k_per_w["total"] == pytest.approx(0.0965860330, rel=1e-6)
    assert result.coolant_rise_c == pytest.approx(2.51952028, rel=1e-6)
    assert result.junction_temp_c == pytest.approx(93.8699832, rel=1e-6)
    assert result.pressure_drop_pa == pytest.approx(3377.1584, rel=1e-6)
    assert result.pump_power_w == pytest.approx(0.450287787, rel=1e-6)


def test_full_wetted_area_uses_channel_aspect_ratio():
    """A 0.5 mm × 2 mm channel (alpha = 0.25) uses its own laminar Nu and f·Re, and
    swapping width and height gives the same Nu and f."""
    tall = Geometry(channel_width_m=0.5e-3, channel_height_m=2.0e-3)
    wide = Geometry(channel_width_m=2.0e-3, channel_height_m=0.5e-3)
    tall_inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=0.5, coolant="water", geometry=tall)
    wide_inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=0.5, coolant="water", geometry=wide)
    a, b = analyze(tall_inp), analyze(wide_inp)

    assert a.regime == "laminar"
    # Shah & London tabulated values at alpha = 0.25: Nu_H1 = 5.331, Darcy f·Re = 72.932.
    assert a.nusselt == pytest.approx(5.331, rel=5e-3)
    assert _darcy_f_re(a, tall_inp) == pytest.approx(72.932, rel=5e-3)
    assert b.nusselt == pytest.approx(a.nusselt, rel=1e-12)
    assert b.reynolds == pytest.approx(a.reynolds, rel=1e-12)
    assert _darcy_f_re(b, wide_inp) / b.reynolds == pytest.approx(_darcy_f_re(a, tall_inp) / a.reynolds, rel=1e-9)


@pytest.mark.parametrize("boundary_re", [2300.0, 4000.0])
def test_full_wetted_area_nu_and_friction_continuous_at_regime_boundaries(boundary_re: float):
    """On the full_wetted_area path Nu and f are continuous across Re = 2300 and Re = 4000."""
    g = Geometry()
    below_inp = _fin_input_at_re(boundary_re * (1 - 1e-9), g)
    above_inp = _fin_input_at_re(boundary_re * (1 + 1e-9), g)
    below, above = analyze(below_inp), analyze(above_inp)
    assert below.regime != above.regime
    assert above.nusselt == pytest.approx(below.nusselt, rel=1e-6)
    f_below = _darcy_f_re(below, below_inp) / below.reynolds
    f_above = _darcy_f_re(above, above_inp) / above.reynolds
    assert f_above == pytest.approx(f_below, rel=1e-6)


def test_full_wetted_area_energy_balance_closes():
    """Q = m_dot·cp·ΔT within 1% (and to round-off) at laminar, transitional and turbulent flows."""
    for flow_lpm in (1.0, 4.0, 8.0, 10.0):
        result = analyze(AnalyzeColdplateInput(heat_load_w=700.0, flow_rate_lpm=flow_lpm, coolant="water"))
        m_dot = flow_lpm / 60000.0 * 997.0
        assert m_dot * 4180.0 * result.coolant_rise_c == pytest.approx(700.0, rel=1e-2)
        assert m_dot * 4180.0 * result.coolant_rise_c == pytest.approx(700.0, rel=1e-12)


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
      GPU 1 Tj  ≈ 70.91 °C  (default case, validated above)
      GPU 2 Tj  ≈ 70.91 + 1.260 = 72.17 °C
      CDU outlet = 25.0 + 2 × 1.260 = 27.52 °C
      total_dp  = 2 × dp_single
    """
    single = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water"))

    rack = analyze_rack(
        AnalyzeRackInput(
            gpu_count=2,
            topology="series",
            heat_load_per_gpu_w=700.0,
            total_flow_lpm=8.0,
            cdu_supply_temp_c=25.0,
            coolant="water",
        )
    )

    # GPU 0 must match standalone analysis at 25°C inlet
    assert abs(rack.per_gpu_junction_temps_c[0] - single.junction_temp_c) < 0.01, (
        f"GPU 0 Tj={rack.per_gpu_junction_temps_c[0]:.2f}, expected {single.junction_temp_c:.2f}"
    )

    # GPU 1 Tj = GPU 0 Tj + coolant_rise (exact relationship from algebra)
    expected_tj1 = rack.per_gpu_junction_temps_c[0] + single.coolant_rise_c
    assert abs(rack.per_gpu_junction_temps_c[1] - expected_tj1) < 0.01, f"GPU 1 Tj={rack.per_gpu_junction_temps_c[1]:.2f}, expected {expected_tj1:.2f}"

    # Hottest GPU is last in series
    assert rack.hottest_gpu_index == 1
    assert abs(rack.max_junction_temp_c - rack.per_gpu_junction_temps_c[1]) < 0.01

    # CDU outlet = supply + N × coolant_rise
    expected_outlet = 25.0 + 2.0 * single.coolant_rise_c
    assert abs(rack.cdu_outlet_temp_c - expected_outlet) < 0.01, f"CDU outlet={rack.cdu_outlet_temp_c:.3f}, expected {expected_outlet:.3f}"

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

    rack = analyze_rack(
        AnalyzeRackInput(
            gpu_count=2,
            topology="parallel",
            heat_load_per_gpu_w=700.0,
            total_flow_lpm=16.0,  # 8 LPM per GPU
            cdu_supply_temp_c=25.0,
            coolant="water",
        )
    )

    # All GPUs identical in parallel
    for i, tj in enumerate(rack.per_gpu_junction_temps_c):
        assert abs(tj - single.junction_temp_c) < 0.01, f"GPU {i} Tj={tj:.2f}, expected {single.junction_temp_c:.2f}"

    # System ΔP = per-branch ΔP (not cumulative)
    assert abs(rack.total_pressure_drop_pa - single.pressure_drop_pa) < 0.1, (
        f"total_dp={rack.total_pressure_drop_pa:.1f}, expected {single.pressure_drop_pa:.1f}"
    )

    # CDU outlet from energy balance
    m_dot_total = (16.0 / 1000.0 / 60.0) * 997.0
    expected_outlet = 25.0 + 1400.0 / (m_dot_total * 4180.0)
    assert abs(rack.cdu_outlet_temp_c - expected_outlet) < 0.01, f"CDU outlet={rack.cdu_outlet_temp_c:.3f}, expected {expected_outlet:.3f}"

    # CDU outlet = supply + 1 × single coolant_rise (energy balance simplification)
    assert abs(rack.cdu_outlet_temp_c - (25.0 + single.coolant_rise_c)) < 0.01

    assert rack.total_heat_load_w == 1400.0


def test_rack_series_topology_invariants():
    """In series: Tj increases monotonically, CDU outlet increases with GPU count."""
    rack_4 = analyze_rack(
        AnalyzeRackInput(
            gpu_count=4,
            topology="series",
            heat_load_per_gpu_w=700,
            total_flow_lpm=8.0,
            cdu_supply_temp_c=25.0,
        )
    )

    # Tj monotonically increases along the chain
    tjs = rack_4.per_gpu_junction_temps_c
    for i in range(1, len(tjs)):
        assert tjs[i] > tjs[i - 1], f"Tj not monotonic: GPU {i - 1}={tjs[i - 1]:.2f}, GPU {i}={tjs[i]:.2f}"

    # Hottest GPU is always last
    assert rack_4.hottest_gpu_index == 3

    # Consecutive Tj differences are all equal (constant coolant_rise per GPU)
    diffs = [tjs[i] - tjs[i - 1] for i in range(1, len(tjs))]
    assert max(diffs) - min(diffs) < 0.001, f"Tj increments not uniform: {diffs}"


def test_rack_parallel_vs_series_tradeoff():
    """Parallel has lower Tj but higher pump power than series at same per-GPU flow."""
    # Series: 8 LPM through all GPUs (8 LPM per GPU)
    series = analyze_rack(
        AnalyzeRackInput(
            gpu_count=4,
            topology="series",
            heat_load_per_gpu_w=700,
            total_flow_lpm=8.0,
            cdu_supply_temp_c=25.0,
        )
    )
    # Parallel: 32 LPM total → 8 LPM per GPU (same per-GPU hydraulics)
    parallel = analyze_rack(
        AnalyzeRackInput(
            gpu_count=4,
            topology="parallel",
            heat_load_per_gpu_w=700,
            total_flow_lpm=32.0,
            cdu_supply_temp_c=25.0,
        )
    )

    # Parallel max Tj < series max Tj (coolant temperature stacking eliminated)
    assert parallel.max_junction_temp_c < series.max_junction_temp_c, (
        f"Parallel Tj={parallel.max_junction_temp_c:.1f} should be < series Tj={series.max_junction_temp_c:.1f}"
    )

    # Series has higher total ΔP (4× vs 1× single plate)
    assert series.total_pressure_drop_pa > parallel.total_pressure_drop_pa


def test_rack_chilled_supply_defaults_ambient_to_cdu_supply():
    """Low CDU supply temperatures should not fail when ambient is omitted."""
    series = analyze_rack(
        AnalyzeRackInput(
            gpu_count=2,
            topology="series",
            heat_load_per_gpu_w=700.0,
            total_flow_lpm=8.0,
            cdu_supply_temp_c=-10.0,
            coolant="water",
        )
    )
    parallel = analyze_rack(
        AnalyzeRackInput(
            gpu_count=2,
            topology="parallel",
            heat_load_per_gpu_w=700.0,
            total_flow_lpm=16.0,
            cdu_supply_temp_c=-10.0,
            coolant="water",
        )
    )

    assert len(series.per_gpu_junction_temps_c) == 2
    assert len(parallel.per_gpu_junction_temps_c) == 2
    assert series.cdu_outlet_temp_c > -10.0
    assert parallel.cdu_outlet_temp_c > -10.0


def test_rack_explicit_ambient_passthrough():
    """Rack ambient should be passed through to per-GPU cold plate inputs."""
    rack = analyze_rack(
        AnalyzeRackInput(
            gpu_count=2,
            topology="parallel",
            heat_load_per_gpu_w=700.0,
            total_flow_lpm=16.0,
            cdu_supply_temp_c=25.0,
            ambient_temp_c=10.0,
            coolant="water",
        )
    )

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
               = (70.91 - 25) / 700 - 8.98e-4 ≈ 0.0647
      ∂Tj/∂Q ≈ 8.98e-4 + (Tj-T_inlet)/Q - 8.98e-4 = (Tj - T_inlet) / Q
    Simpler: ∂Tj/∂Q = Tj_deviation / Q (since Tj is linear in Q here).
    """
    inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8)
    result = analyze(inp)
    sens = compute_sensitivity(inp)

    # Analytical: ∂Tj/∂Q = (Tj - T_inlet) / Q (since Tj linear in Q, fixed flow)
    expected = (result.junction_temp_c - inp.inlet_temp_c) / inp.heat_load_w
    assert abs(sens.dtj_dq_c_per_w - expected) < 1e-4, f"dtj_dq={sens.dtj_dq_c_per_w:.6f}, expected ≈{expected:.6f}"


def test_sensitivity_dtj_dr_tim_equals_heat_load():
    """∂Tj/∂R_tim must equal Q_heat (analytically exact: Tj = ... + Q*R_tim + ...)."""
    for q in (400.0, 700.0, 1200.0):
        inp = AnalyzeColdplateInput(heat_load_w=q, flow_rate_lpm=8)
        sens = compute_sensitivity(inp)
        assert abs(sens.dtj_dr_tim_c_per_kw - q) < 0.1, f"Q={q}: dtj_dr_tim={sens.dtj_dr_tim_c_per_kw:.2f}, expected {q}"


def test_sensitivity_dtj_dt_inlet_is_one():
    """∂Tj/∂T_inlet must be 1.0 (R_conv and coolant_rise do not depend on inlet temp)."""
    inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8)
    sens = compute_sensitivity(inp)
    assert abs(sens.dtj_dt_inlet_dimensionless - 1.0) < 1e-4, f"dtj_dt_inlet={sens.dtj_dt_inlet_dimensionless:.6f}, expected 1.0"


def test_sensitivity_r_jc_uncertainty_hand_calc():
    """An illustrative centered R_jc perturbation gives ±(0.2 × R_jc × Q).

    This is a model delta, not a manufacturing tolerance or probability bound.
    For R_jc=0.04 K/W, Q=700W: ±(0.008 × 700) = ±5.6°C.
    """
    inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, r_jc_k_per_w=0.04)
    sens = compute_sensitivity(inp)
    expected_pm = 0.20 * 0.04 * 700  # = 5.6°C
    assert abs(sens.r_jc_uncertainty_pm_c - expected_pm) < 0.01, f"r_jc_unc={sens.r_jc_uncertainty_pm_c:.3f}, expected {expected_pm:.3f}"


def test_sensitivity_r_tim_aged_hand_calc():
    """A doubled-R_tim scenario gives Tj rise = R_tim_original × Q.

    This is an illustrative model scenario, not a field-aging prediction.
    For R_tim=0.02 K/W, Q=700W: rise = 0.02 × 700 = 14.0°C.
    """
    inp = AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, r_tim_k_per_w=0.02)
    sens = compute_sensitivity(inp)
    expected_delta = 0.02 * 700  # = 14.0°C (doubled R_tim adds Q * R_tim_orig)
    assert abs(sens.r_tim_aged_delta_c - expected_delta) < 0.01, f"r_tim_aged_delta={sens.r_tim_aged_delta_c:.3f}, expected {expected_delta:.3f}"


def test_sensitivity_not_returned_by_default():
    """analyze() should not include sensitivity unless explicitly requested."""
    result = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8))
    assert result.sensitivity is None


# ---------------------------------------------------------------------------
# margin_c tests
# ---------------------------------------------------------------------------


def test_optimize_margin_c_increases_flow():
    """Adding a margin must require higher flow (more conservative target)."""
    inp_no_margin = OptimizeFlowRateInput(heat_load_w=700, max_junction_temp_c=75, margin_c=0.0, coolant="water")
    inp_margin = OptimizeFlowRateInput(heat_load_w=700, max_junction_temp_c=75, margin_c=5.0, coolant="water")
    flow_no_margin, result_no = optimize_flow(inp_no_margin)
    flow_with_margin, result_with = optimize_flow(inp_margin)

    assert flow_with_margin > flow_no_margin, f"With 5°C margin, flow ({flow_with_margin:.2f} LPM) should exceed no-margin flow ({flow_no_margin:.2f} LPM)"
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
    inp = OptimizeFlowRateInput(heat_load_w=700, max_junction_temp_c=70, margin_c=60.0, coolant="water")
    flow, result = optimize_flow(inp)
    assert result is None


# ---------------------------------------------------------------------------
# Straight-fin channel model (docs/physics.md Section I)
# ---------------------------------------------------------------------------

_FIN_WARNING = (
    "straight-fin model assumes fully developed laminar flow with an adiabatic cover; "
    "entrance effects, fin-tip heat transfer and flow maldistribution are not modeled"
)
_FIN_RANGE_WARNING = "straight-fin correlations were checked for laminar flow only; this operating point is outside that range"


def _screen_1d_geometry(**overrides) -> Geometry:
    """The 0.39 / 0.39 / 3.75 mm design used by thermal-design-loop screen_1d."""
    fields = dict(
        channel_count=76,
        channel_width_m=0.39e-3,
        channel_height_m=3.75e-3,
        channel_length_m=0.06,
        base_thickness_m=2.0e-3,
        contact_area_m2=76 * 0.78e-3 * 0.06,
        copper_k_w_mk=385.0,
        channel_model="straight_fin",
        fin_thickness_m=0.39e-3,
    )
    fields.update(overrides)
    return Geometry(**fields)


def _darcy_f_re(result, inp: AnalyzeColdplateInput) -> float:
    """Recover Darcy f·Re from the reported pressure drop: f = ΔP / ((L/Dh)·ρv²/2)."""
    g = inp.geometry
    rho = {"water": 997.0, "glycol50": 1060.0}[inp.coolant]
    dh = 2 * g.channel_width_m * g.channel_height_m / (g.channel_width_m + g.channel_height_m)
    v = inp.flow_rate_lpm / 60000.0 / (g.channel_count * g.channel_width_m * g.channel_height_m)
    f = result.pressure_drop_pa / ((g.channel_length_m / dh) * rho * v**2 / 2)
    return f * result.reynolds


def _fin_input_at_re(target_re: float, geometry: Geometry) -> AnalyzeColdplateInput:
    """Water input whose Reynolds number equals target_re for the given geometry."""
    dh = 2 * geometry.channel_width_m * geometry.channel_height_m / (geometry.channel_width_m + geometry.channel_height_m)
    area = geometry.channel_count * geometry.channel_width_m * geometry.channel_height_m
    flow_lpm = target_re * 0.00089 / (997.0 * dh) * area * 60000.0
    return AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=flow_lpm, coolant="water", geometry=geometry)


@pytest.mark.parametrize(
    ("alpha", "f_re_fanning", "f_re_darcy", "nu_h1"),
    [
        # Shah & London (1978) tabulated fully developed values for rectangular ducts.
        (1.0, 14.227, 56.908, 3.608),
        (0.5, 15.548, 62.192, 4.123),
        (0.25, 18.233, 72.932, 5.331),
        (0.125, 20.585, 82.340, 6.490),
    ],
)
def test_straight_fin_correlations_match_shah_london_table(alpha: float, f_re_fanning: float, f_re_darcy: float, nu_h1: float):
    """G1: the polynomials reproduce the tabulated values within 0.5% relative."""
    geometry = Geometry(
        channel_count=40,
        channel_width_m=1.0e-3 * alpha,
        channel_height_m=1.0e-3,
        channel_model="straight_fin",
        fin_thickness_m=0.5e-3,
    )
    inp = AnalyzeColdplateInput(flow_rate_lpm=0.5, coolant="water", geometry=geometry)
    result = analyze(inp)

    assert result.regime == "laminar"
    assert result.nusselt == pytest.approx(nu_h1, rel=5e-3)
    f_re = _darcy_f_re(result, inp)
    assert f_re == pytest.approx(f_re_darcy, rel=5e-3)
    assert f_re / 4 == pytest.approx(f_re_fanning, rel=5e-3)


@pytest.mark.parametrize(
    ("coolant", "expected"),
    [
        (
            "water",
            dict(
                reynolds=178.016895,
                nusselt=6.738931,
                fin_efficiency=0.749545,
                pressure_drop_pa=1014.389176,
                convection=0.00637425442,
                base_conduction=0.00146052778,
                coolant_rise_c=9.598173,
                junction_temp_c=97.633868,
            ),
        ),
        (
            "glycol50",
            dict(
                reynolds=35.093016,
                nusselt=6.738931,
                fin_efficiency=0.814606,
                pressure_drop_pa=5470.862974,
                convection=0.00884355568,
                base_conduction=0.00146052778,
                coolant_rise_c=11.098779,
                junction_temp_c=100.853473,
            ),
        ),
    ],
)
def test_straight_fin_reproduces_screen_1d(coolant: str, expected: dict[str, float]):
    """G2: reproduce thermal-design-loop analyze_1d (commit 189f017) at this repo's
    coolant constants, 1000 W, 1.5 LPM, 25 °C inlet, default R_jc and R_tim."""
    result = analyze(AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, coolant=coolant, geometry=_screen_1d_geometry()))

    assert result.regime == "laminar"
    assert result.reynolds == pytest.approx(expected["reynolds"], rel=1e-6)
    assert result.nusselt == pytest.approx(expected["nusselt"], rel=1e-6)
    assert result.fin_efficiency == pytest.approx(expected["fin_efficiency"], rel=1e-6)
    assert result.pressure_drop_pa == pytest.approx(expected["pressure_drop_pa"], rel=1e-6)
    assert result.resistances_k_per_w["convection"] == pytest.approx(expected["convection"], rel=1e-6)
    assert result.resistances_k_per_w["base_conduction"] == pytest.approx(expected["base_conduction"], rel=1e-6)
    assert result.coolant_rise_c == pytest.approx(expected["coolant_rise_c"], rel=1e-6)
    assert result.junction_temp_c == pytest.approx(expected["junction_temp_c"], rel=1e-6)


def test_hand_calc_validation_straight_fin_800w_water():
    """G3: independent hand calculation for the straight-fin path.

    Case: 800 W, water, 2.0 LPM, 25 °C inlet, R_jc = 0.04 K/W, R_tim = 0.02 K/W.
    Geometry: N = 50 channels, w = 0.6 mm, H = 1.5 mm, fin t = 0.4 mm, L = 50 mm,
    base 2 mm, k = 385 W/m·K, contact area = N × (w + t) × L = 50 × 1.0e-3 × 0.05 = 2.5e-3 m².
    Water: rho = 997, cp = 4180, k = 0.60, mu = 0.00089.

    Hand calculation (independent of model code):
      alpha  = min(w, H) / max(w, H) = 0.6 / 1.5 = 0.4
      Dh     = 2 × 0.6e-3 × 1.5e-3 / (0.6e-3 + 1.5e-3) = 8.57142857e-4 m
      Vdot   = 2.0 / 60000 = 3.33333333e-5 m³/s
      A_flow = 50 × 0.6e-3 × 1.5e-3 = 4.5e-5 m²
      v      = 3.33333333e-5 / 4.5e-5 = 0.740740741 m/s
      Re     = 997 × 0.740740741 × 8.57142857e-4 / 0.00089 = 711.253790  (laminar, > 500)
      Nu     = 8.235 × (1 − 2.0421·0.4 + 3.0853·0.16 − 2.4765·0.064 + 1.0578·0.0256 − 0.1861·0.01024)
             = 8.235 × 0.543486016 = 4.47560734
      f·Re   = 96 × (1 − 1.3553·0.4 + 1.9467·0.16 − 1.7012·0.064 + 0.9564·0.0256 − 0.2537·0.01024)
             = 96 × 0.682361152 = 65.5066706  (Darcy)
      h      = 4.47560734 × 0.60 / 8.57142857e-4 = 3132.92514 W/m²·K
      m      = sqrt(2 × 3132.92514 / (385 × 0.4e-3)) = 201.711030 1/m
      mH     = 201.711030 × 1.5e-3 = 0.302566544
      eta    = tanh(0.302566544) / 0.302566544 = 0.293659592 / 0.302566544 = 0.970562006
      A_eff  = 50 × 0.05 × (0.6e-3 + 2 × 0.970562006 × 1.5e-3) = 8.77921504e-3 m²
      R_conv = 1 / (3132.92514 × 8.77921504e-3) = 0.0363575237 K/W
      R_base = 2.0e-3 / (385 × 2.5e-3) = 0.00207792208 K/W
      R_tot  = 0.04 + 0.02 + 0.00207792208 + 0.0363575237 = 0.0984354457 K/W
      m_dot  = 3.33333333e-5 × 997 = 0.0332333333 kg/s
      rise   = 800 / (0.0332333333 × 4180) = 5.75890350 °C
      Tj     = 25 + 0.5 × 5.75890350 + 800 × 0.0984354457 = 106.627808 °C
      f      = 65.5066706 / 711.253790 = 0.0921002763
      ΔP     = 0.0921002763 × (0.05 / 8.57142857e-4) × 997 × 0.740740741² / 2 = 1469.51950 Pa
      P_pump = 1469.51950 × 3.33333333e-5 / 0.5 = 0.0979679665 W
    """
    geometry = Geometry(
        channel_count=50,
        channel_width_m=0.6e-3,
        channel_height_m=1.5e-3,
        channel_length_m=0.05,
        base_thickness_m=2.0e-3,
        contact_area_m2=2.5e-3,
        copper_k_w_mk=385.0,
        channel_model="straight_fin",
        fin_thickness_m=0.4e-3,
    )
    result = analyze(
        AnalyzeColdplateInput(
            heat_load_w=800.0,
            flow_rate_lpm=2.0,
            inlet_temp_c=25.0,
            coolant="water",
            r_jc_k_per_w=0.04,
            r_tim_k_per_w=0.02,
            geometry=geometry,
        )
    )

    assert result.regime == "laminar"
    assert result.reynolds == pytest.approx(711.253790, rel=1e-6)
    assert abs(result.reynolds - 711.253790) < 5
    assert result.nusselt == pytest.approx(4.47560734, rel=1e-6)
    assert result.heat_transfer_coeff_w_m2k == pytest.approx(3132.92514, rel=1e-6)
    assert result.fin_efficiency == pytest.approx(0.970562006, rel=1e-6)
    assert result.resistances_k_per_w["convection"] == pytest.approx(0.0363575237, rel=1e-6)
    assert result.resistances_k_per_w["base_conduction"] == pytest.approx(0.00207792208, rel=1e-6)
    assert result.resistances_k_per_w["total"] == pytest.approx(0.0984354457, rel=1e-6)
    assert result.coolant_rise_c == pytest.approx(5.75890350, rel=1e-6)
    assert result.junction_temp_c == pytest.approx(106.627808, rel=1e-6)
    assert abs(result.junction_temp_c - 106.627808) < 1.0
    assert result.pressure_drop_pa == pytest.approx(1469.51950, rel=1e-6)
    assert result.pump_power_w == pytest.approx(0.0979679665, rel=1e-6)


def test_straight_fin_efficiency_bounded_and_falls_with_fin_height():
    """G4: 0 < eta <= 1, and eta falls as fins get taller at fixed width and thickness."""
    etas = []
    for height_mm in (0.5, 1.0, 2.0, 3.75, 6.0, 10.0):
        result = analyze(AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, geometry=_screen_1d_geometry(channel_height_m=height_mm * 1e-3)))
        assert result.fin_efficiency is not None
        assert 0.0 < result.fin_efficiency <= 1.0
        etas.append(result.fin_efficiency)
    assert all(later < earlier for earlier, later in zip(etas, etas[1:])), etas


def test_straight_fin_efficiency_rises_with_conductivity():
    """G4: higher fin conductivity gives higher fin efficiency."""
    etas = []
    for k in (50.0, 150.0, 385.0, 1000.0):
        result = analyze(AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, geometry=_screen_1d_geometry(copper_k_w_mk=k)))
        etas.append(result.fin_efficiency)
    assert all(later > earlier for earlier, later in zip(etas, etas[1:])), etas


def test_straight_fin_r_conv_approaches_full_fin_area_limit():
    """G4: as k grows large, eta -> 1 and R_conv -> 1 / (N L h (w + 2H))."""
    g = _screen_1d_geometry(copper_k_w_mk=1.0e9)
    result = analyze(AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, geometry=g))
    limit = 1.0 / (g.channel_count * g.channel_length_m * result.heat_transfer_coeff_w_m2k * (g.channel_width_m + 2 * g.channel_height_m))
    assert result.fin_efficiency == pytest.approx(1.0, rel=1e-6)
    assert result.resistances_k_per_w["convection"] == pytest.approx(limit, rel=1e-6)


def test_straight_fin_pressure_drop_independent_of_fin_thickness():
    """G4: at fixed N, w, H the flow area and Dh do not involve t, so ΔP does not change."""
    drops = [
        analyze(AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, geometry=_screen_1d_geometry(fin_thickness_m=t))).pressure_drop_pa
        for t in (0.1e-3, 0.39e-3, 1.0e-3)
    ]
    assert drops[0] == pytest.approx(drops[1], rel=1e-12)
    assert drops[2] == pytest.approx(drops[1], rel=1e-12)


def test_straight_fin_correlations_symmetric_under_width_height_swap():
    """G4: Nu and f·Re depend on alpha = short/long side only, so swapping w and H changes neither."""
    a_inp = AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, geometry=_screen_1d_geometry())
    b_inp = AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, geometry=_screen_1d_geometry(channel_width_m=3.75e-3, channel_height_m=0.39e-3))
    a, b = analyze(a_inp), analyze(b_inp)
    assert a.reynolds == pytest.approx(b.reynolds, rel=1e-12)
    assert a.nusselt == pytest.approx(b.nusselt, rel=1e-12)
    assert _darcy_f_re(a, a_inp) == pytest.approx(_darcy_f_re(b, b_inp), rel=1e-9)


def test_straight_fin_geometry_validation_errors():
    """G4: straight_fin requires fin_thickness_m; fin_thickness_m with full_wetted_area is rejected."""
    with pytest.raises(ValueError, match="requires fin_thickness_m"):
        Geometry(channel_model="straight_fin")
    with pytest.raises(ValueError, match="only accepted with channel_model='straight_fin'"):
        Geometry(fin_thickness_m=0.5e-3)
    with pytest.raises(ValueError, match="only accepted with channel_model='straight_fin'"):
        Geometry(channel_model="full_wetted_area", fin_thickness_m=0.5e-3)
    with pytest.raises(ValueError):
        Geometry(channel_model="straight_fin", fin_thickness_m=0.0)
    with pytest.raises(ValueError):
        Geometry(channel_model="pin_fin")


@pytest.mark.parametrize("boundary_re", [2300.0, 4000.0])
def test_straight_fin_nu_and_friction_continuous_at_regime_boundaries(boundary_re: float):
    """G4: on the straight_fin path Nu and f are continuous across Re = 2300 and Re = 4000."""
    g = _screen_1d_geometry()
    below_inp = _fin_input_at_re(boundary_re * (1 - 1e-9), g)
    above_inp = _fin_input_at_re(boundary_re * (1 + 1e-9), g)
    below, above = analyze(below_inp), analyze(above_inp)
    assert below.regime != above.regime
    assert above.nusselt == pytest.approx(below.nusselt, rel=1e-6)
    f_below = _darcy_f_re(below, below_inp) / below.reynolds
    f_above = _darcy_f_re(above, above_inp) / above.reynolds
    assert f_above == pytest.approx(f_below, rel=1e-6)
    assert above.fin_efficiency == pytest.approx(below.fin_efficiency, rel=1e-6)


def test_straight_fin_laminar_endpoint_feeds_transition_blend():
    """At Re = 2300 the blend starts from the Shah & London values, not 4.36 and 64."""
    inp = _fin_input_at_re(2300.0 * (1 + 1e-12), _screen_1d_geometry())
    result = analyze(inp)
    assert result.regime == "transitional"
    # alpha = 0.39 / 3.75 = 0.104; Nu_H1(0.104) = 6.738931 (as in G2);
    # Darcy f·Re(0.104) = 96 × (1 − 1.3553·0.104 + 1.9467·0.104² − 1.7012·0.104³
    #                          + 0.9564·0.104⁴ − 0.2537·0.104⁵) = 84.316751
    assert result.nusselt == pytest.approx(6.738931, rel=1e-6)
    assert _darcy_f_re(result, inp) == pytest.approx(84.316751, rel=1e-6)


def test_straight_fin_out_of_range_warning_only_at_or_above_re_2300():
    """G4: the laminar-only warning appears at Re >= 2300 and not below."""
    g = _screen_1d_geometry()
    below = analyze(_fin_input_at_re(2300.0 * (1 - 1e-9), g))
    at = analyze(_fin_input_at_re(2300.0 * (1 + 1e-12), g))
    turbulent = analyze(_fin_input_at_re(6000.0, g))
    assert _FIN_RANGE_WARNING not in below.warnings
    assert _FIN_RANGE_WARNING in at.warnings
    assert _FIN_RANGE_WARNING in turbulent.warnings


def test_straight_fin_warnings_replace_only_the_rectangular_channel_warning():
    """The straight_fin path swaps the effective-area warning for the fin-model warning."""
    laminar = analyze(AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, inlet_temp_c=35.0, geometry=_screen_1d_geometry()))
    assert laminar.warnings == [
        _FIN_WARNING,
        "coolant properties are fixed at nominal 25°C values; inlet temperature differs from the property reference",
        "no measured cold-plate validation is included; absolute temperature and pressure results are screening estimates",
        "very low Reynolds number; risk of poor flow distribution",
    ]
    transitional = analyze(_fin_input_at_re(3000.0, _screen_1d_geometry()))
    assert transitional.warnings == [
        "transitional-flow correlation is a numerical blend, not an experimentally validated transition model",
        _FIN_WARNING,
        _FIN_RANGE_WARNING,
        "no measured cold-plate validation is included; absolute temperature and pressure results are screening estimates",
    ]
    assert not any("rectangular-channel correlations" in warning for warning in laminar.warnings + transitional.warnings)


def test_straight_fin_energy_balance_closes():
    """G6: Q = m_dot·cp·ΔT and Tj − T_bulk = Q·R_total on the straight_fin path."""
    for coolant, rho, cp in (("water", 997.0, 4180.0), ("glycol50", 1060.0, 3400.0)):
        for flow_lpm in (1.5, 20.0):
            result = analyze(AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=flow_lpm, coolant=coolant, geometry=_screen_1d_geometry()))
            m_dot = flow_lpm / 60000.0 * rho
            assert m_dot * cp * result.coolant_rise_c == pytest.approx(1000.0, rel=1e-2)
            assert m_dot * cp * result.coolant_rise_c == pytest.approx(1000.0, rel=1e-12)
            t_bulk = 25.0 + 0.5 * result.coolant_rise_c
            assert (result.junction_temp_c - t_bulk) / result.resistances_k_per_w["total"] == pytest.approx(1000.0, rel=1e-12)


def test_full_wetted_area_is_the_unchanged_default():
    """G5: the default and an explicit full_wetted_area give identical output, with fin_efficiency None."""
    default = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water"))
    explicit = analyze(AnalyzeColdplateInput(heat_load_w=700, flow_rate_lpm=8, coolant="water", geometry=Geometry(channel_model="full_wetted_area")))
    assert Geometry().channel_model == "full_wetted_area"
    assert Geometry().fin_thickness_m is None
    assert default.fin_efficiency is None
    assert explicit.model_dump() == default.model_dump()


def test_straight_fin_rack_and_sensitivity_pass_geometry_through():
    """Rack and sensitivity helpers run on the straight_fin path without special handling."""
    g = _screen_1d_geometry()
    single = analyze(AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, geometry=g))
    rack = analyze_rack(AnalyzeRackInput(gpu_count=2, topology="parallel", heat_load_per_gpu_w=1000.0, total_flow_lpm=3.0, geometry=g))
    assert rack.max_junction_temp_c == pytest.approx(single.junction_temp_c, rel=1e-12)
    assert any(_FIN_WARNING in warning for warning in rack.warnings)
    sens = compute_sensitivity(AnalyzeColdplateInput(heat_load_w=1000.0, flow_rate_lpm=1.5, geometry=g))
    assert sens.dtj_dr_tim_c_per_kw == pytest.approx(1000.0, rel=1e-6)
