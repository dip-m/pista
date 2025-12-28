# Fix Gradle JDK Image Transformation Error
# Usage: .\fix-build-error.ps1

Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Fixing Gradle Build Error" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════`n" -ForegroundColor Cyan

$gradlePath = "$PSScriptRoot\gradlew.bat"

if (-not (Test-Path $gradlePath)) {
    Write-Host "ERROR: gradlew.bat not found at: $gradlePath" -ForegroundColor Red
    exit 1
}

Write-Host "Step 1: Stopping Gradle daemons..." -ForegroundColor Yellow
& $gradlePath --stop
Start-Sleep -Seconds 2

Write-Host "`nStep 2: Cleaning Gradle cache..." -ForegroundColor Yellow
if (Test-Path "$env:USERPROFILE\.gradle\caches\transforms-3") {
    Write-Host "  Removing transforms-3 cache..." -ForegroundColor White
    Remove-Item -Path "$env:USERPROFILE\.gradle\caches\transforms-3" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "`nStep 3: Cleaning project build..." -ForegroundColor Yellow
& $gradlePath clean
Start-Sleep -Seconds 2

Write-Host "`nStep 4: Invalidating Android Studio caches..." -ForegroundColor Yellow
Write-Host "  Please do this manually in Android Studio:" -ForegroundColor White
Write-Host "  File → Invalidate Caches / Restart → Invalidate and Restart`n" -ForegroundColor White

Write-Host "✅ Cleanup complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Restart Android Studio (if not done via Invalidate Caches)" -ForegroundColor White
Write-Host "  2. Build → Clean Project" -ForegroundColor White
Write-Host "  3. Build → Rebuild Project" -ForegroundColor White
Write-Host "  4. If still failing, try: Build → Make Project`n" -ForegroundColor White
