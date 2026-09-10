# macOS and Linux installation

Install a current [Claude Code client](https://code.claude.com/docs/en/getting-started) and Python 3.11 or newer. From this downloaded repository:

```bash
python3 scripts/install.py /path/to/project --dry-run
python3 scripts/install.py /path/to/project
```

You may also run `./setup.command /path/to/project` after making it executable. Existing settings and conflicting files are preserved by default. Review `.claude/bounded-orchestrator.settings.example.json` if the target already had settings.

To remove unchanged installed files:

```bash
python3 scripts/install.py /path/to/project --uninstall --dry-run
python3 scripts/install.py /path/to/project --uninstall
```
