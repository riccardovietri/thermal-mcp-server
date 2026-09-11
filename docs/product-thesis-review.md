# Thermal systems decision engine: product thesis review

## 1. Executive assessment

**Adopt the thesis, but narrow the first product to auditable, steady-state screening of identical liquid-cooled GPU branches and racks.** The repository has a useful engineering library and the beginnings of a decision workflow. It does not yet justify an authoritative operating recommendation or a complete CDU requirement.

The strongest proposition is: **given explicit component evidence and operating constraints, determine whether a proposed cooling architecture has enough thermal and hydraulic margin, and identify what must be validated next.** Transparent equations are necessary; trustworthy constraint handling, evidence provenance, and honest abstention should become the differentiator.

Today a competent engineer can use it for conditional thermal estimates, energy balances, idealized topology comparisons, and preliminary flow screening. They should independently review inputs and correlations, and obtain vendor curves before selecting hardware. The most challengeable output is the decision memo's “recommended operating point” and “risk” assessment: these look more authoritative than their derivation supports.

If MCP disappeared, the Python model, tests, and examples would retain value. Their compelling reason to exist beyond a personal notebook is still emerging. Build that reason through credible engineering decisions, not additional interfaces. Success can be a small group of sophisticated engineers repeatedly using and reviewing one defensible workflow.

**Review basis:** local commit `2a57406de183a9ef1ff594418d5c539b0474d586`, inspected September 10, 2026; no claim that this is the latest remote state. Three GPT‑5.6 Luna/high reviews informed this document; the parent agent checked their conclusions against source and runtime probes. Recommendations are proposals, not accepted roadmap decisions. Only this document is changed.

**Verification:** all 75 repository tests passed; the sizing notebook passed `pytest --nbmake` after installing the declared demo dependencies and permitting local kernel sockets. Read-only probes reproduced the report behaviors below. These checks establish execution and current behavior, not physical accuracy.

## 2. What the project is today

The architecture already broadly matches the thesis: deterministic calculations in [physics.py](../src/thermal_mcp_server/physics.py), synthesis in [decision_report.py](../src/thermal_mcp_server/decision_report.py), typed contracts in [schemas.py](../src/thermal_mcp_server/schemas.py), and wrappers in [mcp_server.py](../src/thermal_mcp_server/mcp_server.py). However, “first principles” needs qualification: conservation laws are combined with empirical correlations and assumed package resistances.

### Capability map

Classification indicates present product role: **Core** directly supports the thesis; **Supporting** enables credible use; **Commodity** is necessary plumbing; **Distracting** pulls outside scope; **Incomplete** promises a decision it cannot yet fully support. Maturity describes implementation, not measured accuracy.

| Capability / engineering question | Layer | Maturity and classification |
|---|---|---|
| Resistance network and coolant heat pickup: what junction temperature and temperature rise follow from these inputs? | Physics | Working, equation-checked; **Core**. Absolute accuracy remains conditional on resistance and geometry assumptions. |
| Channel hydraulics and pump-power estimate: what cold-plate pressure drop accompanies this flow? | Physics | Working approximation; **Core** for component screening, incomplete for system sizing. |
| Identical series/parallel racks: how do inlet heating, branch flow, and pressure aggregation change? | Physics | Tested limiting topologies; **Core** within this narrow boundary. |
| Minimum-flow search with thermal guardband: what flow meets a temperature target? | Physics/search | Working single-plate thermal search; **Core**. No pressure or pump constraint. |
| Heat-load, TIM, and inlet sensitivities: how much does temperature move? | Physics | Analytically checked local derivatives; **Supporting**. Fixed resistance/aging perturbations are scenarios, not validated uncertainty distributions. |
| Water/glycol comparison: what changes at equal volumetric flow? | Interface composition over physics | Working two-fluid comparison; **Supporting**. Does not establish a preferred coolant under common pump limits. |
| Decision memo, flow band, risk, topology rationale: what should I operate and trust? | Decision | Integrated and tested, but materially heuristic; **Incomplete**. Central future differentiator. |
| Schemas, units, validation, error envelopes: can callers form repeatable requests? | Shared contracts/interfaces | Established, uneven semantics; **Commodity**. Missing provenance and validity states affect decisions. |
| Python API: can engineers compose analyses without an agent? | Interface | Runnable and exercised by tests/examples; **Supporting**. |
| Five MCP tools and in-memory client: can an agent discover and execute deterministic analysis? | Interface | Contract-tested and runnable; **Commodity**, with useful integration reach. |
| Quickstart, rack studies, sizing notebook, decision examples: can engineers inspect tradeoffs? | Interface/examples | Runnable scaffolding; **Supporting**. Multiple studies do not yet form one canonical decision record. |
| Hand calculations, behavior/contract tests, CI: can changes preserve intended mathematics and transport? | Verification infrastructure | Established regression protection; **Supporting**. Not experimental validation. |
| Public chip reference cases: can users explore plausible accelerator scenarios? | Evidence/examples | Power/limit source labels plus geometry/resistance proxies; **Supporting**. “Benchmark” overstates validation if read as measured agreement. |
| Command-line module entry point: can I run a sizing command? | Interface | Starts MCP; a standalone engineering CLI is **Incomplete** and unnecessary for the first milestone. |
| Archived cooling-cost example: what is the financial outcome? | Outside product boundary | Already in `_attic/`; **Distracting** to revive here. |

