# Changelog

All notable changes are documented here.

## [0.3.0] - 2026-09-10

- Added interactive `balanced`, `quality`, `economy`, and per-role `custom` installation profiles.
- Added repeatable non-interactive role model and effort overrides.
- Added an optional dependency-free OpenAI Responses API MCP bridge for bounded implementation proposals.
- Kept the external model proposal-only so the native Claude implementer remains the single workspace writer.
- Added safe `.mcp.json` merging and surgical uninstall without persisting `OPENAI_API_KEY`.
- Added MCP protocol, mocked provider HTTP, profile, interaction, conflict, uninstall, and secret-absence tests.
- Distinguished omitted and explicit OpenAI disable choices, preserving existing selections while safely removing unchanged installer-owned integration files on request.
- Hardened owner-effort validation and malformed `.mcp.json` root handling before release.

## [0.2.0] - 2026-09-10

- Set the main owner to the `opus` alias with `xhigh` effort.
- Added explicit `opus`/`sonnet` aliases and `medium`/`high`/`xhigh` effort levels for every project agent.
- Added validation and installer tests that prevent role routing from drifting.
- Documented settings preservation, override precedence, and account-dependent model access.

## [0.1.0] - 2026-09-10

- Initial Claude Code project-agent workflow with bounded delegation and one writer per scope.
- Added a metadata-only task ledger with dependencies, atomic private writes, and completion gating.
- Added opt-in UI design and secure-change expertise.
- Added safe install, preview, backup, and uninstall flows.
- Added source, macOS/Linux, and Windows package generation plus cross-platform CI.
- Hardened uninstall path validation, expanded installed workflow rules, and retained the runtime ignore file so private ledger and backup data stay untracked after uninstall.
