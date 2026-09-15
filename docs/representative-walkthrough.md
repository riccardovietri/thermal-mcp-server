# Representative walkthrough: an eight-GPU cooling screen

This is the shortest useful explanation of what the project does, followed by
enough detail to defend the calculation in a technical conversation.

## The 20-second version

> Thermal MCP Server is a Python thermal-hydraulic screening engine with an MCP
> interface, built for engineers making early decisions about liquid-cooled AI
> hardware. I used it to evaluate an illustrative eight-GPU parallel rack at
> 700 W per GPU, with 25°C water and 8 LPM per GPU. The model predicted a 70.9°C
> maximum junction temperature, 26.3°C rack return temperature, and 16.8 kPa of
> cold-plate pressure drop. That passed an 83°C limit with a 5°C guardband in the
> model, but I concluded that full system hydraulic feasibility was still unknown
> because manifolds, fittings, and the pump curve were outside the model.

The project value is not that an LLM estimates the answer. Python evaluates a
deterministic model; MCP lets an AI client supply structured inputs, call it, and
receive the assumptions, intermediate results, status, and limitations together.

## The 90-second version

> It is a first-pass design and screening tool for liquid-cooled accelerators,
> for an engineer or an LLM acting through the MCP interface. It models the
> series thermal path from junction-to-case resistance through the TIM, cold-plate
> base conduction, convection into the coolant, and the coolant's own temperature
> rise. On the hydraulic side it uses Darcy–Weisbach to estimate cold-plate
> pressure drop and an illustrative pumping-power requirement.
>
> The run I keep coming back to is an eight-GPU parallel case with 700 W per GPU,
> 8 LPM of water per GPU, and a 25°C inlet. The model predicted a 70.90°C maximum
> junction temperature against an 83°C limit: 12.10°C of hard-limit margin, or
> 7.10°C after a caller-selected 5°C guardband. The coolant warms 1.26°C through
> each branch, and half of that rise contributes 0.63°C to the junction estimate.
> The resistance breakdown was more useful than the final temperature: 61.85%
> junction-to-case, 30.92% TIM, 6.43% convection, and 0.80% base conduction.
>
> That changes the next engineering action. Doubling flow from 8 to 16 LPM lowers
> modeled junction temperature by only 1.70°C, while cold-plate pressure rises
> from 16.80 to 60.33 kPa and per-plate pumping power rises from 4.48 to 32.17 W,
> a 7.18× increase. Halving the assumed TIM resistance from 0.02 to 0.01 K/W
> lowers junction temperature by 7.00°C. I would first validate the package and
> TIM resistance assumptions and investigate the interface before paying the
> hydraulic cost of more flow. The model identifies that priority; it does not
> prove that a particular material change will deliver it.
>
> It is deliberately bounded: steady-state and one-dimensional, with no spreading
> resistance, channel or branch maldistribution, manifold losses, pump curve,
> transients, or two-phase behavior. It tells me what dominates the simplified
> design, whether a candidate passes the stated thermal criterion, and what to
> measure or simulate next. It does not replace CFD or hardware validation.

## The question

> For an illustrative rack with eight identical 700 W accelerators in parallel,
> does a fixed operating point of 8 LPM per GPU with 25°C water keep modeled
> junction temperature below an 83°C limit while retaining a 5°C guardband?

The corresponding report input is:

```python
from thermal_mcp_server.decision_report import generate_decision_report
from thermal_mcp_server.schemas import DecisionScenario

scenario = DecisionScenario(
    chip_label="Illustrative 700 W accelerator",
    heat_load_w=700.0,
    gpu_count=8,
    topology="parallel",
    target_junction_temp_c=83.0,
    margin_c=5.0,
    coolant="water",
    inlet_temp_c=25.0,
    flow_rate_lpm=8.0,  # per GPU; 64 LPM total rack flow
)
report = generate_decision_report(scenario)
```

The relevant schema-v2 report results are:

| Result | Value | Meaning |
|---|---:|---|
| Status | `meets_target` | The evaluated point meets the guarded thermal criterion in this model. |
| Maximum junction temperature | 70.90°C | All ideal parallel branches have the same predicted temperature. |
| Margin to 83°C limit | 12.10°C | `83 − 70.90`. |
| Margin to guarded criterion | 7.10°C | `(83 − 5) − 70.90`; this determines the status. |
| Rack return temperature | 26.26°C | Eight 700 W loads add 5.6 kW to the 64 LPM stream. |
| Cold-plate-only pressure drop | 16.80 kPa | One ideal parallel branch; manifold and system losses are excluded. |
| Illustrative pumping estimate | 35.84 W | Uses total rack flow and a fixed 50% efficiency, not a pump curve. |
| System hydraulic feasibility | `not_assessed` | Available head and non-plate losses were not supplied. |
| Hardware validation state | `unvalidated` | Equations are checked; this case is not calibrated to measured hardware. |

The conclusion is deliberately narrower than “this rack works”: **the proposed
point passes the modeled thermal criterion under the stated inputs.** The next
engineering step is to obtain cold-plate and manifold pressure-drop curves,
available pump head, and evidence for the package/TIM resistances before sizing
the CDU or freezing hardware.

## The decision-driving comparison

These are computed model outputs, not measured hardware data:

| Case | Junction temperature | Cold-plate ΔP | Per-plate pump estimate | Change from baseline |
|---|---:|---:|---:|---|
| Baseline: 8 LPM, `R_tim=0.02 K/W` | 70.90°C | 16.80 kPa | 4.48 W | — |
| Double flow: 16 LPM | 69.20°C | 60.33 kPa | 32.17 W | −1.70°C; 7.18× pump estimate |
| Half TIM resistance: 8 LPM, `R_tim=0.01 K/W` | 63.90°C | 16.80 kPa | 4.48 W | −7.00°C; unchanged hydraulics |

