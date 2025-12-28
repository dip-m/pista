# Get Crash Log for Pista App
# Usage: .\get-crash-log.ps1

$adbPath = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"

if (-not (Test-Path $adbPath)) {
    Write-Host "ADB not found at: $adbPath" -ForegroundColor Red
    Write-Host "`nPlease use Android Studio Logcat instead:" -ForegroundColor Yellow
    Write-Host "1. Open Android Studio" -ForegroundColor White
    Write-Host "2. View → Tool Windows → Logcat" -ForegroundColor White
    Write-Host "3. Filter by: package:com.pista.app" -ForegroundColor White
    Write-Host "4. Launch the app and look for red errors" -ForegroundColor White
    exit 1
}

Write-Host "=== Getting Crash Logs for com.pista.app ===" -ForegroundColor Cyan
Write-Host "`nMake sure your device/emulator is connected and the app has crashed." -ForegroundColor Yellow
Write-Host "`nFetching logs..." -ForegroundColor Yellow
Write-Host ""

& $adbPath logcat -d | Select-String -Pattern "com.pista.app|AndroidRuntime|FATAL|Exception" -Context 10,30

Write-Host "`n=== End of Logs ===" -ForegroundColor Cyan
Write-Host "`nIf no errors shown, try:" -ForegroundColor Yellow
Write-Host "1. Clear logcat: & '$adbPath' logcat -c" -ForegroundColor White
Write-Host "2. Launch the app" -ForegroundColor White
Write-Host "3. Run this script again immediately" -ForegroundColor White
