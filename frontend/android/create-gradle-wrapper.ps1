# Create Gradle Wrapper for Android Project
# This script creates the Gradle wrapper files needed for building

Write-Host "Creating Gradle wrapper..." -ForegroundColor Yellow

# Check if Gradle is installed
$gradleInstalled = Get-Command gradle -ErrorAction SilentlyContinue

if (-not $gradleInstalled) {
    Write-Host "Gradle not found in PATH. Using Android Studio's Gradle..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please do this in Android Studio:" -ForegroundColor Cyan
    Write-Host "1. File → Settings → Build, Execution, Deployment → Build Tools → Gradle" -ForegroundColor White
    Write-Host "2. Select 'Use Gradle from: wrapper task in build script'" -ForegroundColor White
    Write-Host "3. Click 'OK' and let Android Studio create the wrapper" -ForegroundColor White
    Write-Host ""
    Write-Host "OR install Gradle and run this script again" -ForegroundColor Yellow
    exit 0
}

# Create wrapper
Write-Host "Running: gradle wrapper --gradle-version 7.5" -ForegroundColor Gray
gradle wrapper --gradle-version 7.5

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Gradle wrapper created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Now try syncing in Android Studio again" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to create wrapper" -ForegroundColor Red
    Write-Host ""
    Write-Host "Alternative: Let Android Studio create it:" -ForegroundColor Yellow
    Write-Host "1. File → Settings → Build Tools → Gradle" -ForegroundColor White
    Write-Host "2. Select 'Use Gradle from: wrapper task in build script'" -ForegroundColor White
}
