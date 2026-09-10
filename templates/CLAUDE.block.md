<!-- claude-bounded-orchestrator:start -->
## Bounded orchestration

Use the project agents in `.claude/agents/` for complex work. The main Claude session owns scope, architecture, routing, integration, finding triage, and the final outcome. Only `implementer` writes, with one writer per explicitly assigned file or scope. Children must not delegate.

Every delegated request must name its objective, exact scope, write ownership or read-only status, relevant context, invariants, deliverable, acceptance criteria, and stop conditions. Agents return evidence to the main session and do not own the final result.

Before independent review, stop all writers and freeze the candidate by recording an exact commit or deterministic worktree identity. Give the reviewer that identity and reject its review if the candidate changes. The reviewer returns findings only and must not contact the implementer.

Allow at most one focused repair for a proven verification failure and at most one focused repair for accepted material review findings. Do not retry the same failed contract without new evidence or a narrower method.

For workflows with three or more dependent steps, use `.claude/tools/task_ledger.py`. The ledger stores short metadata only and must never contain prompts, source code, command output, logs, credentials, personal data, or secrets. Do not claim completion until all required agents have stopped, ledger dependencies are complete, `check` passes, the final candidate still matches the reviewed identity, accepted findings are resolved or disclosed, and the highest-value checks pass.

External effects require the user's exact authority. Optional `/ui-design` and `/secure-change` skills add guidance only when explicitly invoked; they do not grant tools or permissions.

If the optional `openai_bounded_implementation` MCP tool is configured, treat it as a proposal-only external implementer. Give it an exact task, repository-relative allowed paths, reviewed context, constraints, and acceptance criteria. It cannot inspect or write the workspace. The native `implementer` remains the sole writer: it must review the returned patch, reject out-of-scope changes, apply only accepted edits, and run the normal verification and frozen-review flow. Never include credentials or unrelated source in the supplied context.
<!-- claude-bounded-orchestrator:end -->
