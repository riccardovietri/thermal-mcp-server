# Agent Notes — thermal-mcp-server

Living document for AI coding agents. Updated each session. Summarizes work done,
decisions made, and queued tasks so future agents can orient quickly.

*Last updated: 2026-03-27*

---

## Current state

All planned sprint work is merged to main. The repo is portfolio-ready.

**Merged (PRs 11–20):**

| PR | Content |
|----|---------|
| PR11 / PR13 | Rack-level model (`analyze_rack`, series + parallel, hand-calc validated) |
| PR14 | MCP test completeness (44 tests) + daily regression CI |
| PR15 | Sensitivity output + `margin_c` for `optimize_flow_rate` |
| PR16 / PR19 | CI fixes: physics-aware review prompt, auto-review-response workflow, guarded daily regression |
| PR17 | Portfolio examples (H100/B200/MI300X/Gaudi 3 benchmarks, rack topology, AI factory budget) |
| PR20 | Docs polish: README rewrite (NVL72 lead), 3-section notebook, PORTFOLIO.md, ValidationError fix in `analyze_rack_impl` |

---

## Priority queue

### 1. Personal site (highest visibility ROI)

Make the project discoverable outside GitHub.

- One-page structure: bio / featured project / contact
- Featured project framed as: "I built an AI-native tool that lets engineers size CDUs from
  first principles — from single cold plate hydraulics to full NVL72 rack specs."
- Link to `examples/interactive_sizing.ipynb` ("Open in Colab" — badge already in README)
- Tech: Astro + Tailwind on Netlify or Vercel

### 2. PR benchmark diff in CI (medium effort, high signal)

On every PR opened against main, run `examples/real_chip_benchmarks.py` and post
the output as a PR comment. Forces each PR author to see if their change moved
real-world thermal outputs (H100 Tj, B200 min flow). Add as a step in `ci.yml`.

### 3. ROI calculator (separate repo — see `docs/decisions.md`)

Financial layer: annual cooling cost delta, CDU payback, per-GPU cooling tax.
Decided in `docs/decisions.md`: lives in a separate package (`thermal-roi-calculator`),
not in this repo. Different update cadence; different target user.

---

## Physics change protocol

Before marking any physics change done:
1. Units consistent (resistance calcs in Kelvin, I/O in Celsius)
2. Dimensional analysis passes
3. Energy balance closes: `Q_input ≈ m_dot × cp × ΔT_coolant`
4. `docs/physics.md` updated with justification
5. Hand-calc test added or updated in `tests/test_physics_behavior.py`
6. `pytest` passes — no tolerance relaxation

---

## Files locked against casual change

- `tests/test_physics_behavior.py` — do not weaken numerical tolerances
- `src/thermal_mcp_server/physics.py` constants (COOLANTS dict, pump efficiency = 0.50)
- Key defaults in `schemas.py` (channel geometry, contact_area, copper_k)

Canonical default: 700 W, 8 LPM, water, 25°C → Tj ≈ 70.9°C. Appears in README,
checked in `test_hand_calc_validation_default_case`. Must remain correct.
