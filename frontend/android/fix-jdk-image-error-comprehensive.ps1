# Comprehensive Fix for JDK Image Transformation Error
# This addresses OneDrive sync issues, corrupted caches, and SDK problems

Write-Host "=== Comprehensive JDK Image Transformation Fix ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop all Gradle/Java processes
Write-Host "Step 1: Stopping all Gradle and Java processes..." -ForegroundColor Yellow
Get-Process | Where-Object {
    $_.ProcessName -like "*java*" -or
    $_.ProcessName -like "*gradle*" -or
    $_.ProcessName -like "*jlink*"
} | ForEach-Object {
    try {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Write-Host "  Stopped: $($_.ProcessName)" -ForegroundColor Green
    } catch {
        # Ignore errors
    }
}
Start-Sleep -Seconds 3
Write-Host ""

# Step 2: Clean entire Gradle cache
Write-Host "Step 2: Cleaning entire Gradle cache..." -ForegroundColor Yellow
$gradleCache = "$env:USERPROFILE\.gradle"
if (Test-Path "$gradleCache\caches\transforms-3") {
    Remove-Item -Recurse -Force "$gradleCache\caches\transforms-3" -ErrorAction SilentlyContinue
    Write-Host "  ✓ Removed transforms-3 cache" -ForegroundColor Green
}
if (Test-Path "$gradleCache\daemon") {
    Remove-Item -Recurse -Force "$gradleCache\daemon" -ErrorAction SilentlyContinue
    Write-Host "  ✓ Cleared Gradle daemon cache" -ForegroundColor Green
}
Write-Host ""

# Step 3: Clean local build directories
Write-Host "Step 3: Cleaning local build directories..." -ForegroundColor Yellow
$currentDir = Get-Location
if (Test-Path ".gradle") {
    Remove-Item -Recurse -Force ".gradle" -ErrorAction SilentlyContinue
    Write-Host "  ✓ Removed .gradle" -ForegroundColor Green
}
if (Test-Path "app\build") {
    Remove-Item -Recurse -Force "app\build" -ErrorAction SilentlyContinue
    Write-Host "  ✓ Removed app\build" -ForegroundColor Green
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
    Write-Host "  ✓ Removed build" -ForegroundColor Green
}
Write-Host ""

# Step 4: Verify Android SDK platform file
Write-Host "Step 4: Verifying Android SDK platform..." -ForegroundColor Yellow
$sdkPlatform = "C:\Users\dipmu\AppData\Local\Android\Sdk\platforms\android-33\core-for-system-modules.jar"
if (Test-Path $sdkPlatform) {
    $fileSize = (Get-Item $sdkPlatform).Length
    Write-Host "  ✓ Platform file exists ($([math]::Round($fileSize/1KB, 2)) KB)" -ForegroundColor Green
    if ($fileSize -lt 1KB) {
        Write-Host "  ⚠ WARNING: File seems too small, may be corrupted!" -ForegroundColor Yellow
        Write-Host "  → Reinstall Android SDK Platform 33 in Android Studio" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ Platform file NOT found!" -ForegroundColor Red
    Write-Host "  → Install Android SDK Platform 33 in Android Studio" -ForegroundColor Yellow
}
Write-Host ""

# Step 5: Check OneDrive sync status
Write-Host "Step 5: OneDrive Sync Check..." -ForegroundColor Yellow
$projectPath = (Get-Location).Path
if ($projectPath -like "*OneDrive*") {
    Write-Host "  ⚠ WARNING: Project is in OneDrive folder!" -ForegroundColor Yellow
    Write-Host "  → OneDrive sync may be locking files during build" -ForegroundColor Yellow
    Write-Host "  → Consider pausing OneDrive sync or moving project outside OneDrive" -ForegroundColor Yellow
    Write-Host "  → See docs/FIX_ONEDRIVE_BUILD_LOCK.md for details" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Project is not in OneDrive" -ForegroundColor Green
}
Write-Host ""

Write-Host "=== Fix Complete! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "CRITICAL NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. PAUSE OneDrive Sync (if project is in OneDrive):" -ForegroundColor White
Write-Host "   - Right-click OneDrive icon → Pause syncing → 2 hours" -ForegroundColor Gray
Write-Host ""
Write-Host "2. In Android Studio:" -ForegroundColor White
Write-Host "   - File → Invalidate Caches / Restart → Invalidate and Restart" -ForegroundColor Gray
Write-Host "   - Wait for restart" -ForegroundColor Gray
Write-Host "   - Build → Clean Project" -ForegroundColor Gray
Write-Host "   - Build → Rebuild Project" -ForegroundColor Gray
Write-Host ""
Write-Host "3. If error persists, reinstall Android SDK Platform 33:" -ForegroundColor White
Write-Host "   - Tools -> SDK Manager -> SDK Platforms" -ForegroundColor Gray
Write-Host "   - Uncheck Android 13.0 (API 33), click Apply" -ForegroundColor Gray
Write-Host "   - Re-check Android 13.0 (API 33), click Apply" -ForegroundColor Gray
Write-Host ""
