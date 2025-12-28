# Monitor Android device logs for debug output
# Usage: .\monitor-logs.ps1

$adbPath = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"

if (-not (Test-Path $adbPath)) {
    $adbPath = "$env:USERPROFILE\AppData\Local\Android\Sdk\platform-tools\adb.exe"
}

if (-not (Test-Path $adbPath)) {
    Write-Host "ERROR: ADB not found. Please check Android SDK installation." -ForegroundColor Red
    Write-Host "To find your SDK location:" -ForegroundColor Yellow
    Write-Host "  Android Studio → File → Settings → Android SDK" -ForegroundColor White
    Write-Host "  ADB will be at: <SDK Location>\platform-tools\adb.exe" -ForegroundColor White
    exit 1
}

Write-Host "Clearing old logs..." -ForegroundColor Cyan
& $adbPath logcat -c

Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Monitoring Debug Logs" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop monitoring`n" -ForegroundColor Yellow

# Monitor logs and filter for DEBUG messages
& $adbPath logcat | Select-String -Pattern "DEBUG" -CaseSensitive:$false
