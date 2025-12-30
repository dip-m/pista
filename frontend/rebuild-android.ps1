# Rebuild Android APK with Latest Frontend Changes
# Usage: .\rebuild-android.ps1

Write-Host "🔄 Rebuilding Android APK with latest frontend changes..." -ForegroundColor Green
Write-Host ""

# Step 1: Build React app
Write-Host "Step 1: Building React app..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ React build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ React app built successfully" -ForegroundColor Green
Write-Host ""

# Step 2: Sync to Android
Write-Host "Step 2: Syncing to Android project..." -ForegroundColor Yellow
npx cap sync android

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Capacitor sync failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Files synced to Android project" -ForegroundColor Green
Write-Host ""

# Step 3: Build APK
Write-Host "Step 3: Building Android APK..." -ForegroundColor Yellow
Set-Location android
.\gradlew.bat assembleDebug

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ APK built successfully!" -ForegroundColor Green
    $apkPath = "app\build\outputs\apk\debug\app-debug.apk"
    if (Test-Path $apkPath) {
        $fullPath = (Resolve-Path $apkPath).Path
        Write-Host "`n📦 APK Location: $fullPath" -ForegroundColor Cyan
        Write-Host "`nTo install on device:" -ForegroundColor Yellow
        Write-Host "  adb install $fullPath" -ForegroundColor White
        Write-Host "`nOr manually transfer the APK to your device and install it." -ForegroundColor White
    }
} else {
    Write-Host "`n❌ APK build failed!" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Return to original directory
Set-Location ..

Write-Host "`n✨ All done! Your mobile app now has the latest changes." -ForegroundColor Green
