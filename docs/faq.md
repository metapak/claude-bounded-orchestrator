# FAQ and troubleshooting

## Does this replace Claude Code?

No. It is a project configuration and workflow for a current Claude Code installation.

## Does it choose a specific Claude model?

No. Project agents use `model: inherit`. Your Claude Code client and account determine the active model and availability.

## Is one-writer enforcement absolute?

Only `implementer` receives `Edit` and `Write`, and children cannot delegate. This is a useful concrete restriction, but shell access can still mutate a workspace. Verifier and QA retain `Bash` for evidence checks and are instructed to avoid mutation. Use normal permissions and isolated environments when stronger guarantees are required.

## Why was my existing settings file not changed?

The installer preserves `.claude/settings.json` by default because replacing it could discard hooks, permissions, environment values, or other project configuration. It writes `.claude/bounded-orchestrator.settings.example.json`; merge the `env` entry after review. `--force-settings` creates a backup and replaces the file.

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

The uninstaller removes only unchanged files recorded as installer-owned and removes its marked block from `CLAUDE.md`. Modified files remain.

## Claude does not use the agents as expected

Confirm the files exist under the target project's `.claude/agents/`, the depth environment value is the string `"1"`, and you launched a current Claude Code client from that project. Then run the [runtime smoke test](runtime-smoke-test.md). Model behavior is probabilistic; the repository tests validate configuration and tools, not every live routing decision.
