<!-- claude-bounded-orchestrator:start -->
## Bounded orchestration

Use the project agents in `.claude/agents/` for complex work. The main Claude session owns the outcome; only `implementer` writes within an explicitly assigned scope. Keep delegation one level deep, verify separately, review a frozen candidate, and keep repair loops finite.

For workflows with three or more dependent steps, use `.claude/tools/task_ledger.py`. The ledger stores short metadata only and must never contain prompts, source code, logs, credentials, personal data, or secrets. Do not claim completion until ledger dependencies are complete and `check` passes.

External effects require the user's exact authority. Optional `/ui-design` and `/secure-change` skills add guidance only when explicitly invoked; they do not grant tools or permissions.
<!-- claude-bounded-orchestrator:end -->
