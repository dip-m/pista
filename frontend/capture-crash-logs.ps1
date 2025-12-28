# Capture comprehensive crash logs including our debug messages
# Usage: .\capture-crash-logs.ps1

$adbPath = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"

if (-not (Test-Path $adbPath)) {
    $adbPath = "$env:USERPROFILE\AppData\Local\Android\Sdk\platform-tools\adb.exe"
}

if (-not (Test-Path $adbPath)) {
    Write-Host "ERROR: ADB not found." -ForegroundColor Red
    exit 1
}

Write-Host "Clearing old logs..." -ForegroundColor Cyan
& $adbPath logcat -c

Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Capturing Crash Logs" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "`nNow launch the app on your phone and let it crash." -ForegroundColor Yellow
Write-Host "Press Ctrl+C after the crash to stop logging.`n" -ForegroundColor Yellow

# Capture all logs and filter for relevant information
& $adbPath logcat -v time *:E AndroidRuntime:E chromium:V DEBUG:* | Tee-Object -FilePath "crash_logs.txt"

Write-Host "`nLogs saved to: crash_logs.txt" -ForegroundColor Green
Write-Host "Please share the contents of this file." -ForegroundColor Cyan