Evidence anchors: physics functions at lines 40–331; schemas at lines 14–277; MCP implementations at lines 30 onward; [examples](../examples/); [CI](../.github/workflows/ci.yml). Financial separation is already a durable [decision](decisions.md).

### Workflow assessment

1. **Define architecture:** geometry, resistances, coolant, heat, count, and pure series/parallel topology are expressible. Missing are input provenance, mixed branch arrangements, and real hydraulic limits.
2. **Evaluate thermal performance:** single-plate and rack temperatures are available, but callers must judge correlation applicability and distinguish estimated package inputs from measurements.
3. **Evaluate hydraulics:** component/rack APIs return cold-plate-only pressure and assumed-efficiency pump power. The decision report drops these outputs; complete CDU sizing breaks here.
4. **Check feasibility:** single-plate thermal search works conditionally. Rack-wide search and joint thermal/hydraulic feasibility are absent; a report failure does not establish architecture infeasibility.
5. **Explore sensitivities:** local thermal perturbations exist. There is no ranked, caller-bounded analysis of flow, geometry, hydraulic losses, or combined rack degradation.
6. **Compare alternatives:** coolant and topology comparisons exist, with manual sweeps in examples. No shared constraint/evidence table ensures comparisons use the same objective and boundary conditions.
7. **Receive a recommendation:** a readable memo exists; the flow band and risk labels need stronger semantics and derivation.
8. **Understand blind spots:** reports include a static limitation list. It does not rank decision-specific missing evidence or prescribe the next measurement.

An engineer still reaches for Excel/MATLAB to reconcile budgets and scenario tables, vendor data for resistance/pressure curves and limits, and CFD for spatial effects. The opportunity is to make that reconciliation and validation handoff reproducible.

## 3. Where it is strongest

The model exposes intermediate quantities—Reynolds number, Nusselt number, heat-transfer coefficient, resistance breakdown, coolant rise, pressure drop—rather than returning an unexplained temperature. That is a strong foundation for auditability. Energy balance and idealized series/parallel composition are easy to inspect independently.

The software separation is useful: one physics implementation serves Python, notebooks, and MCP. The tests protect numerical behavior, transport errors, geometry propagation, infeasible optimization, and rack-aware memo checks. [Physics tests](../tests/test_physics_behavior.py), [decision tests](../tests/test_decision_report.py), and [MCP tests](../tests/test_mcp_tools.py) are more valuable than a larger tool catalog.

The baseline itself demonstrates why explicit assumptions matter. At 700 W, 8 LPM water, and 25°C inlet, the current model returns approximately **70.9°C, 16.8 kPa, and Re 3,734**. Package plus TIM resistance contributes **42°C** of rise and about **93% of the total resistance**. Improving the estimate of those inputs may matter more than polishing channel optimization. This is a model decomposition, not a measured claim about an H100.

### Differentiation assessment

