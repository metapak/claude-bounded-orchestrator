# Windows installation

Install a current [Claude Code client](https://code.claude.com/docs/en/getting-started) and Python 3.11 or newer. In PowerShell, from this downloaded repository:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -DryRun
.\scripts\install.ps1 -Target C:\path\to\project
```

Or double-click `setup.cmd` and pass a target path from a terminal. Existing settings and conflicting files are preserved by default. Review `.claude\bounded-orchestrator.settings.example.json` if the target already had settings.

To remove unchanged installed files:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -Uninstall -DryRun
.\scripts\install.ps1 -Target C:\path\to\project -Uninstall
```
