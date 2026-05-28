param(
    [string]$Spec = "",
    [string]$SourceHmi = "",
    [string]$PatchPlan = "",
    [string]$OutDir = "",
    [string]$Name = "",
    [string]$OfficialDir = "",
    [switch]$Flash,
    [switch]$NoFlash,
    [switch]$Camera,
    [switch]$SerialSmoke,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"
$ToolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ToolDir
$ConfigPath = Join-Path $Root "config\local.headless.json"

if (Test-Path -LiteralPath $ConfigPath -PathType Leaf) {
    $Config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    if ($Config.official_install_dir -and -not $OfficialDir) {
        $env:USARTHMI_OFFICIAL_DIR = [string]$Config.official_install_dir
    }
    if ($Config.headless_runtime_root) {
        $env:USARTHMI_HEADLESS_RUNTIME_ROOT = [string]$Config.headless_runtime_root
    }
}
if ($OfficialDir) {
    $env:USARTHMI_OFFICIAL_DIR = $OfficialDir
}

$Python = Get-Command py -ErrorAction SilentlyContinue
$PythonCommand = @()
if ($Python) {
    $PythonCommand = @($Python.Source, "-3")
} else {
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $Python) {
        throw "Python 3.10+ was not found. Run touchsafe_headless_bootstrap.ps1 first."
    }
    $PythonCommand = @($Python.Source)
}

$ArgsList = @((Join-Path $Root "tools\codex_touchsafe_official_pipeline.py"))
if ($Spec) { $ArgsList += @("--spec", $Spec) }
if ($SourceHmi) { $ArgsList += @("--source-hmi", $SourceHmi) }
if ($PatchPlan) { $ArgsList += @("--patch-plan", $PatchPlan) }
if ($OutDir) { $ArgsList += @("--out-dir", $OutDir) }
if ($Name) { $ArgsList += @("--name", $Name) }
if ($OfficialDir) { $ArgsList += @("--install-dir", $OfficialDir) }
if ($Flash) { $ArgsList += "--flash" }
if ($NoFlash) { $ArgsList += "--no-flash" }
if ($Camera) { $ArgsList += "--camera" }
if ($SerialSmoke) { $ArgsList += "--serial-smoke" }
if ($ExtraArgs) { $ArgsList += $ExtraArgs }

$PrefixArgs = @()
if ($PythonCommand.Count -gt 1) {
    $PrefixArgs = $PythonCommand[1..($PythonCommand.Count - 1)]
}
& $PythonCommand[0] @PrefixArgs @ArgsList
exit $LASTEXITCODE
