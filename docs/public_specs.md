# Public Specification Inputs

The examples use public sources and explicit estimates. This file describes the
source categories without treating every value as equally certain.

## Vendor-Published Inputs

- NVIDIA H100 SXM TDP: up to 700 W, NVIDIA H100 product page.
- NVIDIA Blackwell GPU in GB200 NVL72: configurable up to 1,200 W per GPU, NVIDIA
  Blackwell datasheet (HGX B200 is the same GPU family at up to 1,000 W).
- Intel Gaudi 3 OAM: 900 W, Intel Gaudi 3 technical paper (2025). The 1200 W
  liquid-cooled value is from Intel's Hot Chips 2024 material; the 2025 paper
  states 900 W liquid-cooled. The examples keep 1200 W and flag the conflict.
- AMD MI300X 750 W is from trade press; AMD's data sheet could not be opened.

Sources and access notes are listed in
[`research/package-resistance-review.md`](research/package-resistance-review.md).

## Public Analysis And Proxies

- No junction limit in the examples is vendor-published for that part. H100 SXM
  83 °C is a conservative design value (the H100 PCIe product brief gives 87 °C).
  The Blackwell GPU 75 °C is a design target whose source could not be traced.
- MI300X and Gaudi 3 examples use conservative junction-temperature proxies when
  vendor Tj max is not published.
- B200-style cold-plate geometry and package resistance are engineering
  estimates used to demonstrate sensitivity and sizing behavior.
- `examples/reference_case.py` shows package resistance for H100 and the
  Blackwell GPU as a band estimated from die area (H100 814 mm², NVIDIA; Blackwell
  GPU 15.6 cm², an order-of-magnitude footprint from a published test-vehicle
  paper, not a measured die area) and published interface data. No vendor
  publishes junction-to-case resistance for these parts; the band is low
  confidence on values. MI300X and Gaudi 3 stay on the generic package because
  their die area is not published.

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
