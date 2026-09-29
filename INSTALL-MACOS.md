# macOS setup (Linux: optional manual setup)

1. Download and extract the [current main ZIP](https://github.com/metapak/claude-bounded-orchestrator/archive/refs/heads/main.zip). Older versioned packages may lack the current browser launcher. Keep the extracted folder for future edits.
2. Install a current [Claude Code client](https://code.claude.com/docs/en/getting-started) and Python 3.11 or newer. The launcher uses local Python; it does not bundle a runtime or install a background service.
3. On macOS, double-click `launchers/Bounded Orchestrator.app` in the extracted folder. Choose an existing local project directory in the native picker. Git is recommended for source work but is not required by the launcher.
4. In the browser, choose a work style and 1–10 real helper slots with duty, model, and effort. Duplicate duties are allowed. Press **Check changes**, then **Install**. Conflicting managed files stop for review; unrelated settings are preserved and backups stay ignored by Git.
5. Restart Claude Code in the project. Later, reopen the launcher to **Save** a changed team or **Restore** the preceding console-managed change. **Close console** stops the local server.

Linux has no double-click GUI launcher; use the optional manual steps below. If macOS blocks the unnotarized app, use those steps too. Native Finder double-click behavior has not been verified in every environment, and repository tests do not prove a live Claude Code session.

<details>
<summary>Optional terminal, Linux, external-provider, and uninstall steps</summary>

Run the direct installer from the extracted folder:

```bash
python3 scripts/install.py /path/to/project --dry-run
python3 scripts/install.py /path/to/project
```

You may also run `./setup.command` after making it executable. It asks for the target folder, install/preview/uninstall action, native profile, and optional external proposal provider. Existing settings and conflicting files are preserved by default. Review `.claude/bounded-orchestrator.settings.example.json` if the target already had settings.

The guided screen explains balanced, quality, economy, quota saver, and per-role custom settings, then shows a final configuration review and next steps. Every native/custom role must use an Anthropic Claude alias or full `claude-*` ID. The Python command remains non-interactive.

External APIs default to none. To explicitly add a proposal-only provider, set its key in the shell that launches Claude Code and run one of:

```bash
export OPENAI_API_KEY="your key"
python3 scripts/install.py /path/to/project --external-openai --external-model gpt-5.6-sol --external-effort high
export DEEPSEEK_API_KEY="your key"
python3 scripts/install.py /path/to/project --external-provider deepseek --external-model deepseek-flash --external-effort high
```

API keys are inherited at runtime and are never written to project files. The external provider is proposal-only; native Claude remains the sole writer.

Later non-interactive runs preserve the existing provider choice when no provider flag is supplied. Use `--external-provider none`, `--no-external-openai`, or `--no-external-deepseek` to remove only an unchanged installer-owned MCP entry and bridge. Modified entries are kept with a warning.

To remove unchanged installed files:

```bash
python3 scripts/install.py /path/to/project --uninstall --dry-run
python3 scripts/install.py /path/to/project --uninstall
```

The runtime `.gitignore` remains in place to keep any retained ledger state and backups out of Git.

</details>
