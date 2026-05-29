# scheduled_tasks/run_batch.ps1
# Wrapper: Task Scheduler -> python -m topla.cli --batch <region>
# Faz 6.4 — CLAUDE.md kadansi (Pazartesi/Carsamba/Cuma)
#
# Kullanim:
#   .\run_batch.ps1 -Region nordik
#   .\run_batch.ps1 -Region italyan
#   .\run_batch.ps1 -Region alman

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("nordik", "italyan", "alman")]
    [string]$Region
)

$ErrorActionPreference = "Continue"

# Proje koku (bu PS1 -> scheduled_tasks/ -> proje koku)
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogsDir = Join-Path $ProjectRoot "topla\logs"

# Klasor olustur
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Log dosyasi: bugun + bolge
$Today = Get-Date -Format "yyyyMMdd"
$LogFile = Join-Path $LogsDir "task_scheduler_${Region}_${Today}.log"

function Write-Log {
    param([string]$Message)
    $TimeStr = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    $Line = "[$TimeStr] $Message"
    Add-Content -Path $LogFile -Value $Line -Encoding utf8
    Write-Output $Line
}

Write-Log "=== Batch run BASLADI ==="
Write-Log "Bolge: $Region"
Write-Log "Proje koku: $ProjectRoot"
Write-Log "Python: $PythonExe"

# Python exe kontrol
if (-not (Test-Path $PythonExe)) {
    Write-Log "HATA: Python .venv bulunamadi -> $PythonExe"
    Write-Log "Kurulum: python -m venv .venv ; .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# Python -m topla.cli --batch <region>
Set-Location $ProjectRoot
Write-Log "Calistiriliyor: python -m topla.cli --batch $Region"

try {
    $Output = & $PythonExe -m topla.cli --batch $Region 2>&1 | Out-String
    Write-Log "STDOUT:"
    Add-Content -Path $LogFile -Value $Output -Encoding utf8
    Write-Output $Output

    if ($LASTEXITCODE -eq 0) {
        Write-Log "=== Batch run BASARILI ==="
        exit 0
    } else {
        Write-Log "HATA: Python exit kodu = $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} catch {
    Write-Log "EXCEPTION: $($_.Exception.Message)"
    Write-Log $_.ScriptStackTrace
    exit 1
}
