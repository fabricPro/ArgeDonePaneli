# scheduled_tasks/run_all_now.ps1
# Faz 7.4 — Manuel tetik: 3 bölgeyi (nordik + italyan + alman) sıralı tara.
#
# Kullanim:
#   .\run_all_now.ps1
#
# Web UI'dan da /trigger?region=all ile çağrılabilir.

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ScheduledDir = Join-Path $ProjectRoot "scheduled_tasks"

Write-Output "=== Tüm bölgeleri sıralı tara ==="
Write-Output "Proje: $ProjectRoot"
Write-Output ""

foreach ($region in @("nordik", "italyan", "alman")) {
    Write-Output "`n>>> [$region] tarama başlıyor..."
    & (Join-Path $ScheduledDir "run_batch.ps1") -Region $region
    if ($LASTEXITCODE -eq 0) {
        Write-Output ">>> [$region] tamamlandı ✓"
    } else {
        Write-Output ">>> [$region] HATA (exit: $LASTEXITCODE)"
    }
    Start-Sleep -Seconds 5
}

Write-Output "`n=== Tüm bölgeler tamamlandı ==="
Write-Output "Yeni adayları görmek için: http://localhost:5000/pending"
