param([string]$Target = (Get-Location).Path)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "scripts/install.ps1") -Target $Target
exit $LASTEXITCODE
