# Strategy: Portfolio Roadmap and ROI Calculator Decision

*Written March 2026. Revisit before starting major new work.*

## Where the project stands

The physics engine is credible: correct rectangular-channel Dh, hand-calc validated
tests, documented assumptions, and real chip specs. The MCP integration is clean.
`examples/real_chip_benchmarks.py` is the strongest piece — it answers real
engineering questions with cited numbers.

The project is portfolio-presentable now for roles that want to see:
- Physics-backed engineering tooling in Python
- MCP / AI tool integration
- Professional documentation habits

It is not yet portfolio-impressive for senior data center thermal roles, which would
expect rack-level analysis and uncertainty-aware outputs.

---

## Top 3 portfolio gaps (audit, March 2026)

### Gap 1: Single cold plate is the wrong unit of analysis (HIGH)

The tool models one cold plate in isolation. Real engineering decisions at
H100/B200/NVL72 scale are rack-level: manifold ΔP, CDU sizing, outlet temperature
to the cooling tower. A hiring manager at a data center company will immediately
ask "can it model a rack?" — the answer is currently no.

**Fix:** Add `analyze_rack(gpu_count, topology, flow_per_gpu_lpm, ...)` returning
`(total_dp_pa, max_tj_c, cdu_outlet_temp_c, total_pump_power_w)`. Series topology:
ΔP_total = N × ΔP_single, T_in_n = T_in_{n-1} + coolant_rise_{n-1}. Parallel:
ΔP_total = ΔP_single (manifold assumed balanced), flow_per_gpu = total / N.
Roughly 60 lines of new physics in `physics.py`.

### Gap 2: Results are falsely precise (MEDIUM)

`junction_temp_c: 70.9` looks authoritative. Manufacturing reality:
- R_jc: ±20% variation lot-to-lot
- TIM resistance: 2–3× increase over operating life (pump-out)
- Channel maldistribution: ±30% local flow variation
- Constant fluid properties: ~3–5°C error at high load

A model a thermal engineer trusts would return `(tj_mean, tj_p95)` from a Monte
Carlo sweep, or at minimum sensitivity coefficients: ∂Tj/∂Q, ∂Tj/∂R_tim,
∂Tj/∂T_inlet. Currently `optimize_flow_rate` returns a single minimum flow with
no safety margin — a real deployment engineer wants flow for Tj_p95 < 83°C.

**Fix:** Add optional `sensitivity=True` flag to `analyze()` that returns
partial derivatives via finite difference. Add `optimize_flow_rate` with
`margin_c` parameter (default 3°C) that targets `max_junction_temp_c - margin_c`.

### Gap 3: MCP tool tests are smoke tests (LOW — easy fix)

`test_mcp_tools.py` has 3 tests that only check key presence. Missing:
- Error path: `analyze_coldplate_impl(heat_load_w=-1)` → `{"error": [...]}`
- `optimize_flow_rate_impl` with infeasible target → `met_target: False`
- `compare_coolants_impl` result depth check
- Geometry passthrough: non-default geometry propagates through MCP layer

20-minute fix. High signal for code reviewers.

---

## Recommended next PR sequence

```
PR9 (current: claude/pre-publish-fixes-UnOXt)
  ✓ Merge first — rectangular channel fix, PyPI metadata, CLAUDE.md
  Status: ready

PR10: MCP test completeness (Gap 3)
  Small, standalone, no physics changes. Good first PR after merge.

PR11: Rack-level model (Gap 1)
  New tool: analyze_rack. Needs hand-calc validation test.
  Also enables the NVL72 validation target from README roadmap.

PR12: Sensitivity output (Gap 2)
  Adds uncertainty surface to existing analyze() output.
  Consider whether to expose via MCP or only Python API.
```

---

## ROI Calculator: architecture and open questions

### What it is

A layer above the thermal physics that converts engineering outputs (ΔP, pump
power, Tj margin) into financial outcomes (OpEx savings, payback period, NPV).
This answers the actual procurement question: "Should I retrofit liquid cooling?"

### Architecture

```
ROI Layer (new)
  roi_analyze(gpu_count, rack_count, electricity_usd_kwh,
              baseline_pue, liquid_pue, cdu_capex_usd_per_rack,
              amortization_years=5, gpu_utilization=0.75)
  → annual_savings_usd, payback_months, npv_usd,
    break_even_electricity_price, per_gpu_cooling_tax_pct,
    cdu_spec{flow_lpm, heat_rejection_kw, max_dp_bar}
        │
        ▼
Rack Layer (Gap 1, above)
  analyze_rack(gpu_count, topology, flow_per_gpu_lpm, ...)
  → total_dp_pa, max_tj_c, cdu_outlet_temp_c, total_pump_power_w
        │
        ▼
thermal_mcp_server (existing)
  analyze_coldplate × N, optimize_flow_rate
```

