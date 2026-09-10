# macOS and Linux installation

Install a current [Claude Code client](https://code.claude.com/docs/en/getting-started) and Python 3.11 or newer. From this downloaded repository:

```bash
python3 scripts/install.py /path/to/project --dry-run
python3 scripts/install.py /path/to/project
```

You may also run `./setup.command /path/to/project` after making it executable. Existing settings and conflicting files are preserved by default. Review `.claude/bounded-orchestrator.settings.example.json` if the target already had settings.

`setup.command` opens a Turkish selection screen for balanced, quality, economy, or per-role custom model/effort settings. The Python command remains non-interactive; use `--preset quality`, `--preset economy`, or repeat `--role-model ROLE=MODEL` and `--role-effort ROLE=EFFORT` as needed.

To add the proposal-only OpenAI role, select it in the guided setup or set `OPENAI_API_KEY` in the shell that launches Claude Code and run:

```bash
python3 scripts/install.py /path/to/project --external-openai --external-model gpt-5.6-sol --external-effort high
```

The API key is inherited at runtime and is never written to project files.

To remove unchanged installed files:

```bash
python3 scripts/install.py /path/to/project --uninstall --dry-run
python3 scripts/install.py /path/to/project --uninstall
```

The runtime `.gitignore` remains in place to keep any retained ledger state and backups out of Git.
