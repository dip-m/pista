# Capture Crash Logs in Real-Time
# Usage: Run this script, then launch the app

$adbPath = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"

if (-not (Test-Path $adbPath)) {
    Write-Host "ADB not found at: $adbPath" -ForegroundColor Red
    exit 1
}

Write-Host "=== Real-Time Crash Log Capture ===" -ForegroundColor Cyan
Write-Host "`n1. Clearing old logs..." -ForegroundColor Yellow
& $adbPath logcat -c
Start-Sleep -Seconds 1

Write-Host "✅ Ready! Now launch your app..." -ForegroundColor Green
Write-Host "`nCapturing logs (will stop after 30 seconds or when you press Ctrl+C)..." -ForegroundColor Yellow
Write-Host ""

# Capture logs with focus on errors and exceptions
& $adbPath logcat -v time *:E AndroidRuntime:E | Select-String -Pattern "com.pista.app|FATAL|Exception|Error" -Context 3,10
