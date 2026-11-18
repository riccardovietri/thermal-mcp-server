# Public Specification Inputs

The examples use public sources and explicit estimates. This file describes the
source categories without treating every value as equally certain.

## Vendor-Published Inputs

- NVIDIA H100 SXM TDP and thermal limit references.
- NVIDIA GB200/NVL72 public system power and product context.
- AMD MI300X public data sheet values where available.
- Intel Gaudi 3 public product brief values where available.

## Public Analysis And Proxies

- GB200 NVL72 thermal-limit examples use public third-party analysis where NVIDIA
  does not publish the required junction-temperature limit.
- MI300X and Gaudi 3 examples use conservative junction-temperature proxies when
  vendor Tj max is not published.
- B200-style cold-plate geometry and package resistance are engineering
  estimates used to demonstrate sensitivity and sizing behavior.

## Reference Flow

`examples/reference_case.py` evaluates every chip at a reference flow of
1.5 LPM per kW of TDP (owner decision, 2026-11-17), next to the historical
8 LPM default. 1.5 LPM/kW is a scenario input representative of how loops are
commonly sized, not a vendor specification. The straight-fin plate used there
is the screened design from the companion `thermal-design-loop` study, not a
vendor geometry. Results are in [`fidelity-results.md`](fidelity-results.md).

## How To Read The Examples

Values labeled `published` are taken from public vendor-facing materials.
Values labeled `estimated`, `proxy`, or `engineering estimate` are not vendor
specifications. They should be treated as scenario inputs for model exploration,
not as design authority.

## What Is Excluded

The repo does not include proprietary hardware data, internal validation data,
vendor confidential cold-plate geometry, or measured rack test results.
