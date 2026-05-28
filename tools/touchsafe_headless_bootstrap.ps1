param(
    [string]$OfficialDir = "",
    [string]$RuntimeRoot = "",
    [switch]$SkipPipInstall,
    [switch]$InstallSkill,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$ToolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ToolDir

function Find-OfficialDir {
    param([string]$ExplicitDir)
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($ExplicitDir) { $candidates.Add($ExplicitDir) }
    if ($env:USARTHMI_OFFICIAL_DIR) { $candidates.Add($env:USARTHMI_OFFICIAL_DIR) }
    if (${env:ProgramFiles(x86)}) { $candidates.Add((Join-Path ${env:ProgramFiles(x86)} "USART HMI")) }
    if ($env:ProgramFiles) { $candidates.Add((Join-Path $env:ProgramFiles "USART HMI")) }

    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        $exe = Join-Path $candidate "USART HMI.exe"
        $actr = Join-Path $candidate "ACTR.dll"
        if ((Test-Path -LiteralPath $exe -PathType Leaf) -and (Test-Path -LiteralPath $actr -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Official USART HMI install not found. Pass -OfficialDir or set USARTHMI_OFFICIAL_DIR."
}

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @($py.Source, "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @($python.Source) }
    throw "Python 3.10+ was not found. This source package requires Python; build a standalone bundle for no-Python targets."
}

function Invoke-PackagePython {
    param([string[]]$PythonCommand, [string[]]$Arguments)
    $PrefixArgs = @()
    if ($PythonCommand.Count -gt 1) {
        $PrefixArgs = $PythonCommand[1..($PythonCommand.Count - 1)]
    }
    & $PythonCommand[0] @PrefixArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Arguments -join ' ')"
    }
}

$ResolvedOfficialDir = Find-OfficialDir -ExplicitDir $OfficialDir
$PythonCommand = Find-Python

$VersionCode = "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
Invoke-PackagePython -PythonCommand $PythonCommand -Arguments @("-c", $VersionCode)

if ($RuntimeRoot) {
    $env:USARTHMI_HEADLESS_RUNTIME_ROOT = $RuntimeRoot
}
$env:USARTHMI_OFFICIAL_DIR = $ResolvedOfficialDir

if (-not $SkipPipInstall -and -not $CheckOnly) {
    Invoke-PackagePython -PythonCommand $PythonCommand -Arguments @("-m", "pip", "install", "-e", $Root)
}

if (-not $CheckOnly) {
    $HostCheck = "from tools import official_gui_host_select as h; h.ensure_binary(); print(h.EXE_PATH)"
    Invoke-PackagePython -PythonCommand $PythonCommand -Arguments @("-c", $HostCheck)
}

$ConfigDir = Join-Path $Root "config"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
$ConfigPath = Join-Path $ConfigDir "local.headless.json"
$Config = [ordered]@{
    schema_version = 1
    official_install_dir = $ResolvedOfficialDir
    headless_runtime_root = $env:USARTHMI_HEADLESS_RUNTIME_ROOT
    python = ($PythonCommand -join " ")
    source_package_requires_python = $true
}
$Config | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

if ($InstallSkill -and -not $CheckOnly) {
    $SkillSource = Join-Path $Root "skills\usarthmi-headless-toolchain"
    if (Test-Path -LiteralPath $SkillSource -PathType Container) {
        $CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
        $SkillTargetRoot = Join-Path $CodexHome "skills"
        $SkillTarget = Join-Path $SkillTargetRoot "usarthmi-headless-toolchain"
        New-Item -ItemType Directory -Force -Path $SkillTargetRoot | Out-Null
        Copy-Item -LiteralPath $SkillSource -Destination $SkillTargetRoot -Recurse -Force
        Write-Host "Installed Codex skill: $SkillTarget"
    }
}

Write-Host "USART HMI headless package is ready."
Write-Host "OfficialDir: $ResolvedOfficialDir"
Write-Host "Config: $ConfigPath"
Write-Host "Run: powershell -ExecutionPolicy Bypass -File .\tools\run_touchsafe_pipeline.ps1 -Spec <spec.json>"
