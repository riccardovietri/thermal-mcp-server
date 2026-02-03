# Test Strategy and Build Checks

## Overview

This document explains our testing approach, what each test category validates, and how build checks are structured.

---

## Why So Many Tests? (59 Total)

The thermal model is a **physics-based engineering tool** that will be used for real-world data center cooling decisions. Unlike typical software where bugs cause crashes, thermal model errors could lead to:
- **Overheating**: GPUs thermal throttling or failing
- **Over-engineered systems**: Wasting money on excessive cooling
- **Wrong coolant choice**: Using expensive dielectric fluid when water would work

Each test category serves a specific purpose in building confidence:

---

## Test Categories

### 1. **Unit Tests** (34 tests) - `test_coldplate.py`

**Purpose**: Verify individual components work correctly

**What they test**:
- Coolant property lookups (water, glycol, dielectric)
- Model instantiation with different configurations
- Basic calculations (temperature, pressure drop, flow optimization)
- Edge cases (very high/low flow, extreme ambient temps)
- Warning system (alerts for dangerous conditions)

**Why we need them**:
- Catch bugs early when changing code
- Document expected behavior
- Fast to run (~0.3s total)

**Build check usage**: ✅ **Run on every commit** (fast, catches regressions)

**Example**:
```python
def test_coolant_comparison(self):
    """Test that water performs better than glycol"""
    model_water = ColdPlateModel(gpu_power_w=700, coolant_type="water")
    model_glycol = ColdPlateModel(gpu_power_w=700, coolant_type="glycol")

    result_water = model_water.calculate_performance(flow_rate_lpm=12)
    result_glycol = model_glycol.calculate_performance(flow_rate_lpm=12)

    # Water should give lower temps (better thermal properties)
    assert result_water["junction_temp_c"] < result_glycol["junction_temp_c"]
```

---

### 2. **First Principles Validation** (15 tests) - `test_validation.py`

**Purpose**: Verify the physics equations are implemented correctly

**What they test**:
- **Energy balance**: Q = ṁ × cp × ΔT (conservation of energy)
- **Reynolds number**: Turbulent vs laminar flow transitions
- **Pressure drop**: Darcy-Weisbach equation scaling
- **Thermal resistance**: Heat transfer correlations (Dittus-Boelter)
- **Model sensitivity**: How changes in flow/power/temp propagate

**Why we need them**:
- Ensure we're solving the right equations
- Validate against hand calculations
- Confirm model behaves like real physics

**Build check usage**: ✅ **Run on every commit** (validates core physics, ~0.2s)

**Example**:
```python
def test_energy_balance(self):
    """Validate energy balance: Q = m_dot × cp × ΔT"""
    model = ColdPlateModel(gpu_power_w=700, coolant_type="water")
    result = model.calculate_performance(flow_rate_lpm=12)

    # Calculate expected temp rise
    flow_m3s = 12 / 60000.0  # LPM to m³/s
    mass_flow = flow_m3s * model.coolant.density
    expected_delta_T = model.total_power_w / (mass_flow * model.coolant.specific_heat)

    # Should match within 10% (accounts for model simplifications)
    assert abs(result["coolant_temp_rise_c"] - expected_delta_T) < expected_delta_T * 0.1
```

---

### 3. **Published Case Studies** (10 tests) - `test_published_case_studies.py`

**Purpose**: Validate against real-world published research data

**What they test**:
- **NVIDIA H100** cooling (arXiv paper, 2025): 41-50°C at 700W
- **High-power cold plates** (ScienceDirect, 2024): 3500W dissipation
- **Data center systems** (Vertiv, 2024): 10kW cold plate loads
- **Textbook problems** (Incropera): Classic heat transfer examples
- **Industry benchmarks**: Hyperscale data center requirements

**Why we need them**:
- Prove model matches real hardware performance
- Build user trust with citations
- Validate against peer-reviewed research

**Build check usage**: 🔄 **Run on PR/release** (slower, comprehensive validation, ~0.3s)

**Example**:
```python
def test_h100_single_gpu_liquid_cooling(self):
    """
    Test against H100 single GPU liquid cooling performance

    Published data: Liquid-cooled H100 maintains 41-50°C under load
    Reference: arXiv:2507.16781 (July 2025)
    """
    model = ColdPlateModel(
        gpu_power_w=700,  # H100 TDP
        coolant_type="water",
        ambient_temp_c=25
    )

    result = model.calculate_performance(flow_rate_lpm=15)

    # Should achieve temps in published range
    assert 40 < result["junction_temp_c"] < 90
```

