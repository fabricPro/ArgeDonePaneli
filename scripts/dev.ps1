# Yerel gelistirme — GitHub'tan otomatik pull + Flask debug mod
# Kullanim:
#   PowerShell ac, projeye gel, sunu calistir:
#     .\scripts\dev.ps1
#
# Calisinca:
#   1) main daline gecer + son commit'i ceker
#   2) Arka planda her 30 sn'de bir 'git fetch + pull' — Claude push yapinca otomatik gunceller
#   3) Flask debug modda baslar — kod degisikliklerinde otomatik reload
#   4) Tarayicida http://localhost:5000 — sert yenile (Ctrl+F5) ile yeni stilleri gor
#
# Durdurmak: Ctrl+C

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Proje koku: $root" -ForegroundColor Cyan
Write-Host "==> main daline gecisiliyor + son commit cekiliyor..." -ForegroundColor Cyan

git fetch origin main 2>&1 | Out-Null
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne "main") {
    Write-Host "    (su an '$branch' dalindasin -> 'main')" -ForegroundColor Yellow
    git checkout main 2>&1 | Out-Null
}
git pull origin main

# Arka planda otomatik pull — her 30 sn'de bir origin/main'i kontrol et
Write-Host "==> Arka planda auto-pull job baslatiliyor (30 sn aralik)..." -ForegroundColor Cyan
$pullJob = Start-Job -Name "fas-auto-pull" -ScriptBlock {
    param($projectRoot)
    Set-Location $projectRoot
    while ($true) {
        git fetch origin main 2>&1 | Out-Null
        $local = (git rev-parse HEAD).Trim()
        $remote = (git rev-parse origin/main).Trim()
        if ($local -ne $remote) {
            Write-Output "[auto-pull] Yeni commit bulundu: $remote"
            git pull origin main 2>&1
        }
        Start-Sleep -Seconds 30
    }
} -ArgumentList $root

Write-Host ""
Write-Host "==> Flask baslatiliyor (debug=on, auto-reload)" -ForegroundColor Green
Write-Host "==> http://localhost:5000   (sifre: .env icindeki APP_PASSWORD)" -ForegroundColor Green
Write-Host "==> CTRL+C ile her ikisini de durdur." -ForegroundColor Yellow
Write-Host ""

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "HATA: $py bulunamadi. .venv kurulu degil mi?" -ForegroundColor Red
    Stop-Job -Job $pullJob -ErrorAction SilentlyContinue
    Remove-Job -Job $pullJob -ErrorAction SilentlyContinue
    exit 1
}

try {
    & $py web\app.py
} finally {
    Write-Host ""
    Write-Host "==> Auto-pull job durduruluyor..." -ForegroundColor Cyan
    Stop-Job -Job $pullJob -ErrorAction SilentlyContinue
    Remove-Job -Job $pullJob -ErrorAction SilentlyContinue
    Write-Host "==> Cikis." -ForegroundColor Green
}
