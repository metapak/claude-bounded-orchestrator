# Changelog

All notable changes are documented here.

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
