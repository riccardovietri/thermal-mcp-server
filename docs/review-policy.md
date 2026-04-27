# PR Review Policy

## Four-stage gate

Every non-trivial PR must pass four stages before merge:

### 1. Authoring
Code may be written by a human or an AI agent.  
The PR description must state: what changed, why, what was tested, known limitations.  
Use the PR template.

### 2. Review
The Claude review job runs automatically on every PR.  
It checks: correctness, regressions, API compatibility, test coverage, docs drift, release risk.  
Review is not optional commentary — it must be read before merge.

### 3. Triage and remediation
Every **[BLOCKING]** finding must be explicitly marked as one of:
- **fixed** — PR author or fix agent applied the change
- **waived** — PR author leaves a short rationale in the PR thread
- **not applicable** — PR author explains why the finding does not apply

**[SUGGESTION]** findings require no action. They may be applied at the author's discretion.

### 4. Merge approval
A human is responsible for the final merge decision.  
A PR may be merged only when:
- CI is green
- Build passes
- All [BLOCKING] findings have been triaged (fixed / waived / N/A)
- Residual risks are consciously accepted

## Severity rules

| Label | Meaning | Required action |
|-------|---------|-----------------|
| `[BLOCKING]` | Correctness bug, regression, broken test, or release risk | Fix or explicitly waive before merge |
| `[SUGGESTION]` | Style, minor improvement, optional enhancement | No action required |

## Agent role split

| Role | Who | Scope |
|------|-----|-------|
| Author agent | Claude Code / Codex / human | Writes code, docs, tests |
| Review agent | Claude Code Review workflow | Read-only, posts labeled findings |
| Fix agent | Claude Review Response workflow | Applies accepted [BLOCKING] fixes, runs tests, posts summary |
| Merge approver | Human only | Final merge decision |

**No agent auto-merges. No agent self-approves.**

## Operational rules

- No merging before reading AI review findings.
- No "looks good" without concrete findings or an explicit "no findings" statement.
- Behavior-changing PRs must update docs if public behavior, workflow, or API changed.
- Physics/model changes must include analytical or hand-calc validation (see CLAUDE.md).

## Branch protection (manual GitHub setup required)

Recommended settings for this repo:
- Require pull request before merging
- Require status checks to pass: `CI / test`
- Require conversation resolution before merging
- No direct pushes to `main`

These cannot be set by an agent — a repo admin must configure them in  
**Settings → Branches → Branch protection rules**.
