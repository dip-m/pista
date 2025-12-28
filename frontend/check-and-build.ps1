# Check Android Studio Installation and Guide Build Process
# This script checks if Android Studio is installed and guides you through building the APK

Write-Host "`n=== Pista Android APK Build Helper ===" -ForegroundColor Cyan
Write-Host ""

# Check for Android Studio
$androidStudioPaths = @(
    "${env:ProgramFiles}\Android\Android Studio\bin\studio64.exe",
    "${env:ProgramFiles(x86)}\Android\Android Studio\bin\studio64.exe",
    "${env:LOCALAPPDATA}\Programs\Android\Android Studio\bin\studio64.exe"
)

$androidStudioFound = $false
foreach ($path in $androidStudioPaths) {
    if (Test-Path $path) {
        Write-Host "✅ Android Studio found at: $path" -ForegroundColor Green
        $androidStudioFound = $true
        break
    }
}

if (-not $androidStudioFound) {
    Write-Host "❌ Android Studio not found!" -ForegroundColor Red
    Write-Host "`nPlease install Android Studio first:" -ForegroundColor Yellow
    Write-Host "  1. Download from: https://developer.android.com/studio" -ForegroundColor White
    Write-Host "  2. Run the installer with default settings" -ForegroundColor White
    Write-Host "  3. Complete the first-time setup wizard" -ForegroundColor White
    Write-Host "  4. Run this script again" -ForegroundColor White
    Write-Host "`nSee docs/INSTALL_ANDROID_STUDIO.md for detailed instructions" -ForegroundColor Cyan
    exit 1
}

# Check for Android SDK
$sdkPath = "${env:LOCALAPPDATA}\Android\Sdk"
if (Test-Path $sdkPath) {
    Write-Host "✅ Android SDK found at: $sdkPath" -ForegroundColor Green
} else {
    Write-Host "⚠️  Android SDK not found at expected location" -ForegroundColor Yellow
    Write-Host "   This is OK if you haven't completed Android Studio setup yet" -ForegroundColor Yellow
}

# Check if project is built
if (Test-Path "android\app\src\main\assets\public\index.html") {
    Write-Host "✅ Web assets synced to Android project" -ForegroundColor Green
} else {
    Write-Host "⚠️  Web assets not found. Running build:android..." -ForegroundColor Yellow
    npm run build:android
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n=== Next Steps ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Opening Android Studio..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Try to open Android Studio with the project
$androidProjectPath = (Resolve-Path "android").Path
Write-Host "   Project path: $androidProjectPath" -ForegroundColor Gray

# Try to open with Android Studio
$studioExe = $null
foreach ($path in $androidStudioPaths) {
    if (Test-Path $path) {
        $studioExe = $path
        break
    }
}

if ($studioExe) {
    Write-Host "`n2. Launching Android Studio..." -ForegroundColor Yellow
    Start-Process $studioExe -ArgumentList $androidProjectPath
    Write-Host "   ✅ Android Studio should open with your project" -ForegroundColor Green
} else {
    Write-Host "`n2. Please open Android Studio manually:" -ForegroundColor Yellow
    Write-Host "   - File → Open" -ForegroundColor White
    Write-Host "   - Navigate to: $androidProjectPath" -ForegroundColor White
}

Write-Host "`n3. In Android Studio, build the APK:" -ForegroundColor Yellow
Write-Host "   - Go to: Build → Build Bundle(s) / APK(s) → Build APK(s)" -ForegroundColor White
Write-Host "   - Wait for build to complete" -ForegroundColor White
Write-Host "   - Click 'locate' in the notification to find your APK" -ForegroundColor White

Write-Host "`n4. APK will be located at:" -ForegroundColor Yellow
Write-Host "   android\app\build\outputs\apk\debug\app-debug.apk" -ForegroundColor Cyan

Write-Host "`n=== Tips ===" -ForegroundColor Cyan
Write-Host "- First time: Wait for Gradle sync to complete (may take 5-10 minutes)" -ForegroundColor Gray
Write-Host "- If SDK location error: See docs/INSTALL_ANDROID_STUDIO.md" -ForegroundColor Gray
Write-Host "- For release builds: See docs/BUILD_ANDROID_APK.md" -ForegroundColor Gray
Write-Host ""
