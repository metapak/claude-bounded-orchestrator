param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Target,
    [switch]$DryRun,
    [switch]$Force,
    [switch]$ForceSettings,
    [switch]$Uninstall,
    [switch]$Interactive,
    [ValidateSet("balanced", "quality", "economy", "custom")]
    [string]$Preset = "balanced",
    [string[]]$RoleModel,
    [string[]]$RoleEffort,
    [switch]$ExternalOpenAI,
    [switch]$NoExternalOpenAI,
    [string]$ExternalModel = "gpt-5.6-sol",
    [string]$ExternalEffort = "high"
)

$ErrorActionPreference = "Stop"
if ($ExternalOpenAI -and $NoExternalOpenAI) {
    throw "ExternalOpenAI and NoExternalOpenAI cannot be used together."
}
$Installer = Join-Path $PSScriptRoot "install.py"
$Arguments = @($Installer, $Target)
if ($DryRun) { $Arguments += "--dry-run" }
if ($Force) { $Arguments += "--force" }
if ($ForceSettings) { $Arguments += "--force-settings" }
if ($Uninstall) { $Arguments += "--uninstall" }
if ($Interactive) { $Arguments += "--interactive" }
$Arguments += @("--preset", $Preset)
foreach ($Value in $RoleModel) { $Arguments += @("--role-model", $Value) }
foreach ($Value in $RoleEffort) { $Arguments += @("--role-effort", $Value) }
if ($ExternalOpenAI) { $Arguments += "--external-openai" }
if ($NoExternalOpenAI) { $Arguments += "--no-external-openai" }
$Arguments += @("--external-model", $ExternalModel, "--external-effort", $ExternalEffort)

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @Arguments
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python @Arguments
} else {
    throw "Python 3.11 or newer is required."
}
exit $LASTEXITCODE