| Alternative | Present advantage and remaining obligation |
|---|---|
| Spreadsheet | Typed requests, repeatable calculations, tests, and shared reports reduce formula drift. A good spreadsheet can still make the same decisions; provenance and constrained comparisons must improve. |
| Python resistance script | Rack composition, validation, sensitivity, and reporting save integration work. The underlying equations alone are not distinctive. |
| Jupyter notebook | A reusable tested engine separates calculation from presentation. Keep the notebook as an inspection surface; make decisions reproducible outside its cell state. |
| Existing thermal calculators | Packaging several steps helps, but correlation coverage is not a defensible uniqueness claim. EES already exposes rectangular-duct routines with aspect ratio, development length, and boundary-condition treatment. [EES documentation](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1122.htm) |
| CFD | Low input burden, speed, and traceability suit architecture screening. Spatial temperature/flow fields and detailed conjugate heat transfer remain reasons to use CFD; Ansys explicitly demonstrates temperature and pressure-drop sweeps for cold plates. [Ansys example](https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/discovery_tech_show/Discovery/tech_show/trans_cold_plate_flusoltherm/c_cold_plate_prologue.html) |
| Generic LLM + Python | Versioned deterministic functions and tested contracts constrain invented calculations. The remaining advantage must be disciplined evidence and abstention, not fluent prose around familiar equations. |

These are workflow comparisons, not a comprehensive competitor survey. **The decision layer adds integration value today, but insufficient engineering judgment to be the differentiator yet.**

## 4. Where it lacks credibility

### Recommendation semantics can mislead even when equations execute correctly

Runtime probes reproduced these behaviors with otherwise default `DecisionScenario` inputs:

| Probe | Observed result | Engineering consequence |
|---|---|---|
| `flow_rate_lpm=8` | Report evaluates a recommended 9.2 LPM, calls 8 the minimum, and reports LOW risk with 12.72°C margin while listing a +14°C TIM scenario. | Fixed input is changed; minimum is unproven; risk ignores its own stress scenario. |
| `gpu_count=8, topology="series"` | Report says infeasible at 6.324 LPM and 84.8°C. Direct rack evaluation at 12 LPM gives 75.58°C, below the 78°C effective target. | Failure at a selected point is not proof that no flow works. This counterexample establishes thermal feasibility only. |
| `heat_load_w=1200, target_junction_temp_c=75` | Failed 0.5–60 LPM search produces a 60/69/90 LPM “minimum/recommended/maximum” band. | No feasible minimum exists; the suggested point exceeds the search ceiling. |
| `gpu_count=256, topology="series"` | Accepted rack input drives downstream coolant past the 80°C bound; report returns infeasible but fills temperature/margin with single-plate values: 73.64°C and +9.36°C. | Placeholder numbers can be mistaken for computed rack results. |

See [decision_report.py](../src/thermal_mcp_server/decision_report.py), lines 201–288. The 1.15/1.50 flow multipliers and 5/10°C risk thresholds are explicit software rules, not justified operating envelopes (lines 38–40, 290–313). Supply temperature is echoed as “recommended”; topology is explained at equal per-GPU flow rather than selected under a common system constraint. At that comparison basis, ideal cold-plate-only series and parallel pump powers are equal: one uses N times pressure, the other N times flow. Real differences require additional evidence.

The uncertainty section uses single-plate sensitivity even for series racks, omitting additional downstream heat-pickup sensitivity. Its renderer puts ± signs on one-sided aging and positive stress changes (lines 147–154). Neither scenario probability nor combined uncertainty is established.

### Model fidelity and validation boundaries

**Verification is stronger than validation.** The hand calculation at 10 LPM checks the implemented thermal relationship; rack tests check aggregation, often against the same single-plate function. The default pressure assertion spans 1–100 kPa rather than independently checking Darcy–Weisbach. There is no measured cold-plate/rack dataset in the documented evidence boundary. Public TDP and temperature-limit inputs do not validate predicted temperatures or pressure drops. See [tests, lines 47–229](../tests/test_physics_behavior.py) and [public-spec provenance](public_specs.md).

