# How to Get Crash Logs Without ADB in PATH

## Option 1: Use Full Path to ADB

Find your Android SDK location and use the full path:

### Find ADB Location

Common locations:
- `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe`
- `%ProgramFiles%\Android\Android Studio\platform-tools\adb.exe`
- `%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe`

### Use Full Path

```powershell
# Replace with your actual path
& "C:\Users\YourUsername\AppData\Local\Android\Sdk\platform-tools\adb.exe" logcat -d | Select-String -Pattern "com.pista.app|AndroidRuntime|FATAL" -Context 10,30
```

## Option 2: Use Android Studio Logcat (Easiest)

1. **Open Android Studio**
2. **Connect your device/emulator**
3. **Open Logcat**:
   - View → Tool Windows → Logcat
   - Or click the "Logcat" tab at the bottom
4. **Filter by package**:
   - In the filter box, type: `package:com.pista.app`
   - Or use: `tag:AndroidRuntime`
5. **Launch your app**
6. **Look for red error messages** with stack traces

## Option 3: Add ADB to PATH (Permanent Solution)

### Find Your Android SDK

1. Open Android Studio
2. File → Settings → Appearance & Behavior → System Settings → Android SDK
3. Note the "Android SDK Location" path
4. ADB will be at: `[SDK Location]\platform-tools\adb.exe`

### Add to PATH

1. **Open System Environment Variables**:
   - Press `Win + R`
   - Type: `sysdm.cpl` and press Enter
   - Go to "Advanced" tab
   - Click "Environment Variables"

2. **Edit PATH**:
   - Under "User variables", find "Path"
   - Click "Edit"
   - Click "New"
   - Add: `[Your SDK Location]\platform-tools`
   - Example: `C:\Users\YourUsername\AppData\Local\Android\Sdk\platform-tools`
   - Click OK on all dialogs

3. **Restart PowerShell/Terminal**

4. **Test**:
   ```powershell
   adb version
   ```

## Option 4: Quick PowerShell Script

Save this as `get-crash-log.ps1`:

```powershell
# Find ADB
$adbPaths = @(
    "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
    "$env:ProgramFiles\Android\Android Studio\platform-tools\adb.exe",
    "$env:USERPROFILE\AppData\Local\Android\Sdk\platform-tools\adb.exe"
)

$adb = $null
foreach ($path in $adbPaths) {
    if (Test-Path $path) {
        $adb = $path
        break
    }
}

if ($adb) {
    Write-Host "Found ADB at: $adb" -ForegroundColor Green
    Write-Host "Getting crash logs..." -ForegroundColor Yellow
    & $adb logcat -d | Select-String -Pattern "com.pista.app|AndroidRuntime|FATAL" -Context 10,30
} else {
    Write-Host "ADB not found. Please use Android Studio Logcat instead." -ForegroundColor Red
    Write-Host "Or find your Android SDK location and update the script." -ForegroundColor Yellow
}
```

Run it:
```powershell
.\get-crash-log.ps1
```

## Recommended: Use Android Studio Logcat

This is the easiest method and doesn't require any setup!
