# Transfer APK to Phone and Monitor Logs

## Step 1: Enable USB Debugging on Your Phone

1. On your Moto G5, go to **Settings**
2. Scroll down to **About phone**
3. Tap **Build number** 7 times (you'll see "You are now a developer!")
4. Go back to **Settings** → **System** → **Developer options**
5. Enable **USB debugging**
6. Enable **Stay awake** (keeps screen on while charging - helpful for testing)

## Step 2: Connect Phone to Computer

1. Connect your Moto G5 to your computer via USB cable
2. On your phone, you'll see a popup: **"Allow USB debugging?"**
3. Check **"Always allow from this computer"**
4. Tap **"Allow"**

## Step 3: Verify ADB Connection

Open PowerShell/Command Prompt on your computer and run:

```powershell
adb devices
```

You should see your device listed:
```
List of devices attached
ABC123XYZ    device
```

If you see "unauthorized", check your phone for the USB debugging prompt.

## Step 4: Transfer APK to Phone

### Option A: Install Directly via ADB (Recommended)

```powershell
cd C:\Users\dipmu\OneDrive\Documents\GitHub\pista\frontend\android\app\build\outputs\apk\debug
adb install app-debug.apk
```

If you have an old version installed, use:
```powershell
adb install -r app-debug.apk
```
(The `-r` flag replaces the existing app)

### Option B: Transfer via USB File Transfer

1. On your phone, when connected via USB, pull down the notification shade
2. Tap the USB notification
3. Select **"File Transfer"** or **"MTP"**
4. On your computer, open File Explorer
5. Your phone should appear as a drive
6. Copy `app-debug.apk` from:
   ```
   C:\Users\dipmu\OneDrive\Documents\GitHub\pista\frontend\android\app\build\outputs\apk\debug\app-debug.apk
   ```
7. Paste it to your phone's **Download** folder
8. On your phone, open **Files** app → **Downloads**
9. Tap `app-debug.apk` → **Install**
10. Allow "Install from unknown sources" if prompted

## Step 5: Set Up Log Monitoring

### Clear Old Logs First

```powershell
adb logcat -c
```

### Start Monitoring (Choose One Method)

#### Method 1: Filter for Debug Logs Only (Recommended)

```powershell
adb logcat | findstr /i "DEBUG"
```

This shows only our debug logs (faster, less clutter).

#### Method 2: Monitor All Logs (More Information)

```powershell
adb logcat
```

This shows all Android logs (more verbose, but shows system errors too).

#### Method 3: Save Logs to File

```powershell
adb logcat > crash_logs.txt
```

Then press `Ctrl+C` to stop after the crash. Logs will be saved to `crash_logs.txt`.

#### Method 4: Filter by App Package Name

```powershell
adb logcat | findstr /i "com.pista.app"
```

Shows only logs from your app.

## Step 6: Reproduce the Crash

1. **Keep the log monitoring terminal open** (don't close it)
2. On your phone, launch the **Pista** app
3. Watch the terminal for log output
4. Let the app crash naturally (don't force-close it)
5. After it crashes, you'll see error messages in the terminal

## Step 7: Capture the Logs

### If Using Method 1, 2, or 4 (Live Monitoring):
- Copy all the text from the terminal
- Paste it into a text file or share it directly

### If Using Method 3 (Saved to File):
- The logs are already in `crash_logs.txt`
- Open the file and share its contents

## What to Look For in Logs

Look for these patterns:
- `[DEBUG]` - Our debug instrumentation messages
- `[DEBUG ERROR]` - Errors caught by our instrumentation
- `FATAL EXCEPTION` - Android system crash reports
- `AndroidRuntime` - Java/Kotlin exceptions
- `chromium` or `WebView` - WebView/JavaScript errors

## Troubleshooting

### "adb: command not found"
- ADB is not in your PATH
- Solution: Use full path or add Android SDK platform-tools to PATH
- Full path example: `C:\Users\dipmu\AppData\Local\Android\Sdk\platform-tools\adb.exe devices`

### "device offline"
- USB connection issue
- Solution: Unplug and replug USB cable, re-authorize USB debugging

### "no devices/emulators found"
- Phone not connected or USB debugging not enabled
- Solution: Check USB connection, verify USB debugging is enabled

### Phone Not Appearing in File Explorer
- USB mode might be set to "Charging only"
- Solution: Pull down notification → Tap USB notification → Select "File Transfer"

## Quick Reference Commands

```powershell
# Check connection
adb devices

# Clear logs
adb logcat -c

# Monitor debug logs
adb logcat | findstr /i "DEBUG"

# Install APK
adb install -r app-debug.apk

# Uninstall app (if needed)
adb uninstall com.pista.app

# Get app logs only
adb logcat | findstr /i "com.pista.app"
```
