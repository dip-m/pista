# Build Debug APK for Android
# Usage: .\build-apk-debug.ps1

Write-Host "Building Android Debug APK..." -ForegroundColor Green

# Navigate to android directory
Set-Location android

# Build debug APK
Write-Host "Running Gradle build..." -ForegroundColor Yellow
.\gradlew.bat assembleDebug

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ APK built successfully!" -ForegroundColor Green
    $apkPath = "app\build\outputs\apk\debug\app-debug.apk"
    if (Test-Path $apkPath) {
        $fullPath = (Resolve-Path $apkPath).Path
        Write-Host "`nAPK Location: $fullPath" -ForegroundColor Cyan
        Write-Host "`nTo install on device:" -ForegroundColor Yellow
        Write-Host "  adb install $fullPath" -ForegroundColor White
    }
} else {
    Write-Host "`n❌ Build failed!" -ForegroundColor Red
    exit 1
}

# Return to original directory
Set-Location ..
