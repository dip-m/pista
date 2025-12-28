# How to Get Better Crash Logs

The previous logs didn't show a clear crash. Here's how to capture the actual error:

## Method 1: Real-Time Capture (Best)

1. **Clear logcat:**
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" logcat -c
   ```

2. **Start capturing in real-time:**
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" logcat -v time *:E AndroidRuntime:E | Select-String -Pattern "com.pista.app|FATAL|Exception|Error" -Context 5,20
   ```

3. **Launch your app** (while the command is running)

4. **Wait for the crash** - you should see the error appear in real-time

## Method 2: Use the Helper Script

Run the real-time capture script:
```powershell
cd frontend
.\capture-crash-realtime.ps1
```

Then launch your app.

## Method 3: Android Studio Logcat (Easiest)

1. Open Android Studio
2. Connect your device/emulator
3. **View → Tool Windows → Logcat**
4. **Filter by:** `package:com.pista.app`
5. **Set log level to:** `Error` or `Verbose`
6. **Launch your app**
7. **Look for red error messages** with stack traces

## What to Look For

The crash log should show:
- **AndroidRuntime:** followed by a stack trace
- **FATAL EXCEPTION:** with exception type
- **at com.pista.app.** - your app's code
- **Caused by:** - the root cause

## Common Crash Patterns

### JavaScript Error
Look for:
- `chromium` errors
- `WebView` errors  
- `console.error` messages
- File names like `index.html` or `.js` files

### Native Crash
Look for:
- `AndroidRuntime: FATAL EXCEPTION`
- `java.lang.*Exception`
- Stack trace starting with `at android.` or `at com.getcapacitor.`

### Asset Loading Error
Look for:
- `FileNotFoundException`
- `AssetManager` errors
- `index.html` not found

## Enhanced Logging

The MainActivity now has enhanced logging. After launching, check for:
- `MainActivity onCreate called` - confirms activity started
- `MainActivity onCreate completed successfully` - confirms initialization worked
- Any `Error in onCreate` messages - shows what failed

## Next Steps

Once you have the crash log:
1. Share the **full stack trace**
2. Note the **exception type** (e.g., `NullPointerException`, `FileNotFoundException`)
3. Check if it's a **JavaScript error** or **native error**
