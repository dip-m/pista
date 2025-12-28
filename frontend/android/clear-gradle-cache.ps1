# Clear Gradle cache to fix JDK image transformation errors
# Usage: .\clear-gradle-cache.ps1

Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Clearing Gradle Cache" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════`n" -ForegroundColor Cyan

# Stop Gradle daemons
Write-Host "Step 1: Stopping Java/Gradle processes..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.ProcessName -like "*java*" -or $_.ProcessName -like "*gradle*"} | ForEach-Object {
    Write-Host "  Stopping: $($_.ProcessName)" -ForegroundColor White
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3

# Clear transforms cache
Write-Host "`nStep 2: Clearing transforms-3 cache..." -ForegroundColor Yellow
$cachePath = "$env:USERPROFILE\.gradle\caches\transforms-3"
if (Test-Path $cachePath) {
    try {
        Remove-Item -Path $cachePath -Recurse -Force -ErrorAction Stop
        Write-Host "✅ Cache cleared successfully" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not delete cache (may be locked)" -ForegroundColor Yellow
        Write-Host "   Please close Android Studio and try again" -ForegroundColor White
        Write-Host "   Or manually delete: $cachePath" -ForegroundColor Gray
        exit 1
    }
} else {
    Write-Host "Cache folder not found (already cleared?)" -ForegroundColor Yellow
}

# Clear project build
Write-Host "`nStep 3: Clearing project build folders..." -ForegroundColor Yellow
$projectPath = "$PSScriptRoot"
if (Test-Path "$projectPath\app\build") {
    Remove-Item -Path "$projectPath\app\build" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✅ app/build cleared" -ForegroundColor Green
}
if (Test-Path "$projectPath\build") {
    Remove-Item -Path "$projectPath\build" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✅ build cleared" -ForegroundColor Green
}
if (Test-Path "$projectPath\.gradle") {
    Remove-Item -Path "$projectPath\.gradle" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✅ .gradle cleared" -ForegroundColor Green
}

Write-Host "`n✅ Cleanup complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Close Android Studio completely" -ForegroundColor White
Write-Host "  2. Reopen Android Studio" -ForegroundColor White
Write-Host "  3. File → Invalidate Caches / Restart → Invalidate and Restart" -ForegroundColor White
Write-Host "  4. After restart: Build → Clean Project" -ForegroundColor White
Write-Host "  5. Build → Rebuild Project" -ForegroundColor White
Write-Host "  6. Build → Build APK`n" -ForegroundColor White
