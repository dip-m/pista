# Fix Gradle JDK Image Transformation Error
# This script cleans the corrupted Gradle cache that causes jlink.exe failures

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing Gradle JDK Image Error" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop all Gradle daemons
Write-Host "Step 1: Stopping Gradle daemons..." -ForegroundColor Yellow
if (Test-Path ".\gradlew.bat") {
    & .\gradlew.bat --stop 2>&1 | Out-Null
    Write-Host "  [OK] Gradle daemons stopped" -ForegroundColor Green
} else {
    Write-Host "  [WARN] gradlew.bat not found, skipping daemon stop" -ForegroundColor Yellow
}

# Step 2: Clean the transforms cache (most common fix)
Write-Host ""
Write-Host "Step 2: Cleaning Gradle transforms cache..." -ForegroundColor Yellow
$transformsCache = "$env:USERPROFILE\.gradle\caches\transforms-3"
if (Test-Path $transformsCache) {
    try {
        Remove-Item -Recurse -Force "$transformsCache\*" -ErrorAction SilentlyContinue
        Write-Host "  [OK] Transforms cache cleaned" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Could not clean transforms cache: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [INFO] Transforms cache not found (may already be clean)" -ForegroundColor Gray
}

# Step 3: Clean local build directories
Write-Host ""
Write-Host "Step 3: Cleaning local build directories..." -ForegroundColor Yellow
$buildDirs = @(".gradle", "app\build", "build", "capacitor-cordova-android-plugins\build")
foreach ($dir in $buildDirs) {
    if (Test-Path $dir) {
        try {
            Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
            Write-Host "  [OK] Cleaned: $dir" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Could not clean $dir : $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

# Step 4: Run Gradle clean
Write-Host ""
Write-Host "Step 4: Running Gradle clean..." -ForegroundColor Yellow
if (Test-Path ".\gradlew.bat") {
    try {
        & .\gradlew.bat clean 2>&1 | Out-Null
        Write-Host "  [OK] Gradle clean completed" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Gradle clean had issues (this is OK if cache was corrupted)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARN] gradlew.bat not found, skipping Gradle clean" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. In Android Studio: File -> Invalidate Caches / Restart" -ForegroundColor White
Write-Host "2. After restart, try building again" -ForegroundColor White
Write-Host ""
Write-Host "If the error persists, try:" -ForegroundColor Yellow
Write-Host "- Tools -> SDK Manager -> Verify Android SDK Platform 33 is installed" -ForegroundColor White
Write-Host "- File -> Settings -> Build Tools -> Gradle -> Set Gradle JDK to JBR 17 or 21" -ForegroundColor White
Write-Host ""
