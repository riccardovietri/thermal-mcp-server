# Handoff: working on thermal-mcp-server with an orchestrating model

Written 2026-11-15, from what worked on `thermal-design-loop` over the previous week. This file is uncommitted; keep, edit or delete it.

## What made the last project move fast
1. **State lives in the repo, not in chat.** Five files did the work: a frozen spec with dated amendments, an assumptions register
   (every external number with source and status), a one-line-per-decision log, a progress file with a "Resume here" section, and a
   work plan with gates. Any model or person could resume cold. This repo already has `docs/assumptions.md` and `docs/decisions.md`;
   it lacks a progress file and a work plan.
2. **Validate each solver against a known answer before using its output.** Every level had an analytical or independent reference
   and a stated tolerance. Gates were never loosened; when one failed, the work stopped and the numbers were reported. Two of the
   most useful findings came from failed or tight gates.
3. **Written briefs with acceptance criteria.** The orchestrating model wrote each brief (scope, files, gates, what not to touch,
   what to report), a cheaper model implemented it on a branch, and the orchestrator reviewed the pull request and the figures
   before merging. One coding agent at a time once usage got tight; isolated worktrees when two ran in parallel.
4. **Sources read in full text, never constants from memory.** Literature passes went through scholarly APIs and extracted PDFs,
   with every number tagged as text, figure, inferred or snippet.
5. **Plots before decisions.** Requirement numbers, the selection rule and the recommended design were all settled by looking at a
   figure, then recorded.
6. **Physics-judgment calls go to Riccardo; plumbing does not.** Boundary conditions, requirement values and anything that changes
   a recommendation were surfaced. Tooling choices were made and logged.

## What the last project found about this repo's physics
These are the candidates for the first work here. None has been changed yet.
- `physics.py` uses **circular-tube constants on rectangular channels**: Nu = 4.36 and f = 64/Re in laminar flow, with no
  aspect-ratio dependence. For rectangular ducts the laminar values depend on aspect ratio (Shah & London).
- **No fin efficiency.** The full wetted area is treated as if it were at base temperature.
- **No propylene glycol.** Coolants are water and 50% ethylene glycol at 25 °C; data-centre loops commonly run 25% propylene glycol
  at 30 to 45 °C. `thermal-design-loop` takes properties from CoolProp (`tools/fluids.py`).
- **Typical cold-plate channels are deeply laminar** (Reynolds 100 to 200 at 1.5 LPM per kW), so the Dittus-Boelter branch and the
  Re < 500 warning rarely describe a real operating point.
- A straight-fin model that fixes the first two points exists in `thermal-design-loop/tools/screen_1d.py`, tested against the
  Shah & London table and checked against conjugate CFD (1.0% mean difference on thermal resistance). It is the natural thing to
  bring upstream.
- An indicative comparison with a measured skived plate (Ortega et al., ASME InterPACK 2022) had that corrected model reading 6 to
  16% low with an assumed base thickness. This repo's benchmarks are against published specifications, not measured resistance.

## Suggested first three pieces of work
1. **Bring the straight-fin model upstream** as a new geometry option, leaving the existing API and defaults working. Follow this
   repo's physics-change protocol (`AGENTS.md`): justification in `docs/physics.md`, behaviour test, hand-calculation test.
   Gate: reproduce `thermal-design-loop`'s 1D numbers for its recommended design to within rounding.
2. **Coolant properties with temperature**, including 25% propylene glycol, with a sourced basis.
3. **Re-run the public benchmarks** (H100, GB200 NVL72, MI300X, Gaudi 3) with the corrected physics and report what moved. This is
   a result worth publishing either way.

## How to start a session
Paste something like this as the first message, with the model set up as orchestrator:

> Read `AGENTS.md`, `CLAUDE.md`, `docs/decisions.md`, `docs/assumptions.md`, `docs/physics.md` and `docs/fable-handoff.md`.
> Then propose a `PROGRESS.md` and a `docs/work-plan.md` for the three pieces of work in the handoff, with a gate for each.
> Interview me only on physics-judgment calls. Work on branches, one pull request per piece, and do not merge without CI passing.
> Delegate implementation to a cheaper model with a written brief and review its pull request yourself.

## On renaming to `thermal-server-mcp`
Recommendation: don't, or rename to something that describes the content.
- The package is published on PyPI as `thermal-mcp-server` at 0.3.0. A PyPI name cannot be renamed; a new name means a new package
  and a deprecated old one.
- "X-mcp-server" is the common pattern for MCP servers, so the current name is findable. "thermal-server-mcp" reads as an MCP for
  thermal servers and is no clearer.
- GitHub redirects old links after a repo rename, so the repo side is cheap; the package side is not.
- If the goal is positioning (the resume calls it "Server Thermal MCP"), a display title in the README does that without a rename.

## Housekeeping noticed
- The local checkout is on branch `claude/repo-review-2026-06-18`, not `main`.
- Commits in this repo use a personal email; `thermal-design-loop` was switched to the GitHub no-reply address.
