[English](release-v0.3.0.md) | [Türkçe](release-v0.3.0.tr.md)

# Claude Bounded Orchestrator v0.3.0

Version 0.3.0 makes model routing selectable during installation and adds an optional OpenAI implementation-proposal role.

## Highlights

- One-click launchers now offer `balanced`, `quality`, `economy`, and per-role `custom` profiles in a Turkish setup screen.
- Automation can use `--preset`, repeatable `--role-model ROLE=MODEL`, and `--role-effort ROLE=EFFORT` flags without prompts.
- An optional dependency-free stdio MCP bridge calls the OpenAI Responses API with a selected model and reasoning effort.
- `OPENAI_API_KEY` is read only from the runtime environment and is never persisted.
- The OpenAI role receives only supplied context and returns a proposal. It has no workspace access; the native Claude implementer remains the sole writer.
- Existing settings, managed-file conflicts, and MCP server entries are preserved. Uninstall removes only the unchanged entry or file installed by this project.
- Omitting the provider option preserves an earlier selection; guided “Hayır” or `--no-external-openai` explicitly disables only unchanged installer-owned integration files.
- Owner settings reject unsupported `max` effort before writing, while child-agent frontmatter can still select it.

The MCP protocol and provider request were tested end to end against a local mocked Responses API. A live paid request was not run because no API key was available in the release environment.
