# Debugging App Crash on Launch

## Step 1: Rebuild and Resync

Run these commands to ensure everything is up to date:

```bash
cd frontend
npm run build
npx cap sync android
```

## Step 2: Get the Actual Crash Log

The logs you provided don't show the actual crash. To get the real error:

### Option A: Using ADB (Recommended)
```powershell
# Clear logcat first
adb logcat -c

# Launch the app, then immediately run:
adb logcat -d | Select-String -Pattern "com.pista.app|AndroidRuntime|FATAL" -Context 10,30
```

### Option B: Using Android Studio
1. Open Android Studio
2. Connect your device/emulator
3. Go to **View > Tool Windows > Logcat**
4. Filter by package: `com.pista.app`
5. Launch the app
6. Look for red error messages with stack traces

## Step 3: Common Issues and Fixes

### Issue: JavaScript Error
If the crash is due to a JavaScript error in your React app:
- Check the logcat for "chromium" or "WebView" errors
- The error will show which file and line number failed

### Issue: Missing Assets
If assets are missing:
```bash
cd frontend
npm run build
npx cap sync android
```

### Issue: Capacitor Bridge Not Initialized
The MainActivity now includes logging. Check logcat for "MainActivity onCreate called" to verify it's being called.

## Step 4: Check These Files

1. **MainActivity.java** - Should extend BridgeActivity (✓ Already correct)
2. **AndroidManifest.xml** - Should have MainActivity declared (✓ Already correct)
3. **capacitor.config.json** - Should have correct webDir (✓ Already correct)
4. **build.gradle** - Should have Capacitor dependency (✓ Already added)

## Next Steps

After getting the actual crash log, share it and we can fix the specific issue.
