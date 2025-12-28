# Build APK - Quick Steps (Android Studio is Open)

## ✅ Setup Complete
- Android Studio: ✅ Installed
- Android SDK: ✅ Found
- Project: ✅ Synced

## Build Steps (Follow in Android Studio)

### Step 1: Wait for Gradle Sync
- Android Studio is syncing the project
- Watch the bottom status bar for "Gradle sync in progress..."
- **First time may take 5-10 minutes** (downloading dependencies)
- Wait until you see "Gradle sync finished" or no sync indicator

### Step 2: Build the APK

1. **In Android Studio menu bar:**
   - Click: **Build**
   - Select: **Build Bundle(s) / APK(s)**
   - Click: **Build APK(s)**

2. **Wait for build:**
   - Check bottom status bar: "Building APK..."
   - This usually takes 1-3 minutes
   - Watch for "Build completed successfully" message

3. **Get your APK:**
   - A notification will appear: "APK(s) generated successfully"
   - Click **"locate"** in the notification
   - Or navigate to: `android/app/build/outputs/apk/debug/app-debug.apk`

### Step 3: Install on Device

**Option A: Using ADB (if device connected)**
```bash
cd frontend
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

**Option B: Manual Transfer**
1. Copy APK to your Android device (USB, email, cloud)
2. On device: Settings → Security → Enable "Install from unknown sources"
3. Open file manager, tap the APK file
4. Tap "Install"

## Troubleshooting

### "Gradle sync failed"
- Check internet connection
- File → Invalidate Caches / Restart → Invalidate and Restart
- Wait for sync to complete

### "SDK location not found"
- File → Settings → Appearance & Behavior → System Settings → Android SDK
- Check "Android SDK Location" path
- Should be: `C:\Users\dipmu\AppData\Local\Android\Sdk`

### Build takes too long
- First build always takes longer (downloading dependencies)
- Subsequent builds are much faster
- Check internet connection speed

### "Build failed"
- Check the "Build" tab at bottom for error messages
- Common fixes:
  - File → Invalidate Caches / Restart
  - Build → Clean Project, then Build → Rebuild Project

## APK Location

Your APK will be here:
```
frontend\android\app\build\outputs\apk\debug\app-debug.apk
```

## Next Steps After Building

1. **Test the APK** on a real Android device
2. **For production:** See `docs/BUILD_ANDROID_APK.md` for release build with signing
3. **For Play Store:** Build Android App Bundle (AAB) instead of APK
