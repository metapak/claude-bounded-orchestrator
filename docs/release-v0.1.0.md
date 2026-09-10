# Claude Bounded Orchestrator v0.1.0

Initial public-ready Claude Code edition.

## Included

- Eight bounded project agents with unique names and explicit tool lists.
- One-level native subagent spawn depth.
- One implementer with `Edit` and `Write`; separate evidence and review roles.
- Metadata-only local task ledger with dependency and completion gates.
- Opt-in UI design and secure-change skills that grant no tools.
- Idempotent, conflict-preserving installer and safe uninstaller.
- Source, macOS/Linux, and Windows release package builder.
- English and Turkish documentation.

## Verification boundary

Automated tests cover repository structure, agent metadata, installer lifecycle, ledger transitions, permissions, and release archives. Live model routing remains dependent on the current Claude Code client and should be checked with the documented smoke test.