The universal laminar `Nu=4.36` and `f=64/Re` do not establish accuracy for arbitrary rectangular channels. Aspect ratio, heating boundary, and developing flow matter; the [EES rectangular-duct reference](https://fchart.com/ees/heat_transfer_library/internal_flow/hs1122.htm) treats these explicitly. A linear transition blend provides numerical continuity, not experimental validation. The default point lies inside that blend, and the code applies its turbulent expression above Re 4,000 without an explicit applicability check.

Using the full wetted perimeter as effective heated area assumes side/top wall effectiveness without fin-efficiency or conjugate-conduction treatment. Independent positive geometry fields do not ensure a physically realizable channel layout. No spreading model supports hotspot prediction, and average coolant temperature plus lumped resistances cannot resolve local die temperatures. These limitations especially constrain geometry optimization. See [physics.py](../src/thermal_mcp_server/physics.py), lines 54–112, and [Geometry](../src/thermal_mcp_server/schemas.py), lines 14–31.

Properties remain fixed at nominal 25°C, despite inputs spanning −20 to 80°C. Schema acceptance is not a liquid-phase or correlation-validity guarantee. Reports misleadingly describe properties as nominal at the inlet; lower-level warnings cover only high junction temperature and very low Reynolds number. An 85°C generic warning cannot substitute for a caller's component limit. Missing losses and static limitation text can leave apparently clean outputs outside a defensible envelope.

[Physics documentation](physics.md), sections G–H, also asserts generic manifold-loss percentages, negligible property error, ±20% package variation, TIM doubling after 2–3 years, and lifetime TDP creep without adequate supporting provenance. Treat these as unsupported generalizations, not established population statistics. Its proposed 5°C coverage is even smaller than its own 5.6°C package perturbation at 700 W. Preserve useful stress scenarios, but require owner-defined bounds and remove implied service-life predictions.

### Fidelity priorities

- **Matters now:** applicability of rectangular-channel correlations and effective heated area; evidence-backed package/interface resistance; temperature-aware properties or a restricted temperature envelope; explicit non-plate pressure losses and available head for any CDU claim; worst-branch flow allowance for parallel screening. Obtain measured curves where first-principles geometry is insufficient. Do not add unexplained correction factors.
- **Can wait:** general heterogeneous hydraulic networks, detailed aging distributions, full pump-efficiency maps, transient RC/control analysis, and a spreading submodel. Until justified, use bounded user inputs or declare those decisions unsupported; spatial effects may require immediate external validation even if an internal solver waits.
- **Outside this reduced-order product:** general-purpose CFD, resolved jet/manifold turbulence, local boiling inception and multiphase flow, die-scale hotspot fields, and manufacturing/lifetime certification. Exchange evidence with specialist tools instead of claiming to replace them.

Displayed hundredths of a degree and thousandths of LPM communicate solver precision, not model accuracy. Reports should separate numerical convergence, input ranges, model discrepancy, and decision margin.

## 5. Recommended product definition

**Target user:** a thermal or mechanical systems engineer at a server OEM, cooling supplier, or AI-infrastructure integrator, preparing an early architecture review with access to component information.

**Primary use case:** screen an identical parallel GPU rack, compare a few explicitly bounded operating alternatives, and produce a reviewable thermal/hydraulic requirements and validation memo. Retain series analysis as a diagnostic; do not expand immediately into a universal network solver.

Support these four decisions exceptionally well:

1. Is the defined architecture feasible within stated temperature, flow, and available-pressure constraints?
2. What per-branch operating flow range and rack flow/head requirement satisfy those constraints?
3. Which supply-temperature, coolant, or component alternative remains feasible under the same constraints and stated degradation scenarios?
4. Which uncertain input could reverse the decision, and what measurement or simulation should resolve it next?

**Required inputs:** heat load/count; topology; caller-approved temperature limit and guardband; supply-temperature range; coolant identity/concentration and property source; geometry or measured component thermal/hydraulic curves; package/TIM resistance with reference boundary, provenance, and ranges; allowed branch/rack flow; available differential pressure or pump curve; non-plate loss data; minimum branch-flow allowance. Mark unknowns explicitly. Do not silently fill unknown hardware properties from a chip label.

**Required outputs:** evaluated constraints and separate nominal/stressed/unsupported states; worst-GPU temperature and margin; branch/rack flow, modeled heat duty, and coolant return temperature; component versus total modeled pressure and hydraulic margin; pumping assumptions; candidate comparison; dominant decision-changing uncertainties; equations/model version and complete input provenance; excluded effects; actionable next validation step. A missing loss budget should produce “hydraulic feasibility undetermined,” not a complete CDU selection.

**Necessary fidelity:** conservation-based steady-state models, appropriate correlations inside declared ranges, and traceable component curves when available. Curve-based evidence can coexist with transparent physics if reference temperatures and included resistances prevent double counting. No proprietary geometry reverse-engineering is necessary.

**Necessary validation:** independent thermal and hydraulic calculations across supported regimes, measured component curves across relevant flow/temperature conditions, and a rack/branch aggregation check with held-out operating points. Agreement tolerances must be justified before comparison by measurement uncertainty and the intended decision margin.

A senior engineer should find one useful artifact: “Here are the constrained alternatives, why this one survives the stated stresses, and the missing evidence that could change the choice.” If resistance uncertainty dominates, recommend a controlled heater/plate thermal-resistance measurement; if head is uncertain, measure branch and assembly ΔP versus flow; if hotspots or maldistribution dominate, request instrumented temperatures/branch flows or targeted conjugate CFD.

Out of scope: hardware signoff, complete facility/CDU heat-exchanger design, coolant chemistry qualification, financial ROI, generic copilots, and arbitrary cold-plate shape optimization.

## 6. Role of MCP

MCP provides discoverable, typed calls into deterministic calculations, including geometry overrides, sensitivity, explicit optimization failure, and structured reports. The [in-memory client](../examples/mcp_client_demo.py) verifies the call path without requiring an LLM. These are useful capabilities, but transport does not add model validity or engineering judgment.

Client screenshots, server setup, and payload demonstrations are onboarding infrastructure. Keep one tested example; do not make agent orchestration a product milestone. The [README](../README.md) now includes good limitations, but the project name, package description, MCP section, screenshot, and origin story still make the interface disproportionately prominent.

An engineering agent needs machine-readable validity states, input provenance, evaluated constraints, reason codes, unavailable results, and recommended evidence collection. It must preserve unknowns and failure semantics through follow-up calls. Implement these in shared domain schemas and expose them through Python and MCP identically. Retain the thin wrapper; an HTTP API or CLI could later expose the same decisions without changing the product.

## 7. What to stop doing

Stop prioritizing framework polish, additional tool names, chip-count expansion, and transient breadth before the current recommendation can defend its meaning. Keep regression automation; expand it only for engineering evidence or actual reliability gaps.

Emphasize the physics audit trail, measured evidence, explicit feasibility, and decision synthesis. De-emphasize generic risk colors, fixed flow multipliers, and branded reference cases as proof of accuracy. Keep the financial example archived; no active physics capability currently warrants deletion. Consolidate overlapping examples only after a canonical workflow replaces their unique teaching value.

Rewrite the README opening, roadmap, and “Why This Exists” around the engineering job. Align `CLAUDE.md` with the three-layer product once approved. Revise physics/assumption docs to distinguish correlation domains, scenarios, measurements, and unsupported generalizations; make `public_specs.md` a source ledger. Preserve MCP contracts in `docs/mcp.md` as interface documentation.

Make `quickstart.py` the inspection entry point, evolve `decision_memo_examples.py` into the canonical constrained study after its report semantics are repaired, and have `interactive_sizing.ipynb` visualize that same scenario. Label `real_chip_benchmarks.py` as public reference studies unless measurement comparisons earn the benchmark terminology.

Reframe [nvl72_rack_analysis.py](../examples/nvl72_rack_analysis.py), lines 1–10 and 165–174: its procurement question and “CDU PROCUREMENT SPEC” heading exceed the evidence despite labeling the displayed pressure as cold-plate-only. A complete CDU requirement needs the omitted hydraulic budget, cooling duty boundary, and component evidence.

Likely schema redesign: separate fixed evaluation from optimization; distinguish attempted from feasible flow bands; replace overloaded `feasible` with decision states; allow unavailable temperatures; add constraint/evidence records and signed scenario deltas. Clarify `recommended_supply_temp_c`, `FlowBand.max_lpm`, and the unused-but-validating ambient input. These are future compatibility decisions, not changes authorized by this review.

`thermal-mcp-server` is now too implementation-specific as product positioning, though it remains a serviceable package identifier. Evaluate name categories centered on thermal-hydraulic systems, cooling architecture, or auditable engineering decisions; use AI infrastructure as a scope descriptor. Avoid names implying CFD, certification, or black-box prediction. Choose a name only after the product boundary is accepted.

## 8. Three recommended milestones

### Milestone 1 — Establish a trustworthy model and result envelope

**Engineering objective / user value:** users can tell what was calculated, what is supported, and what is unknown before trusting a recommendation.

**Work:** repair fixed-flow, failed-search, rack-failure, and placeholder semantics; separate heuristics from physics; audit correlation domains and heated-area assumptions; document or restrict unsupported inputs; source property/resistance assumptions and relabel aging as caller-defined scenarios. Add provenance and validity contracts without introducing new interfaces.

**Validation:** independent Darcy–Weisbach and thermal hand calculations, regime/geometry boundary cases, analytical sensitivity checks, and regression cases for every reproduced failure above. Audit the default case against applicable engineering references; label any unvalidated region.

**Done:** every published output distinguishes evaluated point, supported domain, and recommendation status; invalid or unavailable results cannot masquerade as feasible designs; numerical tests pass without weakened tolerances. Documentation contains a claim-to-evidence matrix, including absent evidence.

**Sequence:** constrained sizing would otherwise amplify ambiguous verdicts and unjustified precision.

### Milestone 2 — Close one constrained rack-sizing workflow

**Engineering objective / user value:** determine a usable operating envelope for the identical parallel rack and a defensible flow/head requirement.

**Work:** combine thermal targets with explicit branch/rack flow and pressure limits; include supplied non-plate losses or measured component/system curves; support temperature variation within a justified property envelope; incorporate a declared minimum branch-flow allowance. Compare a small candidate set under common constraints. Keep math in physics and decision logic in synthesis.

**Validation:** independent hydraulic budgets and operating-point intersections; feasible, thermally limited, hydraulically limited, and incomplete-data cases; a measured or independently published component dataset with defined reference conditions. Check aggregation and conservation; do not use guessed vendor parameters as validation.

**Done:** one canonical study produces constraint-derived flow bands, worst-branch margin, pressure budget, and honest unresolved requirements. Fixed-flow inputs remain fixed. No point outside caller limits is recommended. Claims are bounded to the demonstrated component/domain.

**Sequence:** only a complete constrained workflow can support meaningful uncertainty ranking and user evaluation.

### Milestone 3 — Demonstrate evidence-backed engineering judgment

**Engineering objective / user value:** show that the memo improves an actual architecture review and directs the next useful validation action.

**Work:** propagate user-bounded operating/degradation scenarios across the whole rack; rank assumptions by ability to change the decision; attach provenance, signed deltas, and concrete measurement/CFD recommendations. Export one reproducible decision record through existing interfaces.

**Validation:** use held-out component points plus an independently measured or documented branch/rack case. Predeclare acceptable temperature/pressure error relative to measurement uncertainty and decision margins. Have two or three external engineers reproduce a study against their spreadsheet/vendor-data workflow and challenge the conclusions.

**Done:** publish a reproducible, source-permitted case with residual errors, decision agreement/disagreement, and limitations; reviewers can reconstruct the recommendation and identify the next validation action. If measurement access is unavailable, leave empirical credibility explicitly unachieved. Success is demonstrated usefulness, not tool count or adoption claims.

**Sequence:** this tests whether the engineering differentiator exists after correctness and workflow completeness, before broader roadmap investment.

## 9. Open strategic questions for the owner

- Which first user and review decision can you access directly: server architecture screening, supplier component comparison, or rack integration?
- Can you obtain publishable resistance/ΔP curves and one branch/rack case, including reference conditions and measurement uncertainty?
- Will the first release explicitly narrow to identical parallel racks, keeping series as a diagnostic rather than promising general network design?
- Should measured component curves be a first-class input alongside geometry models, and who owns their provenance and validity?
- What decision margin and evidence threshold would make a reviewer accept a recommendation, and when should the engine abstain?
- Is the owner willing to replace the current polished recommendation labels with explicit unresolved states until evidence supports them?

After these choices, record accepted product boundaries in `docs/decisions.md` and update `CLAUDE.md`. `docs/agent-notes.md` does not currently exist and is unnecessary for this review; this proposal should not silently become durable policy.
