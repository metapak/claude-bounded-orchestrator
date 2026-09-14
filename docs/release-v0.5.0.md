[English](release-v0.5.0.md) | [Türkçe](release-v0.5.0.tr.md)

# v0.5.0 release notes

- Adds honest usage reporting from an explicitly supplied sanitized OpenTelemetry export, with `/usage` fallback when unavailable.
- Adds a Claude-only `quota-saver` profile while keeping balanced as the default and retaining independent review.
- Adds an explicit shell-free local evaluation runner and opt-in completion gate.
- Adds non-destructive ledger migration, stable attempts/events, interruption and repair states, one bounded retry, derived status, and owner route-back metadata.

No telemetry or evaluation command is enabled automatically.
