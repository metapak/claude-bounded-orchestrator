# Mac setup (Linux below)

Have [Claude Code](https://code.claude.com/docs/en/getting-started) and [Python 3.11 or newer](https://www.python.org/downloads/) installed. Python is not included.

1. **Download:** [Get the current ZIP](https://github.com/metapak/claude-bounded-orchestrator/archive/refs/heads/main.zip) and open the extracted folder.
2. **Open:** Open `launchers` and double-click **Bounded Orchestrator.app**.
3. **Choose a project:** Pick the folder where you use Claude Code.
4. **Install:** In the browser, keep the suggested team or change it. Click **Check changes**, then **Install**. Restart Claude Code in that project.

For later changes, reopen the app and click **Save**; no uninstall is needed. An already-open Claude Code session may need to be reopened before it uses the changes. If macOS blocks the unsigned app, Control-click it and choose **Open**. Keep the app inside the extracted folder beside the launcher script and setup files. If macOS opens the app from a temporary location, step 1/2 asks for the extracted setup package in Downloads containing `launchers` and `scripts`. A wrong choice explains the difference and lets you try again. Step 2/2 asks for the separate Git project where you use Claude Code; settings go to that project, then setup continues in the browser. If the browser cannot open, an alert shows the full local address to open manually.

## Linux: the same four steps

Use the same [current ZIP](https://github.com/metapak/claude-bounded-orchestrator/archive/refs/heads/main.zip) and prerequisites. Linux has no double-click launcher or folder picker in this package. For **Open** and **Choose a project**, open a terminal in the extracted folder and include your project folder in this command:

```bash
python3 scripts/configure.py /absolute/path/to/your-project
```

In the browser, click **Check changes**, then **Install**. Later, repeat the command and use **Save**; no uninstall is needed. Reopen an already-running Claude Code session if it does not use the new settings.

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
