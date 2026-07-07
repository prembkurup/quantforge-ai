param(
    [string]$TaskName = "QuantForge 24-7 Supervisor"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$launcher = Join-Path $repoRoot "scripts\start_quantforge_247.bat"
$autostartLauncher = Join-Path $env:USERPROFILE "qf247start.bat"

if (-not (Test-Path $launcher)) {
    throw "QuantForge 24/7 launcher not found: $launcher"
}

Set-Content -Path $autostartLauncher -Value @(
    "@echo off",
    "call `"$launcher`""
) -Encoding ASCII

$legacyTasks = @(
    "QuantForge Dashboard API",
    "QuantForge Dashboard Frontend",
    "QuantForge Full History Research Scheduler"
)

foreach ($legacyTask in $legacyTasks) {
    $task = Get-ScheduledTask -TaskName $legacyTask -ErrorAction SilentlyContinue
    if ($task) {
        Disable-ScheduledTask -TaskName $legacyTask | Out-Null
        Write-Output "Disabled legacy task: $legacyTask"
    }
}

$fallbackTaskName = "QuantForge Dashboard API"
$fallbackTask = Get-ScheduledTask -TaskName $fallbackTaskName -ErrorAction SilentlyContinue
if ($fallbackTask) {
    $taskCommand = $autostartLauncher
    $fallbackOutput = & schtasks.exe /Change /TN $fallbackTaskName /TR $taskCommand /ENABLE 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Output $fallbackOutput
        throw "Failed to update existing QuantForge scheduled task."
    }
    & schtasks.exe /Run /TN $fallbackTaskName | Out-Null
    Write-Output "Installed and started task: $fallbackTaskName"
    Write-Output "Launcher: $autostartLauncher"
    exit 0
}

$taskCommand = $autostartLauncher
$createArgs = @(
    "/Create",
    "/TN", $TaskName,
    "/TR", $taskCommand,
    "/SC", "ONLOGON",
    "/DELAY", "0000:30",
    "/RL", "LIMITED",
    "/F"
)

$output = & schtasks.exe @createArgs 2>&1
$installedTaskName = $TaskName
if ($LASTEXITCODE -ne 0) {
    Write-Output $output
    Write-Output "Could not create a new task; reusing existing QuantForge Dashboard API task."
    $installedTaskName = "QuantForge Dashboard API"
    $fallbackOutput = & schtasks.exe /Change /TN $installedTaskName /TR $autostartLauncher /ENABLE 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Output $fallbackOutput
        throw "Failed to create or update a QuantForge scheduled task."
    }
}

& schtasks.exe /Run /TN $installedTaskName | Out-Null

Write-Output "Installed and started task: $installedTaskName"
Write-Output "Launcher: $autostartLauncher"
