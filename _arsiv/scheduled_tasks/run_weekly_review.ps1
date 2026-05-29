# scheduled_tasks/run_weekly_review.ps1
# Wrapper: Task Scheduler -> python topla\scripts\weekly_review.py
# Faz 6.4 — CLAUDE.md kadansi (Cumartesi 09:00)
#
# Kullanim:
#   .\run_weekly_review.ps1

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogsDir = Join-Path $ProjectRoot "topla\logs"

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

$Today = Get-Date -Format "yyyyMMdd"
$LogFile = Join-Path $LogsDir "task_scheduler_weekly_review_${Today}.log"

function Write-Log {
    param([string]$Message)
    $TimeStr = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    $Line = "[$TimeStr] $Message"
    Add-Content -Path $LogFile -Value $Line -Encoding utf8
    Write-Output $Line
}

Write-Log "=== Weekly review BASLADI ==="
Write-Log "Proje koku: $ProjectRoot"

if (-not (Test-Path $PythonExe)) {
    Write-Log "HATA: Python .venv bulunamadi -> $PythonExe"
    exit 1
}

Set-Location $ProjectRoot
Write-Log "Calistiriliyor: python topla\scripts\weekly_review.py"

try {
    $Output = & $PythonExe "topla\scripts\weekly_review.py" 2>&1 | Out-String
    Write-Log "STDOUT:"
    Add-Content -Path $LogFile -Value $Output -Encoding utf8
    Write-Output $Output

    if ($LASTEXITCODE -eq 0) {
        Write-Log "=== Weekly review BASARILI ==="
        exit 0
    } else {
        Write-Log "HATA: Python exit kodu = $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} catch {
    Write-Log "EXCEPTION: $($_.Exception.Message)"
    exit 1
}
