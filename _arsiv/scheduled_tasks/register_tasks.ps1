# scheduled_tasks/register_tasks.ps1
# Faz 6.4 — Windows Task Scheduler kayit scripti
# CLAUDE.md kadansi:
#   Pazartesi 06:00 -> nordik (kvadrat, sahco)
#   Carsamba   06:00 -> italyan (dedar, rubelli)
#   Cuma       06:00 -> alman (zimmer_rohde + alt markalar + nya + cb)
#   Cumartesi  09:00 -> haftalik oz-degerlendirme
#
# Kullanim (admin gerektirir):
#   .\register_tasks.ps1
#
# Tum gorevleri silmek icin:
#   .\unregister_tasks.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TaskFolder = "\Mobidik\ARGE_Pazar_Zekasi"
$ScheduledDir = Join-Path $ProjectRoot "scheduled_tasks"

# PowerShell exe (sistem)
$PowerShellExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

# Wrapper scriptler
$RunBatch = Join-Path $ScheduledDir "run_batch.ps1"
$RunWeekly = Join-Path $ScheduledDir "run_weekly_review.ps1"

if (-not (Test-Path $RunBatch)) {
    Write-Error "Wrapper bulunamadi: $RunBatch"
    exit 1
}
if (-not (Test-Path $RunWeekly)) {
    Write-Error "Wrapper bulunamadi: $RunWeekly"
    exit 1
}

# Ortak ayarlar
$CommonSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

function Register-BatchTask {
    param(
        [string]$Region,
        [string]$DayOfWeek,
        [string]$Time,
        [string]$Description
    )
    $TaskName = "Batch_$Region"
    $FullPath = "$TaskFolder\$TaskName"

    $Args = "-NoProfile -ExecutionPolicy Bypass -File `"$RunBatch`" -Region $Region"
    $Action = New-ScheduledTaskAction `
        -Execute $PowerShellExe `
        -Argument $Args `
        -WorkingDirectory $ProjectRoot

    $Trigger = New-ScheduledTaskTrigger `
        -Weekly `
        -DaysOfWeek $DayOfWeek `
        -At $Time

    # Mevcut gorevi sil (varsa)
    try {
        Unregister-ScheduledTask -TaskPath "$TaskFolder\" -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Output "  (mevcut '$FullPath' silindi)"
    } catch {
        # Yoktu, sorun degil
    }

    Register-ScheduledTask `
        -TaskName $TaskName `
        -TaskPath "$TaskFolder\" `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $CommonSettings `
        -Principal $Principal `
        -Description $Description | Out-Null

    Write-Output "Kaydedildi: $FullPath -> $DayOfWeek $Time"
}

function Register-WeeklyReviewTask {
    $TaskName = "Weekly_Review"
    $FullPath = "$TaskFolder\$TaskName"

    $Args = "-NoProfile -ExecutionPolicy Bypass -File `"$RunWeekly`""
    $Action = New-ScheduledTaskAction `
        -Execute $PowerShellExe `
        -Argument $Args `
        -WorkingDirectory $ProjectRoot

    $Trigger = New-ScheduledTaskTrigger `
        -Weekly `
        -DaysOfWeek Saturday `
        -At "09:00"

    try {
        Unregister-ScheduledTask -TaskPath "$TaskFolder\" -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Output "  (mevcut '$FullPath' silindi)"
    } catch {}

    Register-ScheduledTask `
        -TaskName $TaskName `
        -TaskPath "$TaskFolder\" `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $CommonSettings `
        -Principal $Principal `
        -Description "Mobidik ARGE — haftalik oz-degerlendirme (docs/haftalik_oz_degerlendirme_YYYY-MM-DD.md)" | Out-Null

    Write-Output "Kaydedildi: $FullPath -> Saturday 09:00"
}

Write-Output "=== Mobidik ARGE Scheduled Tasks kayit ediliyor ==="
Write-Output "Klasor: $TaskFolder"
Write-Output "Kullanici: $env:USERNAME"
Write-Output ""

Register-BatchTask -Region "nordik"  -DayOfWeek "Monday"    -Time "06:00" `
    -Description "Mobidik ARGE — Nordik bolge (Kvadrat, Sahco) aday taramasi"
Register-BatchTask -Region "italyan" -DayOfWeek "Wednesday" -Time "06:00" `
    -Description "Mobidik ARGE — Italyan bolge (Dedar, Rubelli) aday taramasi"
Register-BatchTask -Region "alman"   -DayOfWeek "Friday"    -Time "06:00" `
    -Description "Mobidik ARGE — Alman bolge (Z+R Group, Nya, Creation Baumann) aday taramasi"
Register-WeeklyReviewTask

Write-Output ""
Write-Output "=== Tamamlandi ==="
Write-Output ""
Write-Output "Kayitli gorevleri gormek icin:"
Write-Output "  Get-ScheduledTask -TaskPath '$TaskFolder\*'"
Write-Output ""
Write-Output "Test (manuel calistir):"
Write-Output "  Start-ScheduledTask -TaskPath '$TaskFolder\' -TaskName 'Batch_nordik'"
Write-Output ""
Write-Output "Silmek icin: .\unregister_tasks.ps1"
