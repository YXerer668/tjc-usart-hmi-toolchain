param(
    [Parameter(Mandatory = $true)]
    [string]$PatchDir,

    [string]$TaskName = "DaBaiDIYGlancePatch"
)

$ErrorActionPreference = "Stop"

$patch = Get-ChildItem -LiteralPath $PatchDir -Filter "*.exe" |
    Where-Object { $_.Name -like "*Glance*" -and $_.Name -notlike "*工具*" } |
    Select-Object -First 1

if (-not $patch) {
    throw "Patch executable not found in: $PatchDir"
}

$patchPath = $patch.FullName
$taskAction = New-ScheduledTaskAction -Execute $patchPath -WorkingDirectory $PatchDir
$taskTrigger = New-ScheduledTaskTrigger -AtLogOn
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$taskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $taskTrigger -Principal $taskPrincipal -Settings $taskSettings -Force | Out-Null

Start-Process -FilePath $patchPath -WorkingDirectory $PatchDir -WindowStyle Hidden

[pscustomobject]@{
    TaskName = $TaskName
    Patch = $patchPath
    Status = "registered_and_started"
} | ConvertTo-Json