### Key financial inputs

| Input | Typical range | Why it matters |
|-------|--------------|----------------|
| electricity_usd_kwh | $0.04–$0.28 | Biggest lever on savings |
| baseline_pue | 1.4–1.6 | Retrofitted air-cooled data center |
| liquid_pue | 1.03–1.15 | CDU (1.03–1.08) vs rear-door (1.10–1.15) |
| cdu_capex_usd_per_rack | $15k–$80k | Drives payback period |
| gpu_utilization | 0.6–0.85 | Actual load vs TDP nameplate |

### Key financial outputs

- `annual_cooling_kwh_saved` — (baseline_pue − liquid_pue) × total_tdp_kw × 8760h × utilization
- `annual_savings_usd` — direct dollar value of reduced cooling overhead
- `payback_months` — cdu_capex / monthly_savings
- `npv_usd` — at 10% discount rate over amortization period
- `break_even_electricity_usd_kwh` — below what price does liquid not pencil?
- `per_gpu_cooling_tax_pct` — pump power as % of GPU TDP (water: 1–3%, glycol: 5–12%)
- `cdu_spec` — procurement input: flow LPM, kW rejection, max ΔP bar

### Open question: same repo or separate?

**Arguments for same repo (thermal-mcp-server extension):**
- ROI layer calls the physics directly — tight coupling by design
- One install, one MCP server, three new tools: `analyze_rack`, `roi_analyze`, `size_cdu`
- Simpler discovery: one PyPI package does everything
- Portfolio benefit: shows the project growing coherently

**Arguments for separate repo/service:**
- ROI calculator has different update cadence (electricity prices, CDU vendor specs)
- May want a web UI front-end (separate deploy concern from a Python package)
- Different target user: CFO/VP wants a web app; engineer wants a Python library
- Avoids scope creep that blurs what `thermal-mcp-server` is

**Recommendation:** Add `analyze_rack` to this repo (it's pure physics, belongs here).
Keep the ROI financial layer separate — either as a second package
(`thermal-roi-calculator`) or as a web app that imports `thermal_mcp_server.physics`
as a dependency. Decide when you have a clear target user in mind (engineer vs.
business stakeholder).

---

## Live demo web app spec

If/when pursuing the web demo, minimum viable stack:

**Backend:** FastAPI, calling `thermal_mcp_server.physics` directly (bypass MCP
protocol for web — adds latency and complexity with no benefit)

**Frontend:** HTMX (reactive slider/input updates → server → partial HTML), Tailwind

**Charts:** Plotly.js — server returns JSON traces, client renders

**Deploy:** Fly.io or Railway, single Docker container, ~$5/month

### Inputs (one screen, no page navigation)

1. GPU selector (H100 SXM / B200 NVL72 / MI300X / Gaudi 3)
2. GPUs per rack (slider: 4–72)
3. Flow rate per cold plate (slider: 2–15 LPM)
4. Inlet temperature (slider: 20–45°C)
5. Coolant (toggle: water / glycol50)
6. Electricity cost $/kWh (input with presets: US West / US East / EU / APAC)

### Outputs (live-updating on any change)

| Output | Format |
|--------|--------|
| Junction temperature | Large number + margin bar (green/yellow/red) |
| Thermal margin to throttle | Degrees, with 3°C warning band |
| Pump power % of TDP | Progress bar ("cooling tax") |
| CDU spec | flow LPM / rejection kW / max ΔP bar |
| Annual electricity saved vs. air | MWh and USD |
| Payback period | Months, with CDU capex slider |

**The one chart that makes it:** Tj vs. flow rate, one curve per inlet temperature
(20/25/30/35/40°C). This is the chart thermal engineers currently generate in MATLAB
or Excel. Rendering in <200ms from a slider drag is the demo moment.

**The portfolio-differentiating feature:** "Export Technical Brief" button — a 1-page
PDF (reportlab or weasyprint) with key numbers, assumptions box, and the Tj chart.
This is the artifact you hand to a procurement team. No other open-source thermal
tool generates this.

---

## What not to build (yet)

- Temperature-dependent fluid properties — adds complexity, <5°C improvement at
  typical operating points. Not worth it until rack model is validated.
- Boiling/two-phase — completely different physics regime. Out of scope unless
  explicitly targeting immersion cooling.
- Transient RC network — valuable for control studies but not for procurement
  decisions. Add only if a specific use case demands it.
- Web scraping current GPU prices / electricity rates — maintenance burden,
  fragile, not the differentiator.
