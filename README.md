[English](README.md) · [Türkçe](README.tr.md)

# Claude Bounded Orchestrator

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/downloads/)

**A small, reviewable team structure for complex Claude Code work.**

Claude Bounded Orchestrator gives the main Claude session clear ownership, separates investigation from implementation, keeps one writer per scope, and requires independent verification before completion. A private local ledger tracks short task metadata so dependent steps are less likely to be skipped.

You still ask for work in normal language. The project supplies the operating rules behind the scenes.

![Claude Bounded Orchestrator role tree showing the owner and bounded responsibilities](docs/assets/claude-bounded-orchestrator-roles-tr.png)

The visual overview uses short Turkish labels. Version 0.2.0 assigns Claude model-family aliases and effort by role; the exact routing is listed below.

```mermaid
flowchart LR
    U[You describe the outcome] --> O[Main Claude session owns the work]
    O --> E[Explore or research]
    E --> I[One implementer writes]
    I --> V[Verifier checks evidence]
    V --> R[Reviewer inspects frozen candidate]
    R --> O
    O --> D[Finished result]
```

## Why use it?

- **One accountable owner:** the main session decides scope, routing, integration, and the final result.
- **One writer per scope:** only the implementer receives `Edit` and `Write` tools.
- **Independent checks:** verification and review are separate from implementation.
- **Bounded delegation:** project agents cannot create more agents; native spawn depth is capped at `1`.
- **Finite repair loops:** failed verification or review can trigger a focused repair, not an endless loop.
- **Completion gating:** dependencies and unfinished work remain visible in a lightweight local ledger.
- **Optional expertise:** UI design and security guidance are available only when explicitly invoked and grant no tools.
- **Safe installation:** existing Claude settings and conflicting managed files are preserved by default.

## Quick start

Requirements:

- A current [Claude Code installation](https://code.claude.com/docs/en/getting-started)
- Python 3.11 or newer

Clone or download this repository, then preview installation into your project:

```bash
python scripts/install.py /path/to/your-project --dry-run
python scripts/install.py /path/to/your-project
```

On Windows PowerShell:

```powershell
.\scripts\install.ps1 -Target C:\path\to\your-project -DryRun
.\scripts\install.ps1 -Target C:\path\to\your-project
```

Open the target project in Claude Code and describe the outcome normally:

```text
Find why checkout sometimes creates duplicate orders, fix it, verify the repair,
and review the final candidate before reporting completion.
```

For a multi-step workflow, Claude can use the local ledger:

```bash
python .claude/tools/task_ledger.py init
python .claude/tools/task_ledger.py add MAP --summary "Map checkout flow" --role explorer
python .claude/tools/task_ledger.py add FIX --summary "Implement approved repair" --role implementer --depends-on MAP
python .claude/tools/task_ledger.py show
```

The ledger is ignored by Git and stores only short metadata. Do not place prompts, source code, logs, command output, credentials, personal data, or secrets in it.

## What gets installed

```text
.claude/
├── agents/                  # bounded project agents
├── skills/                  # opt-in UI and security guidance
├── tools/task_ledger.py     # metadata-only task tracking
├── settings.json            # owner model/effort and depth cap on a fresh install
└── .bounded-orchestrator/   # ignored manifest, backups, and ledger state
CLAUDE.md                    # a marked, removable instruction block
```

If `.claude/settings.json` already exists, the installer preserves it and writes `bounded-orchestrator.settings.example.json` for manual merging. Merge the `model`, `effortLevel`, and `env` entries you want. Use `--force-settings` only after reviewing the backup plan. Conflicting managed files are also preserved unless `--force` is chosen.

Uninstall unchanged files created by the installer:

```bash
python scripts/install.py /path/to/your-project --uninstall --dry-run
python scripts/install.py /path/to/your-project --uninstall
```

Files changed after installation are kept. The runtime `.gitignore` is also retained so any remaining ledger state or backups stay untracked.

## Roles

| Role | Purpose | Model alias | Effort | Edit/Write |
|---|---|---|---|---:|
| Main Claude session | Owns scope, decisions, integration, and outcome | `opus` | `xhigh` | Uses normal session permissions |
| Explorer | Maps code paths and constraints | `sonnet` | `medium` | No |
| Researcher | Verifies current external facts | `sonnet` | `medium` | No |
| Implementer | Makes one assigned change | `sonnet` | `high` | Yes |
| Verifier | Runs focused evidence checks | `sonnet` | `high` | No |
| Failure analyst | Explains one evidenced failure | `opus` | `high` | No |
| QA operator | Observes a bounded runtime flow | `sonnet` | `high` | No |
| Reviewer | Reviews a frozen candidate independently | `opus` | `high` | No |
| Advisor | Advises on one high-risk decision | `opus` | `xhigh` | No |

Aliases select the current Claude family instead of pinning a dated model ID. Model access and supported effort levels depend on your account and current Claude Code client. Environment variables and per-session or per-invocation options can take precedence over project settings; agent frontmatter sets the intended role routing where supported.

## Supported platforms and honest limits

The installer and release builder use the Python 3.11 standard library. Shell launchers are provided for macOS/Linux and PowerShell/cmd launchers for Windows. Repository tests exercise installer, ledger, validation, and release packaging behavior; CI is configured for macOS, Windows, and Ubuntu.

This project does not turn model instructions into a security boundary. The native depth setting and tool allowlists are concrete Claude Code controls; role sequence, one-writer discipline, frozen review, and retry limits remain instructions followed by the model. `Bash` can mutate state even when `Edit` and `Write` are unavailable, so verifier and QA instructions restrict it to evidence gathering. Run a live smoke test with your current Claude Code client before relying on the workflow.

## Documentation

- [Architecture and safety rationale](docs/architecture.md)
- [Examples](docs/examples.md)
- [FAQ and troubleshooting](docs/faq.md)
- [Roadmap](docs/roadmap.md)
- [Runtime smoke test](docs/runtime-smoke-test.md)
- [v0.2.0 release notes](docs/release-v0.2.0.md)
- [macOS/Linux installation](INSTALL-MACOS.md)
- [Windows installation](INSTALL-WINDOWS.md)
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

## Project status

Version `0.2.0` adds explicit model-family and effort routing while preserving the bounded workflow introduced in 0.1.0. The project adapts [Codex Bounded Orchestrator](https://github.com/metapak/codex-bounded-orchestrator) to Claude Code's native project agents, skills, shared instructions, and settings. See [NOTICE](NOTICE) and [provenance](docs/provenance.md) for attribution.

If the project helps your team, a GitHub star helps other people discover it. Issues and focused pull requests are welcome.

## License

Apache License 2.0. See [LICENSE](LICENSE).