The flow comparison crosses from the implementation's transitional treatment at
8 LPM (`Re=3734`) into its turbulent treatment at 16 LPM (`Re=7468`). Therefore,
the 7.18× pumping ratio is the result of this model at these two points, not a
universal cubic scaling law. A real system operating point still requires the
complete loss curve and pump curve.

## How Python calculates the result

The detailed model is documented in [physics.md](physics.md), the concise map is
in [model_overview.md](model_overview.md), the implementation is in
[physics.py](../src/thermal_mcp_server/physics.py), and independent equation
checks are in [test_physics_behavior.py](../tests/test_physics_behavior.py).

### 1. Convert rack flow into channel velocity

Each GPU receives 8 LPM. With 40 square channels, each 1 mm by 1 mm:

```text
V_dot = 8 LPM = 1.3333e-4 m³/s
A_flow = n * w * h = 40 * 0.001 * 0.001 = 4.0e-5 m²
v = V_dot / A_flow = 3.333 m/s
Dh = 2wh / (w + h) = 0.001 m
```

The dimensionless flow groups are:

```text
Re = rho * v * Dh / mu = 3734
Pr = cp * mu / k = 6.20
```

This point lies in the model's transitional range, `2300 ≤ Re ≤ 4000`.

### 2. Estimate convection

The implementation uses `Nu=4.36` for its laminar endpoint and evaluates
Dittus–Boelter at the upper transition endpoint, `Re=4000`:

```text
Nu_turbulent_endpoint = 0.023 * 4000^0.8 * Pr^0.4 = 36.336
h = Nu * k / Dh
```

At this point it linearly blends between the endpoint values, giving:

```text
Nu = 31.33
h = 18,801 W/(m²·K)
```

That linear blend is a numerical choice that keeps an optimization continuous.
It is not a validated transition correlation.

### 3. Build the thermal-resistance network

The model uses Fourier conduction through the copper base and Newton convection
to the coolant:

```text
R_base = t_base / (k_copper * A_contact) = 0.000519 K/W
A_wetted = n * 2(w + h) * L = 0.0128 m²
R_conv = 1 / (h * A_wetted) = 0.004155 K/W

R_total = R_jc + R_tim + R_base + R_conv
        = 0.04 + 0.02 + 0.000519 + 0.004155
        = 0.064675 K/W
```

Here `R_jc=0.04 K/W` and `R_tim=0.02 K/W` are scenario assumptions. Together
they account for 42°C of the predicted rise, so their provenance matters more
than extra numerical precision in the solver.

### 4. Apply the coolant energy balance

For steady, single-phase heat pickup:

```text
Q_dot = m_dot * cp * deltaT_coolant
m_dot = rho * V_dot = 0.13293 kg/s per GPU
deltaT_coolant = 700 / (0.13293 * 4180) = 1.25976°C
```

The junction estimate uses the mean coolant temperature, approximated as the
inlet plus half the bulk rise:

```text
T_junction = T_inlet + 0.5 * deltaT_coolant + Q_dot * R_total
           = 25 + 0.62988 + 700 * 0.064675
           = 70.90°C
```

For eight ideal parallel branches, total flow and heat are both multiplied by
eight, so the rack coolant rise stays 1.25976°C and return temperature is 26.26°C.

### 5. Estimate channel pressure drop

The hydraulic calculation uses Darcy–Weisbach:

```text
deltaP = f * (L / Dh) * (rho * v² / 2)
```

The implementation linearly blends its laminar and Blasius turbulent friction
endpoints at this Reynolds number, giving `f=0.03791` and:

```text
deltaP = 16,800 Pa = 16.80 kPa
```

Parallel branches see the same modeled branch pressure drop. The estimate omits
manifolds, headers, bends, fittings, valves, entrance/exit effects, roughness,
and flow maldistribution. The 35.84 W pumping number is simply
`deltaP * V_dot_total / 0.50`; it does not locate a real pump-system operating
point.

## What holds up under outside scrutiny

An engineer from robotics, automotive, aerospace, or industrial systems should
recognize the underlying method:

- Mass/energy conservation, continuity, Reynolds and Prandtl definitions,
  Fourier conduction, Newton convection, and Darcy–Weisbach are standard.
- Dittus–Boelter and Blasius are empirical closures. Their applicability depends
  on Reynolds number, geometry, roughness, boundary condition, and development
  length.
- `Nu=4.36`, the effective wetted area, the half-bulk-temperature approximation,
  fixed 25°C properties, and the transitional blend are declared model choices.
- Package/TIM resistances, geometry, temperature limit, and pump efficiency are
  device or scenario inputs; defaults are not vendor measurements.
- The tests reproduce the stated equations and rack aggregation. The repository
  does not yet contain measured cold-plate or rack validation data.

The same calculation can screen a steady, single-phase liquid-cooled robotics
inverter if its loss, geometry, and thermal interfaces are represented. It cannot
be transferred unchanged to a motor with transient duty cycles, distributed
winding/core losses, thermal mass, and rotating heat paths. That needs a different
network, transient modeling, or measured calibration.

## What the MCP adds

Without MCP, this remains a useful Python model. MCP makes it discoverable and
composable for an AI client. The client can ask for missing inputs, call the same
tested functions, compare alternatives, and return a structured record containing
the result status, input provenance, model version, stress cases, and blind spots.
It should never fill missing engineering evidence with an LLM guess.

To reproduce the interface locally, run:

```bash
uv run python examples/mcp_client_demo.py
uv run python examples/decision_memo_examples.py --review
```
