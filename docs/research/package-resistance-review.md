# Package resistance literature review

Status: research note for the owner. No code, tests, defaults or chip data were changed.
Scope: why no public chip case in `docs/fidelity-results.md` meets its junction limit at
1.5 LPM/kW and 35 °C inlet, and which input assumption is most likely wrong.

## How to read this note

Every number carries a source number (S1 to S33, listed in Section 5) and one tag:

- **[text]** read in the source text.
- **[figure]** read off a chart.
- **[derived]** computed here from cited numbers; the arithmetic is shown.
- **[secondary]** a third party reporting about a vendor.

Source rank, best first: **R1** vendor datasheet or spec, **R2** standards body / OCP / ASHRAE,
**R3** peer-reviewed or proceedings paper, **R4** vendor white paper, application note or
distributor sheet, **R5** trade press, analyst or personal technical blog. No forum posts are used.

Where a step needs a value that no source gave (die thickness, lid thickness), it is marked
**assumption** and shown as a range so the owner can see how much it matters.

Reference-case arithmetic used throughout (configuration C, straight-fin reference plate, water,
35 °C inlet, 1.5 LPM/kW), from the model run on `origin/main` at `03e7d44`:

- Coolant capacity rate per kW at 1.5 LPM/kW: 1.5/60000 m³/s × 997 kg/m³ × 4180 J/kg·K =
  104.19 W/K, so the coolant rise is 1000/104.19 = 9.598 K at any power and half of it is
  4.799 K [derived from the repo's water properties].
- Plate side, `R_base + R_conv` = 1.461 + 6.374 = 7.835 mK/W, the same for every chip in
  configuration C because the plate is on its laminar plateau [model output, `docs/fidelity-results.md`].
- So **Tj(C) = 35 + 4.799 + Q × (R_jc + R_tim + 7.835 mK/W)**. Check: H100, 700 W,
  60 mK/W package gives 35 + 4.799 + 700 × 0.067835 = 87.28 °C, which matches the published 87.3 °C.

## 1. Summary

| # | Finding | Confidence |
|---|---|---|
| F1 | **The generic package pair `R_jc + R_tim` = 60 mK/W is the input that is wrong, and it is too high by roughly 2x to 10x.** A bottom-up estimate from die area and published TIM classes gives about 10 to 39 mK/W for H100 (814 mm²) and about 5 to 20 mK/W for a 1200 W Blackwell part if its die area is about 15.6 cm². Two independent measured stacks point the same way: an OCP TTV cold plate measured 14 to 19 mK/W case-to-inlet *including TIM2* (S8), and a trade-press GB300 run implies about 6 mK/W junction-to-plate-inlet (S22, derived). With these values H100 runs at about 52 to 72 °C and a 1200 W part at about 55 to 73 °C in configuration C (Section 3.3). | Medium on direction and order of magnitude; low on any single per-chip value |
| F2 | **`R_tim` = 20 mK/W is the clearest outlier.** Over the H100 die area it equals 0.163 K·cm²/W, the range of older greases (S15), against 0.04 K·cm²/W for a current phase-change pad (S31) and 0.08 to 0.12 K·cm²/W for an optimized grease (S14). Over the reference plate's 35.6 cm² contact area it equals 0.71 K·cm²/W, at the top of the 2003-era phase-change range of 0.3 to 0.7 K·cm²/W (S15). A modern TIM2 over an H100-sized die is about 5 to 15 mK/W. | Medium |
| F3 | **1200 W for the per-GPU device in GB200 NVL72 is a vendor number, not an estimate.** NVIDIA's Blackwell datasheet lists the Blackwell GPU in GB200 NVL72 as "Configurable up to 1,200 W" and in HGX B200 as up to 1,000 W (S6). The repo's "SemiAnalysis estimate" label can be upgraded. | High |
| F4 | **None of the junction limits in the repo is traceable to a vendor document for that SKU.** The H100 SXM 83 °C "NVIDIA datasheet, throttle onset" attribution was not found in any NVIDIA document read; the NVIDIA H100 PCIe product brief gives 87 °C GPU thermal qualification temperature (S1), and a secondary blog reports nvidia-smi values for H100 SXM5 of 85 °C max operating, 87 °C slowdown, 90 °C shutdown (S26). The B200 75 °C value could not be traced to SemiAnalysis (paywalled, S27) or NVIDIA. MI300X and Gaudi 3 limits are not published in anything read. | Medium that the labels need correcting; low on what the right values are |
| F5 | **1.5 LPM/kW at 35 °C is a defensible reference point.** OCP's OAI guideline gives 1.25 to 2.0 LPM/kW with 1.5 LPM/kW as the typical target and a "Group 2" secondary supply of 30 to 37 °C (S8). A GB200 NVL72 rack vendor document gives 45 °C max inlet and about 1.13 LPM/kW (S20, derived). The flow per kW changes Tj by only about 1 to 4 K across 1.0 to 2.0 LPM/kW in configuration C; inlet temperature moves Tj one for one. | High for flow per kW; medium for 35 °C as the single reference |

## 2. Findings by question

### Q1. Package resistance (junction to case, junction to coolant)

**No vendor publishes `R_jc`, `psi_jc` or junction-to-coolant resistance for H100, B200/GB200,
MI300X or Gaudi 3 in any document read.** Searched: NVIDIA H100 product page and datasheet, H100
PCIe product brief, Blackwell datasheet, Intel Gaudi 3 technical paper and Hot Chips slides, AMD
SMI documentation; web searches for "psi_jc", "junction to case", "thermal design guide" with each
part name. AMD MI300X documents could not be opened (Section 4). Thermal design guides for these
parts appear to be under NDA; none was found publicly.

What was found:

| Quantity | Value | Boundary | Source | Tag | Rank |
|---|---|---|---|---|---|
| H100 die area | 814 mm² | GH100 die | S4 NVIDIA Hopper in-depth blog | [text] | R1 |
| OAM TTV cold plate, DI water, 1.5 to 3.5 LPM per plate, 1 kW, 30 × 30 mm heater | 0.014 to 0.019 °C/W | case (top of copper lid) to inlet, includes TIM2 (phase-change material) | S8 OCP OAI guideline, Sec. 6.3.3 | [text] | R2 |
| Same TTV, single plate, DI water, high flow | 0.015 to 0.016 °C/W | case to inlet | S8 Sec. 6.2.3 | [text] | R2 |
| Same TTV, PG25 | below 0.02 °C/W | case to inlet | S8 Sec. 6.2.3 | [text] | R2 |
| OCP statement on what dominates | "a large portion of the temperature built up could originate from surface of and within the package" | qualitative | S8 Sec. 2.5 | [text] | R2 |
| OCP interface recommendation | TIM effective conductivity > 5 W/m·K, mounting pressure > 40 psi, cold plate flatness < 0.1 mm, package warpage < 0.2 mm | TIM2 | S8 Sec. 3.5 | [text] | R2 |
| JetCool SmartPlate on H100 | 0.122 °C/W reduced to 0.021 °C/W | **not stated** (could be junction-to-inlet; the release does not say) | S24 HPCwire release, 2024 | [text] | R4/R5 |
| MSI GB300 workstation plate | about 0.017 °C/W at 1.5 LPM | not stated; MSI figure reported by press | S22 StorageReview, 2026 | [secondary] | R5 |
| Same run: GPU die 60 °C, coolant leaving radiator 37 °C, GPU about 995 W | (60 − 37)/995 = 23.1 mK/W junction to loop supply; minus 17 mK/W plate gives about 6.1 mK/W for die, TIM and anything else | junction to supply, package by difference | S22 | [derived] from [secondary] | R5 |
| Blackwell (B200) logic area emulated by Accelsius | 60 × 26 mm = 15.6 cm² | heater footprint, not a measured die | S13 InterPACK2025 | [text] (their source for it is weak, see note) | R3 |

Note on S13: the paper cites an NVIDIA H100 datasheet for the B200 area, which does not contain it.
Treat 15.6 cm² as a plausible order of magnitude for two reticle-sized dies, not a die area.

Note on S22: the die temperature is the value the GPU reports, which may be an average sensor rather
than the hottest point, and the 0.017 °C/W plate figure has no stated boundary. The 6 mK/W result
is therefore a lower-bound style indication, not a measurement of `R_jc + R_tim`.

**Bottom-up estimate (labelled estimate).** The model's `R_jc` lumps everything between junction
and package top surface; `R_tim` is the interface to the cold plate (TIM2, or TIM1.5 on a bare die).
Whether H100 SXM, B200 and MI300X are lidded or bare-die was **not established** from any source
read (Section 4), so both builds are shown. 1D conduction over the die area, uniform power, no
hotspot factor.

Inputs:

| Input | Value | Source | Tag |
|---|---|---|---|
| Silicon conductivity at 350 K | k = 1.5 (T/300)^(-4/3) W/cm·K = 1.5 × (350/300)^(-4/3) = 1.22 W/cm·K = 122 W/m·K | S16 Electronics Cooling 1998 | [derived] from [text] formula |
| Doped silicon | about 80% of pure value | S16 | [text] |
| Die thickness | 0.5 to 0.8 mm | **assumption**, no source found | |
| Reflowed indium TIM1 | < 0.05 K·cm²/W | S15 Electronics Cooling 2003 (solder class) | [text] |
| Indium bulk conductivity, typical bondline | 86 W/m·K; bondlines > 0.2 mm "not uncommon" | S18 Indium Corp. PDS | [text] |
| Indium TIM1 bulk term | 0.2 mm / 86 W/m·K = 2.33e-6 m²K/W = 0.023 K·cm²/W | S18 | [derived] |
| Compressed indium foil (TIM2 use), ASTM D5470 | 0.039 to 0.061 cm²·°C/W | S19 Indium TIMs brochure | [text] |
| Copper lid conductivity | 385 W/m·K | repo default `copper_k` | (repo) |
| Lid thickness | 1.5 to 3 mm | **assumption**, no source found | |
| Phase-change TIM2 (PTM7950 class) | 0.04 °C·cm²/W, 8.5 W/m·K | S31 distributor sheet | [text] |
| Optimized grease bondline | 8 to 12 K·mm²/W = 0.08 to 0.12 K·cm²/W | S14 IBM, THERMINIC 2007 | [text], [derived] unit conversion |
| Grease, older and newer products | about 1 and about 0.2 K·cm²/W | S15 | [text] |
| PCM (2003 era) | 0.3 to 0.7 K·cm²/W | S15 | [text] |

H100, A = 8.14 cm² [derived from S4]:

| Term | Arithmetic | mK/W |
|---|---|---|
| Die conduction | 0.5e-3/(122 × 8.14e-4) to 0.8e-3/(122 × 8.14e-4) | 5.0 to 8.1 |
| TIM1 indium (lidded only) | 0.023/8.14 to 0.05/8.14 K·cm²/W ÷ cm² | 2.9 to 6.1 |
| Copper lid, 1D over die area (lidded only) | 1.5e-3/(385 × 8.14e-4) to 3e-3/(385 × 8.14e-4) | 4.8 to 9.6 |
| TIM2, PCM to optimized grease | 0.04/8.14 to 0.12/8.14 | 4.9 to 14.7 |
| **Bare die total (`R_jc` = die; `R_tim` = TIM2)** | 5.0 + 4.9 to 8.1 + 14.7 | **9.9 to 22.8** |
| **Lidded total** | (5.0 + 2.9 + 4.8) + 4.9 to (8.1 + 6.1 + 9.6) + 14.7 | **17.6 to 38.5** |

1200 W Blackwell part, A = 15.6 cm² (order-of-magnitude area from S13; every term scales by
8.14/15.6 = 0.522): bare die 5.2 to 11.9 mK/W, lidded 9.2 to 20.1 mK/W [derived].

What the estimate leaves out: non-uniform power maps and hotspots (raise effective `R_jc`, not
quantified in any source read), lateral spreading in the lid (lowers the lid and TIM2 terms), TIM
ageing and pump-out (raises `R_tim`), and HBM and VRM heat sharing the plate. The OCP measurement is
a consistency check: if its plate side is near the model's 7.8 mK/W, its 14 to 19 mK/W
case-to-inlet leaves about 6 to 11 mK/W for TIM2 over 9 cm², or 0.055 to 0.10 K·cm²/W [derived],
inside the PCM-to-grease band above. The OCP plate is not the model plate, so this is consistency,
not validation.

MI300X and Gaudi 3: die areas were **not found** in any source read (Section 4). MI300X package
footprint is 76.8 × 72.0 × 4.9 mm per TechInsights (S29, search summary only; page not opened, not
used for arithmetic). No bounded estimate is given for these two parts.

### Q2. Area scaling

Yes. Interface resistances are published as area-specific values (K·cm²/W or K·mm²/W) in every TIM
source read (S14, S15, S18, S19, S31), and S13 normalizes cold-plate results by die area in
mm²·K/W for the same reason. A fixed K/W value silently assumes one die size: the same 20 mK/W is
0.163 K·cm²/W on an 8.14 cm² die but 0.31 K·cm²/W on a 15.6 cm² die [derived]. For a screening
model that compares parts of different die area, area-specific inputs are the honest form.

| TIM class | Area-specific resistance | Source | Tag | Rank |
|---|---|---|---|---|
| Solder (reflowed metal) | < 0.05 K·cm²/W | S15 | [text] | R4/R5 |
| Indium bulk term at 0.2 mm bondline | 0.023 K·cm²/W | S18 | [derived] | R4 |
| Indium foil, compressed, 40 psi, ASTM D5470 | 0.0514 at 0.004" | S19 | [text] | R4 |
| In-clad foil / 52In48Sn foil | 0.0606 / 0.0390 | S19 | [text] | R4 |
| Phase-change pad, current (PTM7950) | 0.04 °C·cm²/W | S31 | [text] | R4 |
| Optimized grease, 27 to 46 µm bondline | 0.08 to 0.12 K·cm²/W | S14 | [text] | R3 |
| Grease, 2003 traditional / newest | about 1 / about 0.2 K·cm²/W | S15 | [text] | R4/R5 |
| Phase change (2003) | 0.3 to 0.7 K·cm²/W | S15 | [text] | R4/R5 |
| Gels | 0.4 to 0.8 K·cm²/W | S15 | [text] | R4/R5 |
| Elastomeric pads / tapes | 1 to 3 / 1 to 4 K·cm²/W | S15 | [text] | R4/R5 |
| GT90 Pro grease under a 75 × 75 mm calorimeter | 1.2 K/kW over 56.25 cm² = 0.0675 K·cm²/W | S17 | [derived] from [text] | R4 |
| Measurement floor of a conventional TIM stand | about 2 K·mm²/W (0.02 K·cm²/W), bondline < 5 µm | S14 | [text] | R3 |

Liquid-metal TIM1 values: no numeric value was found in any source read (Indium's liquid-metal
pages give plots without numbers, S30). Not reported here.

### Q3. Junction limits

| Chip | Repo value | What was found | Source | Tag | Rank |
|---|---|---|---|---|---|
| H100 SXM | 83 °C, "NVIDIA datasheet, throttle onset" | Not in the NVIDIA H100 datasheet (S2, PCIe page, no temperatures) or H100 product page (S3, no temperatures). H100 **PCIe** brief: thermal qualification temperature GPU T_AVG = 87 °C, HBM 95 °C; max operating at TLIMIT = 0 °C, hardware slowdown at TLIMIT = −2 °C, shutdown at TLIMIT = −5 °C (TLIMIT is a distance to the slowdown point, not an absolute temperature) | S1 PB-11133-001_v02, 2022 | [text] | R1 (different SKU) |
| H100 SXM | | nvidia-smi fields for H100 SXM5 80GB: max operating 85 °C, slowdown 87 °C, shutdown 90 °C; HBM slowdown about 95 °C; the blog gives no source | S26 MANISH AI blog, 2026 | [secondary] | R5 |
| H100 | | "known throttle temperature is 87C", citing a TechPowerUp PCIe page | S13 | [secondary] | R3 citing R5 |
| B200 / GB200 | 75 °C, "SemiAnalysis" | Not found in the free part of SemiAnalysis's GB200 article (thermal section paywalled) | S27 | not found | R5 |
| B200 / GB200 | | GB300 trade-press run: NVIDIA data center GPUs "don't begin reducing clocks until the die is well into the 80s" | S22, 2026 | [secondary] | R5 |
| MI300X | 85 °C proxy | AMD SMI docs: high violation percentage "combined with high hotspot temps (>95°C) indicates thermal throttling" (diagnostic guidance, not a limit); slowdown and shutdown limits are shown by `amd-smi static --limit`, values not published | S12 | [text] | R1 |
| Gaudi 3 | 85 °C proxy | No junction or throttle limit in Intel technical paper (S9), Hot Chips slides (S10) or Supermicro OAM hardware page (S11) | | not found | |

What operators design to: not found as a published number for these parts. The OCP TTV work
recommends keeping case temperature "below 75C through test" for the TTV (S8 Sec. 6.2.2, [text])
and shows a 1 kW OAM case below 60 °C at 30 to 37 °C supply (S8, [text]). Those are case targets
for a test vehicle, not junction limits.

### Q4. Power

| Chip | Repo value | Found | Source | Tag | Rank |
|---|---|---|---|---|---|
| H100 SXM | 700 W | "Up to 700W (configurable)"; H100 NVL 350 to 400 W; H100 PCIe 300 to 350 W | S3 NVIDIA H100 page; S2 datasheet | [text] | R1 |
| Blackwell GPU in GB200 NVL72 | 1200 W, "SemiAnalysis estimate" | "Configurable up to 1,200 W" per GPU for GB200 NVL72 and GB200 NVL4; HGX B200 "Configurable up to 1,000 W" | S6 NVIDIA Blackwell datasheet, 2025 | [text] | R1 |
| Same | | Supermicro GB200 NVL72 rack operating power 125 to 135 kW | S21 | [text] | R4 |
| MI300X | 750 W | Headline "Rated for 750 Watts"; AMD's own data sheet could not be opened | S28 Tom's Hardware | [secondary], headline only | R5 |
| Gaudi 3 OAM (HL-325L) | 900 W air | "up to 900W Total Device Power (TDP) with passive cooling and up to 900W TDP with liquid cooling" | S9 Intel technical paper, V1 Rev. 2, March 2025 | [text] | R1/R4 |
| Gaudi 3 OAM | 1200 W liquid | "900W (Air) / 1200W (Liquid)"; "Up to 1200W with liquid cooling" | S10 Intel Hot Chips 2024 slides | [text] | R4 |

The two Intel documents disagree on the liquid-cooled figure; the later document (S9, 2025) says
900 W for the HL-325L with liquid cooling. A separate liquid-cooled mezzanine (HL-335) appears on
Intel's Habana product page only in a search summary (page not opened); its power was not found in
anything read.

### Q5. Naming

| Statement | Source | Tag | Rank |
|---|---|---|---|
| GB200 NVL72 "connects 36 Grace CPUs and 72 Blackwell GPUs in a rack-scale, liquid-cooled design" | S5 NVIDIA GB200 NVL72 page | [text] | R1 |
| A GB200 Grace Blackwell Superchip pairs two Blackwell GPUs with one Grace CPU | S5 | [text] | R1 |
| The datasheet's per-GPU table has columns GB200 NVL72, GB200 NVL4, HGX B200 under "Individual Blackwell GPU Specifications" | S6 | [text] | R1 |
| Supermicro lists the rack's GPUs as "72x NVIDIA Blackwell B200 GPUs"; 18 compute trays of 4 GPUs (QCT) | S21, S20 | [text] | R4 |

So: **GB200** is the superchip (2 GPUs + 1 CPU), **NVL72** is the 72-GPU NVLink rack domain, and
NVIDIA calls the per-GPU device a "Blackwell GPU". "B200" is used by OEMs and by NVIDIA for the HGX
product, where the same GPU name carries a 1,000 W limit (S6). Calling the 1200 W row "B200" invites
confusion with HGX B200 at 1,000 W.

Recommended row label: **"Blackwell GPU (GB200 NVL72), 1200 W"**, with the note that HGX B200 is the
same GPU family at up to 1,000 W.

### Q6. Facility conditions

| Item | Value | Source | Tag | Rank |
|---|---|---|---|---|
| ASHRAE 5th ed. (2021) liquid classes by facility-water upper limit | W17 17 °C, W27 27 °C, W32 32 °C, W40 40 °C (new), W45 45 °C, W+ above 45 °C | S25 Upsite summary of ASHRAE; the ASHRAE book and reference card were not opened | [secondary] | R4 (reporting R2) |
| OCP OAI flow per kW | coolant rise 7.5 to 12 °C, "equivalent to ... 1.25 LPM/kW~2.0 LPM/kW" for PG25; "typical design target is 10°C temperature rise, i.e. 1.5 LPM/kW" | S8 Sec. 1.3 | [text] | R2 |
| OCP OAI secondary supply groups | Group 1: 40 to 45 °C; Group 2: 30 to 37 °C; Group 3: 15 to 25 °C | S8 Sec. 1.4 | [text] | R2 |
| OCP OAM cold plate flow | 1 to 2 L/min per plate typical | S8 Sec. 1.3 | [text] | R2 |
| GB200 NVL72 rack (QCT) | max liquid inlet 45 °C, max return 65 °C, up to 130 LPM per rack, liquid cooling 115 kW | S20 | [text] | R4 |
| Same, per kW | 130/115 = 1.13 LPM/kW | S20 | [derived] | R4 |
| CoolIT 4 kW cold plate test | 6 LPM, "1.5 LPM per kW" as the industry-recommended flow | S23 StorageReview, 2025 | [secondary] | R5 |
| GB300 workstation run | coolant to plates 37 °C, return 47 °C, plate flow 1.5 LPM at about 995 W | S22 | [secondary] | R5 |
| CDU approach for GB300 NVL72 (CoolIT CHx2000) | 2 MW at 5 °C approach | S7 NVIDIA blog, 2025 | [text] | R4 |

Is 1.5 LPM/kW at 35 °C reasonable? Flow per kW: yes, it is the OCP typical target and sits inside
the published 1.13 to 2.0 LPM/kW band. Inlet: 35 °C is inside OCP Group 2 (30 to 37 °C) and below
the 45 °C rack maximum in S20, so it is a fair mid-case, not a worst case. The Vertiv / OCP "30 °C
coolant" roadmap (S32) and Uptime's figures (S33) could not be opened, so a 30 °C industry minimum
is not cited as a number here.

Sensitivity in configuration C (model run, current package 60 mK/W; then package 25 mK/W):

| Inlet (°C) | LPM/kW | H100 Tj, 60 / 25 mK/W | 1200 W Tj, 60 / 25 mK/W |
|---:|---:|---|---|
| 30 | 1.5 | 82.3 / 57.8 | 116.2 / 74.2 |
| 35 | 1.0 | 89.7 / 65.2 | 123.6 / 81.6 |
| 35 | 1.5 | 87.3 / 62.8 | 121.2 / 79.2 |
| 35 | 2.0 | 86.1 / 61.6 | 120.0 / 78.0 |
| 40 | 1.5 | 92.3 / 67.8 | 126.2 / 84.2 |
| 45 | 1.5 | 97.3 / 72.8 | 131.2 / 89.2 |

Going from 1.0 to 2.0 LPM/kW moves Tj by 3.6 K at any package value; going from 60 to 25 mK/W moves
it by 24.5 K (H100) and 42 K (1200 W). The package term dominates.

### Q7. Cold-plate resistance sanity check

| Plate | Resistance | Boundary | Conditions | Source | Tag | Rank |
|---|---|---|---|---|---|---|
| OCP OAM plate, system test | 0.014 to 0.019 °C/W | case to inlet, includes PCM TIM2 | DI water, 1.5 to 3.5 LPM per plate, 1 kW, 30 × 30 mm heater | S8 | [text] | R2 |
| UIUC Cu diamond-pin plate | 7.6 K/kW (0.0076 K/W) | calorimeter top to inlet, includes TIM | 1 kW, 75 × 75 mm, water, 1.7 to 3.8 LPM | S17 Electronics Cooling, 2026 | [text] | R4 (academic authors, magazine) |
| UIUC CuW pin plate | 10.4 K/kW | same | same | S17 | [text] | R4 |
| CoolIT 4 kW plate | < 0.009 °C/W | not stated | 6 LPM, 4 kW TTV | S23 | [secondary] | R5 |
| MSI GB300 plate | about 0.017 °C/W | not stated | 1.5 LPM | S22 | [secondary] | R5 |
| Two-phase direct-on-die | about 0.0062 K/W; 11.38 mm²·K/W at 1200 W | fluid to heater, no TIM | refrigerant, 15.6 cm² | S13 | [text] | R3 |
| **Model, configuration C** | 1.461 + 6.374 = **7.835 mK/W** plate only, no TIM | base + convection | 1.05 to 1.8 LPM | `docs/fidelity-results.md` | (model) | |

The model's plate side, 7.8 mK/W, is in family with the UIUC plate+TIM 7.6 mK/W over a large
heater and leaves room under the OCP 14 to 19 mK/W case-to-inlet for a 6 to 11 mK/W TIM2 [derived].
**The plate is not the problem.** Adding the model's 20 mK/W `R_tim` gives 27.8 mK/W case-to-inlet,
about 1.5 to 2x the OCP measurement on a similar-size heat source [derived: 27.8/19 = 1.46,
27.8/14 = 1.99].

## 3. Proposed changes for the owner (options, not edits)

All Tj values are configuration C at 35 °C inlet and 1.5 LPM/kW using
Tj = 39.799 + Q × (R_jc + R_tim + 7.835 mK/W); model-run values match this to 0.01 K.
Required package for a pass: 1200 W at 75 °C needs R_jc + R_tim ≤ (75 − 39.799)/1200 − 7.835e-3
= 21.5 mK/W; H100 at 83 °C needs ≤ 53.9 mK/W; at 85 °C ≤ 56.7 mK/W; at 87 °C ≤ 59.6 mK/W [derived].

### 3.1 R_jc

| Option | Value | Evidence | Confidence | H100 Tj (R_tim 20) | 1200 W Tj (R_tim 20) |
|---|---|---|---|---|---|
| Keep | 40 mK/W | none | n/a | 39.799 + 700 × 0.067835 = 87.3 | 39.799 + 1200 × 0.067835 = 121.2 |
| Per-chip estimate, lidded upper | H100 24 mK/W; 1200 W part 12 mK/W | Q1 bottom-up, lidded high end (8.1 + 6.1 + 9.6 = 23.8; ×0.522 = 12.4) | Low | 39.799 + 700 × 0.051835 = 76.1 | 39.799 + 1200 × 0.039835 = 87.6 |
| Per-chip estimate, bare die | H100 5 to 8 mK/W; 1200 W part 3 to 4 mK/W | Q1, die conduction only | Low | 700 × (0.005..0.008 + 0.027835): 62.8 to 64.9 | 1200 × (0.003..0.004 + 0.027835): 76.8 to 78.0 |

### 3.2 R_tim

| Option | Value | Evidence | Confidence | H100 Tj (R_jc 40) | 1200 W Tj (R_jc 40) |
|---|---|---|---|---|---|
| Keep | 20 mK/W | none; equals 0.163 K·cm²/W on H100 die, 2003-era grease | n/a | 87.3 | 121.2 |
| PCM / optimized grease over die | H100 5 to 15 mK/W; 1200 W part 3 to 8 mK/W | S31, S14 over die area; OCP check 6 to 11 mK/W over 9 cm² (S8, derived) | Medium | 700 × (0.040 + 0.005..0.015 + 0.007835): 76.8 to 83.8 | 1200 × (0.040 + 0.003..0.008 + 0.007835): 100.8 to 106.8 |

Either change alone leaves the 1200 W row failing; both together are needed.

### 3.3 Combined package (the decision that matters)

| Option | H100 R_jc + R_tim | 1200 W R_jc + R_tim | H100 Tj | 1200 W Tj | Confidence |
|---|---|---|---|---|---|
| Keep | 60 | 60 | 87.3 (fail at 83) | 121.2 (fail at 75) | n/a |
| Lidded estimate | 17.6 to 38.5 | 9.2 to 20.1 | 39.799 + 700 × (0.0176..0.0385 + 0.007835) = 57.6 to 72.2 | 39.799 + 1200 × (0.0092..0.0201 + 0.007835) = 60.2 to 73.3 | Low to medium |
| Bare-die estimate | 9.9 to 22.8 | 5.2 to 11.9 | 52.2 to 61.2 | 55.4 to 63.5 | Low to medium |
| Single central value for screening | 25 | 12 | 62.8 | 63.6 | Low |

Recommendation for the owner: if one change is made, replace the 60 mK/W package with per-chip or
area-scaled values in the 10 to 40 mK/W band for H100-class dies, and present the result as a band,
not a point. Keep the current 60 mK/W only as an explicitly labelled conservative stress case.

**Model form: area-specific is the better change.** Reasons: every TIM source reports K·cm²/W; the
parts differ in die area by about 2x; and it makes the assumption auditable (die area is public for
H100, TIM class is a nameable choice). Per-chip K/W values are simpler but would be unsourced numbers
again for three of four parts.

Schema changes each would need (described, not made):

- *Per-chip package values.* No schema change; `r_jc_k_per_w` and `r_tim_k_per_w` already exist on
  the inputs. Changes are in `examples/real_chip_benchmarks.py` (`ChipSpec` gains `r_jc` and `r_tim`
  with a source string) and the reference-case script. Not API-breaking.
- *Area-specific formulation.* Additive, optional fields, for example `die_area_m2`,
  `r_jc_area_k_m2_per_w` and `r_tim_area_k_m2_per_w`, with a validator that either the K/W pair or the
  area-specific pair plus area is given, and `R = r_area / die_area`. The existing `contact_area_m2`
  (default 100 cm²) is the plate footprint and should not be reused as die area. Needs a
  `docs/physics.md` justification and a hand-calc test under the physics change protocol; keeping
  the K/W fields as the default path avoids breaking callers.

### 3.4 Junction limits

| Chip | Current | Proposed | Evidence | Confidence | Effect (config C, current package) |
|---|---|---|---|---|---|
| H100 SXM | 83 °C, "NVIDIA datasheet" | Keep 83 °C as a conservative design value but relabel as "not vendor-published for SXM; PCIe brief gives 87 °C qualification; nvidia-smi SXM5 reports 85 °C max operating (secondary)"; or use 85 °C | S1, S26 | Low to medium | margin −4.3 K at 83, −2.3 K at 85; with a 25 mK/W package +20.2 K at 83 |
| 1200 W Blackwell | 75 °C, "SemiAnalysis" | Keep 75 °C as a labelled design target, not a limit; source not traceable | S27 not found; S22 "well into the 80s" (secondary) | Low | unchanged; pass needs package ≤ 21.5 mK/W |
| MI300X | 85 °C proxy | Keep as proxy | S12 only says > 95 °C hotspot indicates throttling | Low | n/a |
| Gaudi 3 | 85 °C proxy | Keep as proxy | nothing found | Low | n/a |

### 3.5 TDP

| Chip | Current | Proposed | Evidence | Confidence |
|---|---|---|---|---|
| H100 SXM | 700 W | Keep; source NVIDIA H100 page | S3 | High |
| Blackwell GPU (GB200 NVL72) | 1200 W, "SemiAnalysis estimate" | Keep 1200 W; relabel source as NVIDIA Blackwell datasheet. Optionally add HGX B200 at 1000 W (Tj config C, current package: 39.799 + 1000 × 0.067835 = 107.6 °C; with 12 mK/W: 59.6 °C) | S6 | High |
| MI300X | 750 W | Keep; vendor confirmation pending (AMD data sheet not opened) | S28 | Medium |
| Gaudi 3 | 900 W air / 1200 W liquid | Keep 900 W; mark 1200 W liquid as "Hot Chips 2024; Intel's 2025 technical paper says 900 W liquid", or drop the 1200 W row | S9, S10 | Medium |

### 3.6 Labels

| Current | Proposed | Evidence | Confidence |
|---|---|---|---|
| "B200 (NVL72)" | "Blackwell GPU (GB200 NVL72)" | S5, S6 | High |

### 3.7 Inlet temperature and flow per kW

| Item | Current | Proposed | Evidence | Confidence | Effect |
|---|---|---|---|---|---|
| Inlet | 35 °C | Keep 35 °C as reference; report a 30 to 45 °C sweep (OCP Group 2 to rack max) | S8, S20 | Medium | ±1 K Tj per 1 K inlet (table in Q6) |
| Flow per kW | 1.5 LPM/kW | Keep; optional 1.0 to 2.0 band | S8, S20 | High | 1.0 to 2.0 LPM/kW moves Tj by 3.6 K |

## 4. What could not be established

| Gap | What was searched | What would settle it |
|---|---|---|
| Vendor `R_jc` / `psi_jc` / junction-to-coolant for any of the four parts | vendor pages, datasheets, product briefs, web search per part | NVIDIA / AMD / Intel thermal design guides (likely NDA), or a published measured stack on real silicon |
| Whether H100 SXM, B200 and MI300X are lidded or bare die, and TIM1 type | web search, teardown coverage | Teardown or cross-section report (TechInsights), or vendor mechanical drawings |
| B200, MI300X, Gaudi 3 die areas | NVIDIA, AMD, Intel documents; trade press | Vendor architecture papers (ISSCC / Hot Chips) or die-shot analyses |
| Die thickness and lid thickness | not found | Cross-section, package drawings |
| Hotspot factor (peak vs average flux) | not found | Vendor power maps or TTV heat-map spec |
| H100 SXM junction limit from NVIDIA | NVIDIA pages, datasheet, PCIe brief | An HGX H100 thermal guide, or `nvidia-smi -q -d TEMPERATURE` on owned hardware (the limits are readable from the driver) |
| B200 junction limit and the origin of 75 °C | SemiAnalysis (paywalled), NVIDIA | NVIDIA GB200 documentation, or driver output on hardware |
| MI300X and Gaudi 3 limits | AMD SMI docs, Intel papers, Supermicro manual | `amd-smi static --limit`; `hl-smi -q` on hardware |
| MI300X TDP from AMD | AMD data sheets and pages timed out (four attempts across three URLs) | Opening the AMD MI300X data sheet |
| Gaudi 3 liquid-cooled power, 900 vs 1200 W | two Intel documents disagree | Intel HL-335 product brief |
| ASHRAE classes from the primary text | ASHRAE reference card URL returned 404 | ASHRAE *Thermal Guidelines*, 5th ed., liquid cooling chapter |
| Vertiv / OCP 30 °C coolant roadmap; Uptime flow figures | Vertiv returned 403 on four locales; Uptime PDF 404; DCD 403 | Opening the OCP white paper "30°C Coolant, A Durable Roadmap for the Future" |
| Liquid-metal TIM1 area-specific values | Indium pages | A peer-reviewed TIM1 comparison (ECTC / ITherm) |

The single measurement that would settle the main question: junction temperature, inlet temperature
and power on one real H100 SXM (or GB200 tray) cold plate at known flow, with the plate's
case-to-inlet resistance known. `(Tj − T_in − ΔT/2)/Q − R_plate` gives `R_jc + R_tim` directly.

## 5. Sources

Access: **full** = page or PDF text read; **partial** = only part readable; **not accessible** =
could not be opened, no numbers cited from it.

| ID | Title | Publisher / venue | Year | URL | Rank | Access |
|---|---|---|---|---|---|---|
| S1 | NVIDIA H100 PCIe GPU Product Brief, PB-11133-001_v02 | NVIDIA (mirror) | 2022 | https://openzeka.com/wp-content/uploads/2023/12/PB-11133-001_v01.pdf | R1 | full |
| S2 | NVIDIA H100 Tensor Core GPU Datasheet (PCIe edition) | NVIDIA (PNY mirror) | 2022 | https://www.pny.com/file%20library/company/support/product%20brochures/nvidia%20data%20center%20gpus/nvidia-h100-datasheet.pdf | R1 | full |
| S3 | NVIDIA H100 Tensor Core GPU product page | NVIDIA | accessed 2026 | https://www.nvidia.com/en-us/data-center/h100/ | R1 | full |
| S4 | NVIDIA Hopper Architecture In-Depth | NVIDIA Technical Blog | 2022 | https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/ | R1 | full |
| S5 | NVIDIA GB200 NVL72 product page | NVIDIA | accessed 2026 | https://www.nvidia.com/en-us/data-center/gb200-nvl72/ | R1 | full |
| S6 | NVIDIA Blackwell Datasheet | NVIDIA (mirror) | 2025 | https://gpusolutions.hrp.hu/wp-content/uploads/2026/05/blackwell-datasheet-4204213.pdf | R1 | full |
| S7 | Blackwell platform water efficiency, liquid cooling | NVIDIA Blog (M. Hamilton) | 2025 | https://blogs.nvidia.com/blog/blackwell-platform-water-efficiency-liquid-cooling-data-centers-ai-factories/ | R4 | full |
| S8 | OCP OAI System Liquid Cooling Guidelines (Mar 3 2023 update) | Open Compute Project (Meta, Microsoft, Intel, CoolerMaster, Wiwynn, Boyd) | 2023 | https://www.opencompute.org/documents/oai-system-liquid-cooling-guidelines-in-ocp-template-mar-3-2023-update-pdf | R2 | full |
| S9 | Intel Gaudi 3 AI Accelerator Technical Paper, V1 Rev. 2 | Intel (Presidio mirror) | 2025 | https://www.presidio.com/wp-content/uploads/2025/06/gaudi-3-ai-accelerator-white-paper.pdf | R1/R4 | full |
| S10 | Intel Gaudi 3 AI Accelerator: Architected for Gen AI Training and Inference (R. Kaplan) | Hot Chips 2024 | 2024 | https://www.hc2024.hotchips.org/assets/program/conference/day1/60_HC2024.Intel.RomanKaplan.Gaudi3-0826.pdf | R4 | full |
| S11 | Gaudi3 OAM Key Hardware (SYS-822GA-NGR3 manual) | Supermicro | accessed 2026 | https://www.supermicro.com/en/support/manuals/product/system/sys-822ga-ngr3/Content/gaudi3-oam-key-hardware.htm | R4 | full |
| S12 | AMD SMI: GPU violations | AMD ROCm documentation | accessed 2026 | https://rocm.docs.amd.com/projects/amdsmi/en/latest/conceptual/gpu-violations.html | R1 | full |
| S13 | Direct on Die Two Phase Cooling Approach for High Power GPUs, INTERPACK2025-164278 (Narayanan et al.) | ASME InterPACK | 2025 | https://accelsius.com/wp-content/uploads/164278-Direct-on-Die-Two-Phase-Cooling-Approach-for-High-Power-GPUs-1-1.pdf | R3 | full |
| S14 | High-Performance Thermal Interface Technology Overview (Linderman, Brunschwiler, Smith, Michel) | THERMINIC 2007 / IBM Research | 2007 | https://arxiv.org/pdf/0801.1046 | R3 | full |
| S15 | Thermal Interface Materials (D. Blazej) | Electronics Cooling | 2003 | https://www.electronics-cooling.com/2003/11/thermal-interface-materials/ | R4/R5 | full |
| S16 | The Thermal Conductivity of Silicon | Electronics Cooling | 1998 | https://www.electronics-cooling.com/1998/05/the-thermal-conductivity-of-silicon/ | R4/R5 | full |
| S17 | High-Performance Copper-Tungsten Cold Plates for Direct-to-Chip Single-Phase Liquid Cooling (Pinkus, Park, Ganesan, Zaki, Miljkovic, King) | Electronics Cooling | 2026 | https://www.electronics-cooling.com/2026/04/high-performance-copper-tungsten-cold-plates-for-direct-to-chip-single-phase-liquid-cooling/ | R4 | full |
| S18 | Indium-Based Solder Thermal Interface Materials, PDS 100407 R0 | Indium Corporation | 2025 | https://www.indium.com/wp-content/uploads/2025/08/Indium-Based-Solder-Thermal-Interface-Materials-PDS-100407-R0.pdf | R4 | full |
| S19 | Thermal Interface Materials brochure 99342 A4 R4 | Indium Corporation | 2025 | https://www.indium.com/wp-content/uploads/2025/08/TIMs-Brochure-99342-A4-R4.pdf | R4 | full |
| S20 | QCT QoolRack Stand-Alone: Advanced Liquid Cooling for NVIDIA GB200 NVL72 Systems | QCT / TCI Media | 2025 | https://blog.qct.io/wp-content/uploads/2025/04/QCT-Qoolrack-Stand-Alone_Advanced-Liquid-Cooling-for-NVIDIA-GB200-NVL72-Systems.pdf | R4 | full |
| S21 | Supermicro NVIDIA GB200 NVL72 SuperCluster datasheet | Supermicro | accessed 2026 | https://www.supermicro.com/datasheet/datasheet_SuperCluster_GB200_NVL72.pdf | R4 | full |
| S22 | MSI XpertStation WS300 thermals: why a 1300W GB300 does not throttle on a desk (B. Beeler) | StorageReview | 2026 | https://www.storagereview.com/review/msi-xpertstation-ws300-thermals-why-a-1300w-gb300-does-not-throttle-on-a-desk | R5 | full |
| S23 | CoolIT unveils 4000W cold plate | StorageReview | 2025 | https://www.storagereview.com/news/coolit-unveils-4000w-cold-plate-setting-new-standard-for-single-phase-direct-liquid-cooling | R5 | full |
| S24 | JetCool SmartPlate technology elevates NVIDIA H100 GPUs | HPCwire (JetCool release) | 2024 | https://www.hpcwire.com/off-the-wire/jetcools-smartplate-technology-elevates-nvidia-h100-gpus-with-superior-cooling-efficiency/ | R4/R5 | full |
| S25 | Major changes to ASHRAE's fifth edition of Thermal Guidelines, part 3: liquid cooling | Upsite Technologies | 2024 | https://www.upsite.com/blog/major-changes-to-ashraes-fifth-edition-of-thermal-guidelines-part-3-liquid-cooling-chapter-updates/ | R4 | full |
| S26 | Why HBM thermal throttling is silent | MANISH AI (personal technical blog) | 2026 | https://manishklach.github.io/writings/why-hbm-thermal-throttling-is-silent.html | R5 | full |
| S27 | GB200 Hardware Architecture and Component Supply Chain | SemiAnalysis | 2024 | https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component | R5 | partial (thermal section paywalled; no numbers cited) |
| S28 | AMD MI300X Guzzles Power, Rated for 750 Watts | Tom's Hardware | 2023 | https://www.tomshardware.com/news/amd-mi300x-guzzles-power-rated-for-750-watts | R5 | partial (headline only) |
| S29 | AMD Instinct MI300X Processor Floorplan Analysis | TechInsights | 2024 | https://www.techinsights.com/blog/amd-instinct-mi300x-processor-floorplan-analysis | R5 | not accessible (search summary only; not used for arithmetic) |
| S30 | Metal TIMs 101, chapter 2 | Indium Corporation blog | n.d. | https://www.indium.com/ko/blog/metal-tims-101-chapter-2/ | R4 | full (no numeric values in text) |
| S31 | Solstice (Honeywell) PTM7950 product sheet | Krayden (distributor) | accessed 2026 | https://www.krayden.com/products/solstice-ptm7950 | R4 | full (manufacturer TDS not opened) |
| S32 | A roadmap for the future chip coolant temperature | Vertiv | n.d. | https://www.vertiv.com/en-us/about/news-and-insights/articles/blog-posts/a-roadmap-for-the-future-chip-coolant-temperature/ | R4 | not accessible (HTTP 403) |
| S33 | Uptime Intelligence report on DLC flow rates | Uptime Institute | 2025 | https://intelligence.uptimeinstitute.com/entity_pdf/node/153594/pdf | R5 | not accessible (HTTP 404) |

Also attempted and not accessible, no numbers used: AMD Instinct MI300X data sheet, MI300X platform
data sheet, CDNA 3 white paper and MI300X product page (amd.com, timeouts); ASHRAE 2021 reference
card (404); CoolIT 4000 W and skived cold plate technical briefs (404); JetCool H100 page (404);
Data Center Dynamics "Hot water, cold water" (403); AnandTech Blackwell article (blocked); Tom's
Hardware Blackwell and Frore articles (body truncated); Honeywell PTM7950 and PTM7900 pages
(redirect / 404).
