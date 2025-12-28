# Fix Gradle JDK Image Transformation Error
# This script cleans the Gradle cache to resolve JDK image transformation issues

Write-Host "=== Fixing Gradle JDK Image Transformation Error ===" -ForegroundColor Cyan
Write-Host ""

# Stop all Gradle daemons first
Write-Host "1. Stopping Gradle daemons..." -ForegroundColor Yellow
& .\gradlew --stop 2>$null
Write-Host "   ✓ Gradle daemons stopped" -ForegroundColor Green
Write-Host ""

# Clean local build directories
Write-Host "2. Cleaning local build directories..." -ForegroundColor Yellow
if (Test-Path ".gradle") {
    Remove-Item -Recurse -Force ".gradle" -ErrorAction SilentlyContinue
    Write-Host "   ✓ Removed .gradle directory" -ForegroundColor Green
}
if (Test-Path "app\build") {
    Remove-Item -Recurse -Force "app\build" -ErrorAction SilentlyContinue
    Write-Host "   ✓ Removed app\build directory" -ForegroundColor Green
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
    Write-Host "   ✓ Removed build directory" -ForegroundColor Green
}
Write-Host ""

# Clean the transforms cache (where the error occurs)
Write-Host "3. Cleaning Gradle transforms cache..." -ForegroundColor Yellow
$transformsCache = "$env:USERPROFILE\.gradle\caches\transforms-3"
if (Test-Path $transformsCache) {
    $itemCount = (Get-ChildItem $transformsCache -ErrorAction SilentlyContinue | Measure-Object).Count
    Remove-Item -Recurse -Force "$transformsCache\*" -ErrorAction SilentlyContinue
    Write-Host "   ✓ Cleaned $itemCount transform cache entries" -ForegroundColor Green
} else {
    Write-Host "   ℹ Transforms cache not found (may already be clean)" -ForegroundColor Gray
}
Write-Host ""

# Optionally clean the entire Gradle cache (commented out by default)
# Uncomment the section below if the above doesn't work
<#
Write-Host "4. Cleaning entire Gradle cache (this will re-download everything)..." -ForegroundColor Yellow
$gradleCache = "$env:USERPROFILE\.gradle\caches"
if (Test-Path $gradleCache) {
    Remove-Item -Recurse -Force $gradleCache -ErrorAction SilentlyContinue
    Write-Host "   ✓ Removed entire Gradle cache" -ForegroundColor Green
}
Write-Host ""
#>

Write-Host "=== Cache cleanup complete! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. In Android Studio: File → Invalidate Caches / Restart → Invalidate and Restart" -ForegroundColor White
Write-Host "2. Build → Clean Project" -ForegroundColor White
Write-Host "3. Build → Rebuild Project" -ForegroundColor White
Write-Host ""
Write-Host "Or run from command line:" -ForegroundColor Yellow
Write-Host "   .\gradlew clean" -ForegroundColor White
Write-Host "   .\gradlew assembleDebug" -ForegroundColor White
Write-Host ""
