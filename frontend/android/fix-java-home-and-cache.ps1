# Fix JAVA_HOME and Gradle Cache Issues
# This script sets JAVA_HOME and cleans corrupted Gradle cache

Write-Host "=== Fixing JAVA_HOME and Gradle Cache ===" -ForegroundColor Cyan
Write-Host ""

# Find Android Studio's JDK
$androidStudioJdk = "C:\Program Files\Android\Android Studio\jbr"
$alternativeJdk = "$env:USERPROFILE\.jdks\jbr-21.0.9"

# Determine which JDK to use
$javaHome = $null
if (Test-Path $androidStudioJdk) {
    $javaHome = $androidStudioJdk
    Write-Host "Found Android Studio JDK at: $javaHome" -ForegroundColor Green
} elseif (Test-Path $alternativeJdk) {
    $javaHome = $alternativeJdk
    Write-Host "Found alternative JDK at: $javaHome" -ForegroundColor Green
} else {
    Write-Host "ERROR: Could not find JDK!" -ForegroundColor Red
    Write-Host "Please install Android Studio or set JAVA_HOME manually" -ForegroundColor Yellow
    exit 1
}

# Set JAVA_HOME for current session
Write-Host ""
Write-Host "1. Setting JAVA_HOME for current session..." -ForegroundColor Yellow
$env:JAVA_HOME = $javaHome
$env:PATH = "$javaHome\bin;$env:PATH"

Write-Host "   JAVA_HOME = $env:JAVA_HOME" -ForegroundColor Green
Write-Host ""

# Verify Java is accessible
Write-Host "2. Verifying Java installation..." -ForegroundColor Yellow
try {
    $javaVersion = & "$javaHome\bin\java.exe" -version 2>&1 | Select-Object -First 1
    Write-Host "   $javaVersion" -ForegroundColor Green
} catch {
    Write-Host "   WARNING: Could not verify Java version" -ForegroundColor Yellow
}
Write-Host ""

# Clean Gradle transforms cache (where the error occurs)
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

# Clean local build directories
Write-Host "4. Cleaning local build directories..." -ForegroundColor Yellow
$currentDir = Get-Location
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

Write-Host "=== Fix Complete! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "JAVA_HOME has been set for this PowerShell session." -ForegroundColor Yellow
Write-Host ""
Write-Host "To make JAVA_HOME permanent:" -ForegroundColor Yellow
Write-Host "1. Right-click 'This PC' → Properties" -ForegroundColor White
Write-Host "2. Advanced system settings → Environment Variables" -ForegroundColor White
Write-Host "3. Under 'User variables', click 'New'" -ForegroundColor White
Write-Host "4. Variable name: JAVA_HOME" -ForegroundColor White
Write-Host "5. Variable value: $javaHome" -ForegroundColor White
Write-Host "6. Click OK, then restart Android Studio" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. In Android Studio: File → Invalidate Caches / Restart" -ForegroundColor White
Write-Host "2. Build → Clean Project" -ForegroundColor White
Write-Host "3. Build → Rebuild Project" -ForegroundColor White
Write-Host ""
Write-Host "Or run from command line (in this PowerShell session):" -ForegroundColor Yellow
Write-Host "   cd frontend\android" -ForegroundColor White
Write-Host "   .\gradlew.bat clean" -ForegroundColor White
Write-Host "   .\gradlew.bat assembleDebug" -ForegroundColor White
Write-Host ""
