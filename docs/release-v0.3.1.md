[English](release-v0.3.1.md) | [Türkçe](release-v0.3.1.tr.md)

# Claude Bounded Orchestrator v0.3.1

Version 0.3.1 fixes interactive installation on Windows terminals whose active output encoding cannot represent every Turkish character.

The installer now keeps Turkish text unchanged when the terminal supports it. On restrictive encodings such as CP1252, only unsupported characters are replaced instead of terminating setup with `UnicodeEncodeError`. Profile selection and installation continue normally.

This release includes a regression test that runs the complete balanced-profile interaction with strict CP1252 output and verifies successful installation. All v0.3.0 profile, OpenAI MCP, secret handling, conflict preservation, and bounded single-writer behavior remain unchanged.
