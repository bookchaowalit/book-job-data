# Hourly Windows Task Scheduler ingest of book-job-scraping captures into the lake.
#
# Usage (PowerShell, current user, no admin):
#   .\ops\windows\scheduled-ingest.ps1 install
#   .\ops\windows\scheduled-ingest.ps1 status
#   .\ops\windows\scheduled-ingest.ps1 remove
#
# Ingest is idempotent: an unchanged capture maps to the same batch id and is
# skipped, so the hourly cadence only lands new scraper output. The job_postings
# readiness gate allows 8 hours of staleness; the scraper refreshes every 6.
param([Parameter(Mandatory)][ValidateSet('install', 'remove', 'status')][string]$Action)

$ErrorActionPreference = 'Stop'
$TaskName = 'book-job-data-ingest'
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Python = Join-Path $ProjectDir '.venv\Scripts\pythonw.exe'
$Runner = Join-Path $ProjectDir 'scripts\scheduled_ingest.py'
$Log = Join-Path $ProjectDir 'data\ingest.log'

switch ($Action) {
    'install' {
        if (-not (Test-Path $Python)) { throw "Missing $Python — create .venv and install '.[lake]' first." }
        # pythonw + a Python runner: a hidden powershell.exe console was killed
        # by Task Scheduler (0xC000013A) before ingest could write its log.
        $taskAction = New-ScheduledTaskAction -Execute $Python -Argument "`"$Runner`"" -WorkingDirectory $ProjectDir
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
            -RepetitionInterval (New-TimeSpan -Hours 1)
        # Priority 4 = normal. The default (7) also drops I/O priority, which
        # stalled Python imports for minutes on a busy host.
        $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Priority 4 `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
        Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $trigger -Settings $settings `
            -Description 'book-job-data: ingest scraper captures into the Bronze lake' -Force | Out-Null
        Write-Host "Installed $TaskName (hourly). Log: $Log"
    }
    'remove' {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Removed $TaskName"
    }
    'status' {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if (-not $task) { Write-Host 'Status: NOT INSTALLED'; break }
        $info = $task | Get-ScheduledTaskInfo
        Write-Host "Status: $($task.State)  LastRun: $($info.LastRunTime)  LastResult: $($info.LastTaskResult)  NextRun: $($info.NextRunTime)"
    }
}
