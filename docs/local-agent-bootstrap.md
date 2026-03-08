# Local Agent Bootstrap Prompt

Use this prompt with your local Claude Code or Codex instance when you want it
to align with this repo's persistent memory model and your agent-based workflow.

## Summary

This prompt tells a local agent:

- what durable memory was added to the repo
- where to look first for project context
- how to separate repo memory from local personal memory
- how to report what it learned and what it changed

## Bootstrap prompt

```text
You are working on the thermal-mcp-server repository.

Before doing any task, build context from the repo in this order:
1. Read AGENTS.md
2. Read CLAUDE.md
3. Read docs/agent-notes.md
4. Read docs/decisions.md
5. Inspect the relevant code and tests

Treat repo memory as the canonical shared memory layer. Do not rely on chat
history for anything that should survive across sessions or across agents.

Memory model for this project:
- AGENTS.md = tool-neutral cross-agent contract
- CLAUDE.md = detailed workflow and modeling guardrails
- docs/agent-notes.md = current branch/session continuity and queued work
- docs/decisions.md = durable architectural and modeling decisions

Working rules:
- Keep physics logic in src/thermal_mcp_server/physics.py
- Keep MCP wrappers thin in src/thermal_mcp_server/mcp_server.py
- Any physics change must update docs/physics.md and tests
- If defaults or correlation behavior change, add or update a hand-calculation test
- Do not weaken numerical tolerances without explicit approval

When you start a task, summarize:
- what the repo says the current priorities are
- what memory files you used
- any assumptions you are making

When you finish a task, report:
- what files you changed
- whether the change should also update docs/agent-notes.md
- whether any durable decision should be promoted into docs/decisions.md
- what tests or checks you ran

If I ask what changed in the project memory setup, answer with:
- the purpose of AGENTS.md
- the purpose of docs/decisions.md
- how these differ from CLAUDE.md and docs/agent-notes.md
- how this improves cross-agent continuity and remote-agent reliability

If I ask how to query this setup, answer by pointing me to:
- AGENTS.md for shared operating rules
- CLAUDE.md for detailed workflow constraints
- docs/agent-notes.md for current work state
- docs/decisions.md for durable decisions

If local machine memory exists, treat it as user-specific preference memory,
not as the source of truth for this repo.
```

## Useful follow-up queries for a local agent

Ask your local agent:

- `Summarize the project memory model for this repo.`
- `What are the current priorities according to the repo memory files?`
- `What durable decisions already exist, and which ones are still only in agent-notes?`
- `Before editing code, tell me which memory files you read and what constraints they impose.`
- `After this task, what should be updated in agent-notes versus decisions?`

## Workflow benefit

This setup improves agent-based development by:

- reducing re-explaining at the start of each session
- making remote and local agents converge on the same project context
- separating temporary task context from durable decisions
- keeping personal preferences local without polluting repo-level truth
