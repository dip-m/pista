# Install APK to connected Android device
# Usage: .\install-apk.ps1

$adbPath = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"

if (-not (Test-Path $adbPath)) {
    $adbPath = "$env:USERPROFILE\AppData\Local\Android\Sdk\platform-tools\adb.exe"
}

if (-not (Test-Path $adbPath)) {
    Write-Host "ERROR: ADB not found. Please check Android SDK installation." -ForegroundColor Red
    Write-Host "Expected locations:" -ForegroundColor Yellow
    Write-Host "  - $env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" -ForegroundColor White
    Write-Host "  - $env:USERPROFILE\AppData\Local\Android\Sdk\platform-tools\adb.exe" -ForegroundColor White
    Write-Host "`nTo find your SDK location:" -ForegroundColor Yellow
    Write-Host "  1. Open Android Studio" -ForegroundColor White
    Write-Host "  2. File → Settings → Appearance & Behavior → System Settings → Android SDK" -ForegroundColor White
    Write-Host "  3. Note the 'Android SDK Location' path" -ForegroundColor White
    Write-Host "  4. ADB will be at: <SDK Location>\platform-tools\adb.exe" -ForegroundColor White
    exit 1
}

$apkPath = "$PSScriptRoot\android\app\build\outputs\apk\debug\app-debug.apk"

if (-not (Test-Path $apkPath)) {
    Write-Host "ERROR: APK not found at: $apkPath" -ForegroundColor Red
    Write-Host "Please build the APK first in Android Studio." -ForegroundColor Yellow
    exit 1
}

Write-Host "Checking for connected devices..." -ForegroundColor Cyan
& $adbPath devices

Write-Host "`nInstalling APK..." -ForegroundColor Cyan
& $adbPath install -r $apkPath

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ APK installed successfully!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Installation failed. Check the error message above." -ForegroundColor Red
}
