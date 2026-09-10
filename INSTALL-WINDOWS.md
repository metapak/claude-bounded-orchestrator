# Windows installation

Install a current [Claude Code client](https://code.claude.com/docs/en/getting-started) and Python 3.11 or newer. In PowerShell, from this downloaded repository:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -DryRun
.\scripts\install.ps1 -Target C:\path\to\project
```

Or double-click `setup.cmd` and pass a target path from a terminal. Existing settings and conflicting files are preserved by default. Review `.claude\bounded-orchestrator.settings.example.json` if the target already had settings.

`setup.ps1` and `setup.cmd` open a Turkish selection screen for balanced, quality, economy, or per-role custom model/effort settings. The lower-level installer remains non-interactive:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -Preset quality
```

To add the proposal-only OpenAI role, select it in guided setup or define `OPENAI_API_KEY` in the environment that launches Claude Code:

```powershell
$env:OPENAI_API_KEY = "your key"
.\scripts\install.ps1 -Target C:\path\to\project -ExternalOpenAI -ExternalModel gpt-5.6-sol -ExternalEffort high
```

The API key is inherited at runtime and is never written to project files.

To remove unchanged installed files:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -Uninstall -DryRun
.\scripts\install.ps1 -Target C:\path\to\project -Uninstall
```

The runtime `.gitignore` remains in place to keep any retained ledger state and backups out of Git.
