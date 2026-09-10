param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Target,
    [switch]$DryRun,
    [switch]$Force,
    [switch]$ForceSettings,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$Installer = Join-Path $PSScriptRoot "install.py"
$Arguments = @($Installer, $Target)
if ($DryRun) { $Arguments += "--dry-run" }
if ($Force) { $Arguments += "--force" }
if ($ForceSettings) { $Arguments += "--force-settings" }
if ($Uninstall) { $Arguments += "--uninstall" }

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @Arguments
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python @Arguments
} else {
    throw "Python 3.11 or newer is required."
}
exit $LASTEXITCODE