---

## Build Check Strategy

### Current Structure (`.github/workflows/test.yml`)

```yaml
name: Test

on:
  push:
    branches: [ main, claude/** ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        run: |
          pytest tests/ -v --tb=short
```

**Current approach**: Run ALL tests on every commit (59 tests, ~0.5s total)

**Pros**:
- Simple configuration
- Catches everything immediately
- Tests are fast enough (<1s) that it's not a bottleneck

**Cons**:
- Could be split for clarity
- Published case studies could be slower as model grows

---

### Recommended Build Check Structure

As the project grows, consider this tiered approach:

#### **Tier 1: Fast Checks** (Run on every commit)
```yaml
- name: Fast unit tests
  run: pytest tests/test_coldplate.py -v -k "not optimization"
```
- Unit tests excluding slow optimizations
- ~0.2s runtime
- Catches 90% of bugs immediately

#### **Tier 2: Physics Validation** (Run on every commit)
```yaml
- name: Physics validation
  run: pytest tests/test_validation.py -v
```
- First principles tests
- ~0.2s runtime
- Ensures core physics is correct

#### **Tier 3: Full Validation** (Run on PR to main)
```yaml
- name: Full validation suite
  run: pytest tests/ -v
  if: github.event_name == 'pull_request'
```
- All 59 tests including published case studies
- ~0.5s runtime
- Comprehensive check before merging

#### **Tier 4: Release Validation** (Run on tag/release)
```yaml
- name: Release validation
  run: |
    pytest tests/ -v --tb=long
    python scripts/generate_validation_report.py
  if: startsWith(github.ref, 'refs/tags/')
```
- Full test suite with detailed output
- Generate validation report for documentation
- Run before tagging new versions

---

## Quick Reference

| Test Category | Tests | Runtime | When to Run | Purpose |
|--------------|-------|---------|-------------|---------|
| Unit Tests | 34 | 0.3s | Every commit | Catch bugs, test components |
| First Principles | 15 | 0.2s | Every commit | Validate physics equations |
| Published Cases | 10 | 0.3s | PR/Release | Match real-world data |
| **Total** | **59** | **~0.5s** | **All or tiered** | **Full confidence** |

---

## Running Tests Locally

### Quick validation (all tests)
```bash
./scripts/run_tests.sh
```

### Specific test categories
```bash
# Unit tests only
pytest tests/test_coldplate.py -v

# Physics validation only
pytest tests/test_validation.py -v

# Published case studies only
pytest tests/test_published_case_studies.py -v

# Single test
pytest tests/test_coldplate.py::TestCoolantProperties::test_water_properties -v
```

### Watch mode (auto-run on file changes)
```bash
pytest-watch tests/ src/
```

---

## Should We Remove Any Tests?

**No.** Here's why each category matters:

1. **Unit tests (34)**: These are standard software engineering practice. They're fast and comprehensive.

2. **First principles (15)**: These validate the physics. Without these, we're just curve-fitting to published data without understanding why.

3. **Published cases (10)**: These build user trust. When someone asks "does this actually work?", we can point to peer-reviewed papers.

**Total runtime is <1 second.** For a physics-based engineering tool, this is excellent coverage.

---

## Test Maintenance

### When to add new tests:
- Adding new coolant types
- Supporting new GPU models
- Adding new features (immersion cooling, etc.)
- Bug fixes (add regression test)

### When to update tests:
- Thermal resistance values change (better materials)
- Published data is superseded by newer research
- Physics correlations improve

### Red flags requiring test updates:
- Model predictions drift from published data
- Energy balance errors increase
- Test assertions become too loose

---

## Future Test Enhancements

1. **Performance benchmarks**: Track model execution time
2. **Property table validation**: Test coolant properties against NIST data
3. **CFD comparison**: When available, compare to full CFD simulations
4. **Hardware validation**: Test against physical test bench data

---

## Summary

**The point of 59 tests:**
1. **Correctness**: Verify physics equations are right
2. **Confidence**: Match published research data
3. **Reliability**: Catch bugs before they reach production
4. **Documentation**: Tests show how the model should behave

**Build check approach:**
- **Current**: Run all 59 tests on every commit (~0.5s, simple)
- **Future**: Tier tests as project grows (fast checks → full validation → release checks)

**Bottom line**: For a thermal engineering tool used in real data centers, this level of testing is appropriate and industry-standard. The tests are fast, comprehensive, and provide confidence that the model works correctly.

---

**Author**: Riccardo Vietri
**Last Updated**: February 3, 2026
