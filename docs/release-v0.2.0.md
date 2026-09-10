[English](release-v0.2.0.md) | [Türkçe](release-v0.2.0.tr.md)

# Claude Bounded Orchestrator v0.2.0

Version 0.2.0 makes the intended model family and reasoning effort explicit for every role without pinning dated model IDs.

## Routing

| Role | Model alias | Effort |
|---|---|---|
| Main owner | `opus` | `xhigh` |
| Explorer | `sonnet` | `medium` |
| Researcher | `sonnet` | `medium` |
| Implementer | `sonnet` | `high` |
| Verifier | `sonnet` | `high` |
| QA operator | `sonnet` | `high` |
| Failure analyst | `opus` | `high` |
| Reviewer | `opus` | `high` |
| Advisor | `opus` | `xhigh` |

## Upgrade behavior

A fresh install writes the main owner defaults to `.claude/settings.json`. If that file already exists, the installer preserves it and writes `.claude/bounded-orchestrator.settings.example.json` for manual review and merging. Agent files remain conflict-preserving unless `--force` is explicitly selected.

Environment variables and per-session or per-invocation options can override project settings. Agent frontmatter defines intended role routing where supported; environment effort configuration can still take precedence. Model access and supported effort levels depend on the account and current Claude Code client.

## Verification boundary

Static validation and tests assert the complete routing map so settings and documentation changes cannot silently drift from agent definitions. Live selection remains a Claude Code runtime behavior and should be checked with the documented smoke test.
