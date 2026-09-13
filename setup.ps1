param([string]$Target)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Claude Bounded Orchestrator Setup"
Write-Host "+=================================================================="
Write-Host "| Claude Bounded Orchestrator - guided installer                  |"
Write-Host "| Native team: Anthropic Claude only                              |"
Write-Host "+=================================================================="
if (-not $Target) {
    Write-Host ""
    Write-Host "Paste or drag the target project folder here."
    $DefaultTarget = (Get-Location).Path
    $InputTarget = Read-Host "Target [$DefaultTarget]"
    $Target = if ($InputTarget) { $InputTarget.Trim('"') } else { $DefaultTarget }
}
Write-Host ""
Write-Host "Action"
Write-Host "  1. Safe install or update"
Write-Host "  2. Dry-run preview (no files changed)"
Write-Host "  3. Uninstall unchanged managed files"
$Action = Read-Host "Select [1]"
if (-not $Action) { $Action = "1" }
switch ($Action) {
    "1" { & (Join-Path $PSScriptRoot "scripts/install.ps1") -Target $Target -Interactive }
    "2" { & (Join-Path $PSScriptRoot "scripts/install.ps1") -Target $Target -Interactive -DryRun }
    "3" { & (Join-Path $PSScriptRoot "scripts/install.ps1") -Target $Target -Uninstall }
    default { Write-Error "Choose 1, 2, or 3."; exit 2 }
}
exit $LASTEXITCODE
