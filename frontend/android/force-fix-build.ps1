# Force fix for JDK image transformation error
# This clears all caches and forces Android Studio JDK

Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Force Fix: JDK Image Transformation Error" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════`n" -ForegroundColor Cyan

# Stop all Java/Gradle processes
Write-Host "Step 1: Stopping all Java/Gradle processes..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.ProcessName -like "*java*" -or $_.ProcessName -like "*gradle*" -or $_.ProcessName -like "*studio*"} | ForEach-Object {
    Write-Host "  Stopping: $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor White
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 5

# Clear Gradle cache
Write-Host "`nStep 2: Clearing Gradle cache..." -ForegroundColor Yellow
$gradleCache = "$env:USERPROFILE\.gradle\caches"
if (Test-Path $gradleCache) {
    try {
        Remove-Item -Path "$gradleCache\transforms-3" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "✅ Cleared .gradle\caches\transforms-3" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not clear .gradle cache: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Clear the weird .jdks cache (this is the problem!)
Write-Host "`nStep 3: Clearing .jdks cache (this is causing the issue)..." -ForegroundColor Yellow
$jdksCache = "$env:USERPROFILE\.jdks\jbr-21.0.9\caches"
if (Test-Path $jdksCache) {
    try {
        Remove-Item -Path $jdksCache -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "✅ Cleared .jdks\jbr-21.0.9\caches" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not clear .jdks cache: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ .jdks cache not found (good)" -ForegroundColor Green
}

# Clear project build
Write-Host "`nStep 4: Clearing project build..." -ForegroundColor Yellow
$projectPath = "$PSScriptRoot"
@("app\build", "build", ".gradle") | ForEach-Object {
    $path = Join-Path $projectPath $_
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "✅ Cleared $_" -ForegroundColor Green
    }
}

Write-Host "`n✅ Cleanup complete!" -ForegroundColor Green
Write-Host "`nCRITICAL: Set Gradle JDK in Android Studio UI:" -ForegroundColor Yellow
Write-Host "  1. File → Settings → Build Tools → Gradle" -ForegroundColor White
Write-Host "  2. Set 'Gradle JDK' to: 'JetBrains Runtime 21.0.8'" -ForegroundColor White
Write-Host "  3. Click OK" -ForegroundColor White
Write-Host "  4. File → Sync Project with Gradle Files" -ForegroundColor White
Write-Host "  5. Build → Clean Project" -ForegroundColor White
Write-Host "  6. Build → Build APK`n" -ForegroundColor White
