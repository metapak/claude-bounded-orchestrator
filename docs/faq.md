# FAQ and troubleshooting

## Does this replace Claude Code?

No. It is a project configuration and workflow for a current Claude Code installation.

## Does it choose a specific Claude model?

It chooses model-family aliases and effort levels by role: the main owner uses `opus`/`xhigh`; exploration and routine implementation use `sonnet`; difficult failure analysis and independent review use `opus`. These aliases do not pin a dated model ID. Availability and supported effort levels depend on your account and current Claude Code client.

## Is one-writer enforcement absolute?

Only `implementer` receives `Edit` and `Write`, and children cannot delegate. This is a useful concrete restriction, but shell access can still mutate a workspace. Verifier and QA retain `Bash` for evidence checks and are instructed to avoid mutation. Use normal permissions and isolated environments when stronger guarantees are required.

## Why was my existing settings file not changed?

The installer preserves `.claude/settings.json` by default because replacing it could discard hooks, permissions, environment values, or other project configuration. It writes `.claude/bounded-orchestrator.settings.example.json`; merge the desired `model`, `effortLevel`, and `env` entries after review. `--force-settings` creates a backup and replaces the file.

## Can I override the selected model or effort?

Yes. Claude Code environment variables and per-session or per-invocation options can take precedence over project settings. Agent frontmatter supplies the intended role-level routing where supported, while environment effort configuration can still override it. Confirm the active model and effort in your current client when exact routing matters.

The installer also supports `--preset balanced|quality|economy|custom`, plus repeatable `--role-model ROLE=MODEL` and `--role-effort ROLE=EFFORT` overrides. The one-click launchers show the same choices in Turkish.

## Can Claude use a GPT model in this workflow?

Yes, through the optional local MCP bridge and OpenAI Responses API. This is an external tool call, not a native Claude subagent model alias. Select it during guided setup or use `--external-openai`, then define `OPENAI_API_KEY` in the environment that launches Claude Code. The key is never stored by the installer.

The GPT role returns a proposal and cannot inspect or write the workspace. The native Claude implementer remains the only writer and reviews any proposed patch before applying it. If the MCP server name already has a different configuration, the installer preserves it and writes an example for manual review.

## Why does the OpenAI tool report that the key is missing?

Claude Code did not inherit `OPENAI_API_KEY`. Define the variable in the same terminal or operating-system environment used to start Claude Code, restart the client, and try again. Never place the key in `CLAUDE.md`, `.mcp.json`, prompts, or the task ledger.

## Why was an agent or skill skipped?

A different file already existed at the managed path. The safe default is to keep it. Compare the project version, then use `--force` if replacement is intentional; the installer stores an ignored backup first.

## Why will a task not start?

All entries named by `--depends-on` must be complete. Run:

```bash
python .claude/tools/task_ledger.py show
```

Complete the prerequisites or correct the plan by creating a new ledger with `init --force` if the previous plan is no longer valid.

## Why does `check` fail?

At least one task is pending, in progress, or blocked. This is the completion gate working as intended.

## Can the ledger contain detailed debugging output?

No. Keep detailed evidence in the normal working context or approved project artifacts. The ledger accepts only short summaries and must not contain prompts, source code, logs, command output, credentials, personal data, or secrets.

## How do I remove it?

Preview first:

```bash
python scripts/install.py /path/to/project --uninstall --dry-run
python scripts/install.py /path/to/project --uninstall
```

The uninstaller removes only unchanged files recorded as installer-owned and removes its marked block from `CLAUDE.md`. Modified files remain. It preserves `.claude/.bounded-orchestrator/.gitignore` so retained ledger state and backups remain untracked.

## Claude does not use the agents as expected

Confirm the files exist under the target project's `.claude/agents/`, the depth environment value is the string `"1"`, and you launched a current Claude Code client from that project. Then run the [runtime smoke test](runtime-smoke-test.md). Model behavior is probabilistic; the repository tests validate configuration and tools, not every live routing decision.
