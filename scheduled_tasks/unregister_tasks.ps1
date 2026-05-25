# scheduled_tasks/unregister_tasks.ps1
# Faz 6.4 — Mobidik ARGE scheduled tasks silme
#
# Kullanim:
#   .\unregister_tasks.ps1

$ErrorActionPreference = "Continue"

$TaskFolder = "\Mobidik\ARGE_Pazar_Zekasi"
$Tasks = @("Batch_nordik", "Batch_italyan", "Batch_alman", "Weekly_Review")

Write-Output "=== Mobidik ARGE Scheduled Tasks siliniyor ==="
Write-Output "Klasor: $TaskFolder"
Write-Output ""

foreach ($TaskName in $Tasks) {
    $FullPath = "$TaskFolder\$TaskName"
    try {
        Unregister-ScheduledTask -TaskPath "$TaskFolder\" -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Output "Silindi: $FullPath"
    } catch {
        Write-Output "Bulunamadi (zaten yok): $FullPath"
    }
}

# Bos folder'i kaldirmaya calis
try {
    $ScheduleObject = New-Object -ComObject Schedule.Service
    $ScheduleObject.Connect()
    $RootFolder = $ScheduleObject.GetFolder("\Mobidik")
    $RootFolder.DeleteFolder("ARGE_Pazar_Zekasi", 0)
    Write-Output ""
    Write-Output "Klasor silindi: $TaskFolder"

    # Mobidik altinda baska sey yoksa onu da sil
    $MobidikFolder = $ScheduleObject.GetFolder("\Mobidik")
    if ($MobidikFolder.GetTasks(0).Count -eq 0 -and $MobidikFolder.GetFolders(0).Count -eq 0) {
        $ScheduleObject.GetFolder("\").DeleteFolder("Mobidik", 0)
        Write-Output "Klasor silindi: \Mobidik"
    }
} catch {
    # Klasor zaten yok veya bos degil
}

Write-Output ""
Write-Output "=== Tamamlandi ==="
