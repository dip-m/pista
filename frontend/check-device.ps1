# Check if Android device is connected and authorized
# Usage: .\check-device.ps1

$adbPath = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"

if (-not (Test-Path $adbPath)) {
    $adbPath = "$env:USERPROFILE\AppData\Local\Android\Sdk\platform-tools\adb.exe"
}

if (-not (Test-Path $adbPath)) {
    Write-Host "ERROR: ADB not found." -ForegroundColor Red
    exit 1
}

Write-Host "Checking for connected devices..." -ForegroundColor Cyan
Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Yellow

$devices = & $adbPath devices

Write-Host $devices

Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Yellow

if ($devices -match "device$") {
    Write-Host "`n✅ Device found and authorized!" -ForegroundColor Green
    Write-Host "You can proceed with installing the APK." -ForegroundColor White
} elseif ($devices -match "unauthorized") {
    Write-Host "`n⚠️  Device found but NOT authorized" -ForegroundColor Yellow
    Write-Host "`nOn your phone:" -ForegroundColor Cyan
    Write-Host "  1. Look for a popup: 'Allow USB debugging?'" -ForegroundColor White
    Write-Host "  2. Check 'Always allow from this computer'" -ForegroundColor White
    Write-Host "  3. Tap 'Allow'" -ForegroundColor White
    Write-Host "  4. Run this script again to verify" -ForegroundColor White
} elseif ($devices -match "offline") {
    Write-Host "`n⚠️  Device found but OFFLINE" -ForegroundColor Yellow
    Write-Host "`nTry these steps:" -ForegroundColor Cyan
    Write-Host "  1. Unplug USB cable" -ForegroundColor White
    Write-Host "  2. Wait 5 seconds" -ForegroundColor White
    Write-Host "  3. Plug USB cable back in" -ForegroundColor White
    Write-Host "  4. On phone: Pull down notification → Tap USB → Select 'File Transfer'" -ForegroundColor White
    Write-Host "  5. Run this script again" -ForegroundColor White
} else {
    Write-Host "`n❌ No devices found" -ForegroundColor Red
    Write-Host "`nTroubleshooting steps:" -ForegroundColor Cyan
    Write-Host "  1. Is your phone connected via USB?" -ForegroundColor White
    Write-Host "  2. Is USB debugging enabled?" -ForegroundColor White
    Write-Host "     Settings → Developer options → USB debugging" -ForegroundColor White
    Write-Host "  3. Try a different USB cable" -ForegroundColor White
    Write-Host "  4. Try a different USB port" -ForegroundColor White
    Write-Host "  5. On phone: Pull down notification → Tap USB → Select 'File Transfer'" -ForegroundColor White
    Write-Host "  6. Restart ADB server:" -ForegroundColor White
    Write-Host "     $adbPath kill-server" -ForegroundColor Gray
    Write-Host "     $adbPath start-server" -ForegroundColor Gray
}
