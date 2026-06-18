# Public Specification Inputs

The examples use public sources and explicit estimates. This file describes the
source categories without treating every value as equally certain.

## Vendor-Published Inputs

- NVIDIA H100 SXM TDP and thermal limit references.
- NVIDIA GB200/NVL72 public system power and product context.
- AMD MI300X public data sheet values where available.
- Intel Gaudi 3 public product brief values where available.

## Public Analysis And Proxies

- B200/NVL72 thermal-limit examples use public third-party analysis where NVIDIA
  does not publish the required junction-temperature limit.
- MI300X and Gaudi 3 examples use conservative junction-temperature proxies when
  vendor Tj max is not published.
- B200-style cold-plate geometry and package resistance are engineering
  estimates used to demonstrate sensitivity and sizing behavior.

## How To Read The Examples

Values labeled `published` are taken from public vendor-facing materials.
Values labeled `estimated`, `proxy`, or `engineering estimate` are not vendor
specifications. They should be treated as scenario inputs for model exploration,
not as design authority.

## What Is Excluded

The repo does not include proprietary hardware data, internal validation data,
vendor confidential cold-plate geometry, or measured rack test results.
