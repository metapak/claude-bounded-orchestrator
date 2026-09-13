[English](release-v0.4.0.md) | [Türkçe](release-v0.4.0.tr.md)

# Claude Bounded Orchestrator v0.4.0

Version 0.4.0 keeps the native Claude team single-brand by design and makes every external model an explicit, proposal-only API choice.

## Highlights

- Balanced, quality, economy, and custom native routes now accept only `opus`, `sonnet`, `haiku`, or full `claude-*` model IDs.
- GPT, DeepSeek, and other provider IDs are rejected for native roles with guidance to use an external proposal provider.
- Guided setup defaults to no external provider and can explicitly select OpenAI GPT or DeepSeek V4.1 Flash.
- The new dependency-free DeepSeek bridge uses the current `deepseek-flash` API alias, validates model and effort values, caps supplied text, and reads `DEEPSEEK_API_KEY` only from the process environment.
- Both external providers have no workspace functions and return untrusted proposal text; the native Claude implementer remains the sole writer.
- macOS, Linux, and Windows launchers now show clearer target/action prompts, profile descriptions, API disclosure, a configuration review, install results, and next steps.
- Existing MCP servers, modified files, older OpenAI manifests, backups, dry runs, and surgical uninstall behavior remain supported.
- Release archives retain only `.claude/.bounded-orchestrator/.gitignore` from the private runtime directory; task state, locks, and backups are excluded.
- Uninstall now keeps a provider bridge when a user-modified MCP entry still depends on it, while unchanged provider installations are removed completely.

## Validation

Automated tests cover native-brand rejection, default provider state, OpenAI compatibility, DeepSeek MCP calls against a local mock server, payload bounds, secret absence, provider switching, uninstall safety, restrictive terminal encodings, and release archives. No paid live API request was made; account and regional availability must be verified by each user.
