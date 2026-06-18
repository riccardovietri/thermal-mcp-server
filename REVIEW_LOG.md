# Overnight Review Log

Branch: `codex/codebase_review`
Base: `origin/main` at `8de237a` (PR #28 merged)
Date: 2026-06-18

## Baseline

Started from `origin/main` because `main` is checked out in another local
worktree. Created `codex/codebase_review` directly from `origin/main`.

Read before edits:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/decisions.md`
- `docs/physics.md`

Baseline commands:

- `tree -L 3` failed because `tree` is not installed locally.
- `find . -maxdepth 3 ...` used as the tree snapshot substitute.
- `uv run pytest` passed: `72 passed in 0.72s`.
- `uv build` passed: built source distribution and wheel.
- `uv run python examples/decision_memo_examples.py` passed.
- `uv run python examples/rack_topology_tradeoffs.py` passed.
- `uv run python examples/real_chip_benchmarks.py` passed.
- `uv run python examples/nvl72_rack_analysis.py` passed.
- `uv run python examples/ai_factory_cooling_budget.py` passed.

Observed local-only ignored artifacts:

- `.venv/`, `venv/`
- `.pytest_cache/`
- `dist/`
- `build/`
- `__pycache__/` directories
- `src/thermal_mcp_server.egg-info/`

These are ignored generated artifacts, not repo content.

## Initial Findings

- `examples/quickstart.py` and `examples/rack_sizing_example.py` do not exist.
- `README.md` leads with Colab and Claude Desktop instead of a fast local
  runnable path.
- `README.md` roadmap mentions ROI work, but `docs/decisions.md` says financial
  ROI work belongs in a separate repo or app.
- `docs/mcp.md` still says the server exports four tools; PR #28 added a fifth
  tool, `generate_decision_report`.
- `CLAUDE.md` still says four MCP tools and contains stale old-priority wording.
- `docs/review-policy.md` and `.github/PULL_REQUEST_TEMPLATE.md` still assume
  Claude review, but the funded automatic review path is now Codex/human review.
- `.github/workflows/claude.yml` and `.github/workflows/claude-review-response.yml`
  still require `ANTHROPIC_API_KEY`.
- `examples/ai_factory_cooling_budget.py` contains financial/cost modeling that
  conflicts with the ROI-separate project decision.
- Ruff is not configured or listed in dev dependencies.

## Intended Workstreams

1. Add first-touch examples and smoke tests.
2. Move the financial-cost example to `_attic/` with a reason.
3. Refresh README and concise docs to match current behavior.
4. Align review process docs and remove Claude-funded workflows.
5. Add conservative Ruff configuration and CI checks.
6. Run final local and fresh-env gates.

## Moved To `_attic/`

- `_attic/ai_factory_cooling_budget.py` - moved from `examples/` because it
  includes electricity-cost and annual operating-cost estimates. The repo
  decision in `docs/decisions.md` says ROI and financial modeling belong in a
  separate package or app.

## Workstream Updates

### First-touch examples

Added:

- `examples/quickstart.py`
- `examples/rack_sizing_example.py`
- `tests/test_examples.py`

Verification:

- `uv run pytest` passed: `74 passed in 0.94s`.
- `uv build` passed.
- `uv run python examples/quickstart.py` passed.
- `uv run python examples/rack_sizing_example.py` passed.

### Scope alignment

Moved:

- `examples/ai_factory_cooling_budget.py` to `_attic/ai_factory_cooling_budget.py`

Reason:

- The example still runs, but it includes cost assumptions that belong outside
  this core physics package per `docs/decisions.md`.

### Documentation and review process

Updated:

- `README.md` now leads with local install, first-touch examples, model scope,
  assumptions, test count, roadmap, and rationale.
- Added `docs/model_overview.md`, `docs/assumptions.md`, and
  `docs/public_specs.md`.
- Updated `docs/mcp.md` for five tools.
- Updated `CLAUDE.md` for the fifth MCP tool and current branch policy.
- Updated `docs/review-policy.md` and `.github/PULL_REQUEST_TEMPLATE.md` to
  reflect Codex/human review.
- Removed `.github/workflows/claude.yml` and
  `.github/workflows/claude-review-response.yml` because both require a funded
  Anthropic API key.
- Updated the daily regression example list after moving the cost-oriented
  example to `_attic/`.

Verification:

- `uv run pytest` passed: `74 passed in 1.04s`.
- `uv build` passed.
- `uv run python examples/quickstart.py` passed.
- `uv run python examples/rack_sizing_example.py` passed.
- `rg -n -i "portfolio|cleanup" ...` returned no matches.

### Ruff and CI gate

Changed:

- Add Ruff to pip and uv dev dependencies.
- Add conservative Ruff config in `pyproject.toml`.
- Update CI to run tests, Ruff, smoke examples, and build.
- Applied `ruff check --fix .` and `ruff format .` once to make the new gate
  pass on existing active Python files.

Verification:

- `uv run pytest` passed: `74 passed in 0.97s`.
- `uv build` passed.
- `uv run python examples/quickstart.py` passed.
- `uv run python examples/rack_sizing_example.py` passed.
- `uv run ruff check .` passed.
- `uv run ruff format --check .` passed.

## Open Questions For Morning Review

- Whether `_attic/` should stay in the repository long term or only serve this
  review branch.
- Whether the Colab notebook should remain linked prominently after local
  quickstart examples exist.
- Whether the remaining manual Claude mention workflow should be restored later
  if funding resumes.

## Work Explicitly Skipped

- Package layout migration. The project already uses `src/thermal_mcp_server`,
  and moving modules would add risk without improving morning review value.
