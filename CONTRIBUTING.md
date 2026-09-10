# Contributing

Focused bug reports, documentation improvements, and small pull requests are welcome.

1. Open an issue for material behavior or architecture changes.
2. Keep one concern per pull request and preserve the one-writer, one-level, finite-retry, and exact-authority invariants.
3. Do not add telemetry, external services, dependencies, or secret-bearing ledger fields.
4. Run `python scripts/validate.py` and `python -m unittest discover -s tests -v`.
5. Explain the trigger, resulting behavior, validation, and remaining limits in the pull request.

Contributions are accepted under Apache-2.0. Preserve existing NOTICE attribution and add attribution when required by reused material.
