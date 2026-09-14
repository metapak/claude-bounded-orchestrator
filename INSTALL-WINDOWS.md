# Windows installation

Install a current [Claude Code client](https://code.claude.com/docs/en/getting-started) and Python 3.11 or newer. In PowerShell, from this downloaded repository:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -DryRun
.\scripts\install.ps1 -Target C:\path\to\project
```

Or double-click `setup.cmd`. It asks for the target folder, install/preview/uninstall action, native profile, and optional external proposal provider. Existing settings and conflicting files are preserved by default. Review `.claude\bounded-orchestrator.settings.example.json` if the target already had settings.

The guided screen explains balanced, quality, economy, quota saver, or per-role custom settings, then shows a final configuration review and next steps. Every native/custom role must use an Anthropic Claude alias or full `claude-*` ID. The lower-level installer remains non-interactive:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -Preset quality
```

External APIs default to none. To explicitly add a proposal-only provider, define its key in the environment that launches Claude Code:

```powershell
$env:OPENAI_API_KEY = "your key"
.\scripts\install.ps1 -Target C:\path\to\project -ExternalOpenAI -ExternalModel gpt-5.6-sol -ExternalEffort high
$env:DEEPSEEK_API_KEY = "your key"
.\scripts\install.ps1 -Target C:\path\to\project -ExternalProvider deepseek -ExternalModel deepseek-flash -ExternalEffort high
```

API keys are inherited at runtime and are never written to project files. External providers are proposal-only; native Claude remains the sole writer.

Later non-interactive runs preserve the existing provider choice when no provider switch is supplied. Use `-ExternalProvider none`, `-NoExternalOpenAI`, or `-NoExternalDeepSeek` to remove only an unchanged installer-owned MCP entry and bridge. Modified entries are kept with a warning.

To remove unchanged installed files:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -Uninstall -DryRun
.\scripts\install.ps1 -Target C:\path\to\project -Uninstall
```

The runtime `.gitignore` remains in place to keep any retained ledger state and backups out of Git.
