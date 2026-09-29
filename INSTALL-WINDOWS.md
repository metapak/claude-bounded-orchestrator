# Windows setup

1. Download and extract the [current main ZIP](https://github.com/metapak/claude-bounded-orchestrator/archive/refs/heads/main.zip). Older versioned packages may lack the current browser launcher. Keep the extracted folder for future edits.
2. Install a current [Claude Code client](https://code.claude.com/docs/en/getting-started) and Python 3.11 or newer. The launcher uses local Python; it does not bundle a runtime or install a background service.
3. Double-click `launchers/Launch Bounded Orchestrator.vbs` in the extracted folder. Choose an existing local project directory in the native picker. Git is recommended for source work but is not required by the launcher.
4. In the browser, choose a work style and 1–10 real helper slots with duty, model, and effort. Duplicate duties are allowed. Press **Check changes**, then **Install**. Conflicting managed files stop for review; unrelated settings are preserved and backups stay ignored by Git.
5. Restart Claude Code in the project. Later, reopen the launcher to **Save** a changed team or **Restore** the preceding console-managed change. **Close console** stops the local server.

Native Windows double-click behavior has not been verified on Windows, and repository tests do not prove a live Claude Code session.

<details>
<summary>Optional PowerShell, external-provider, and uninstall steps</summary>

Run the PowerShell installer from the extracted folder:

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

</details>
