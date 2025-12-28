# Installing Android Studio and Building APK

This guide walks you through installing Android Studio and building your first APK.

## Step 1: Install Android Studio

### Download

1. Go to: https://developer.android.com/studio
2. Click "Download Android Studio"
3. Accept the terms and download the installer

### Windows Installation

1. **Run the installer** (`android-studio-*.exe`)
2. **Choose components:**
   - ✅ Android Studio
   - ✅ Android SDK
   - ✅ Android SDK Platform
   - ✅ Android Virtual Device (optional, for emulator)
   - ✅ Performance (Intel HAXM) - if available

3. **Choose installation location:**
   - Default: `C:\Program Files\Android\Android Studio`
   - SDK location: `C:\Users\YourName\AppData\Local\Android\Sdk`

4. **Complete the installation**
5. **Launch Android Studio**

### First Launch Setup

1. **Welcome Screen:**
   - Choose "Do not import settings" (first time)
   - Click "Next"

2. **Setup Wizard:**
   - Choose "Standard" installation
   - Accept license agreements
   - Click "Finish" and wait for components to download

3. **SDK Components:**
   - Android Studio will download required SDK components
   - This may take 10-30 minutes depending on internet speed
   - Wait for "Finish" button to become active

## Step 2: Configure Android Studio

### Verify SDK Installation

1. Go to: **File → Settings** (or **Android Studio → Preferences** on Mac)
2. Navigate to: **Appearance & Behavior → System Settings → Android SDK**
3. Check that these are installed:
   - ✅ Android SDK Platform-Tools
   - ✅ Android SDK Build-Tools
   - ✅ Android SDK Platform (API 33 or latest)
   - ✅ Google Play services (if needed)

### Set Environment Variables (Optional but Recommended)

**Windows:**
1. Open System Properties → Environment Variables
2. Add new System Variable:
   - Name: `ANDROID_HOME`
   - Value: `C:\Users\YourName\AppData\Local\Android\Sdk`
3. Add to Path:
   - `%ANDROID_HOME%\platform-tools`
   - `%ANDROID_HOME%\tools`

**Mac/Linux:**
Add to `~/.bashrc` or `~/.zshrc`:
```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/tools
```

## Step 3: Open Your Project

1. **Open Android Studio**

2. **Open the Android project:**
   ```bash
   cd frontend
   npm run open:android
   ```
   
   Or manually:
   - In Android Studio: **File → Open**
   - Navigate to: `frontend/android`
   - Click "OK"

3. **Wait for Gradle Sync:**
   - Android Studio will sync the project
   - This downloads dependencies (first time may take a while)
   - Watch the bottom status bar for progress

4. **If prompted:**
   - Accept Gradle wrapper download
   - Accept SDK license agreements
   - Install any missing components

## Step 4: Build the APK

### Build Debug APK (Testing)

1. **In Android Studio:**
   - Go to: **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - Wait for build to complete (check bottom status bar)

2. **Find your APK:**
   - A notification will appear: "APK(s) generated successfully"
   - Click "locate" in the notification
   - Or navigate to: `frontend/android/app/build/outputs/apk/debug/app-debug.apk`

3. **Install on device:**
   - Transfer APK to Android device
   - Enable "Install from unknown sources" in device settings
   - Tap the APK file to install

### Build Release APK (Production)

**First, set up signing:**

1. **Generate keystore:**
   ```bash
   keytool -genkey -v -keystore pista-release.keystore -alias pista -keyalg RSA -keysize 2048 -validity 10000
   ```
   - Save keystore in `frontend/android/` directory
   - Remember your passwords!

2. **Configure signing in Android Studio:**
   - Go to: **Build → Generate Signed Bundle / APK**
   - Select **APK**
   - Click "Create new..." for keystore
   - Fill in keystore information
   - Select release build variant
   - Click "Finish"

## Step 5: Troubleshooting

### "SDK location not found"

1. Go to: **File → Settings → Appearance & Behavior → System Settings → Android SDK**
2. Check "Android SDK Location" path
3. Or create `frontend/android/local.properties`:
   ```properties
   sdk.dir=C\:\\Users\\YourName\\AppData\\Local\\Android\\Sdk
   ```

### "Gradle sync failed"

1. **Check internet connection** (Gradle downloads dependencies)
2. **Try:**
   - File → Invalidate Caches / Restart
   - Click "Invalidate and Restart"
3. **Check Gradle version:**
   - File → Project Structure → Project
   - Ensure Gradle version is compatible

### "Build failed: OutOfMemoryError"

1. Increase memory in `frontend/android/gradle.properties`:
   ```properties
   org.gradle.jvmargs=-Xmx4096m -XX:MaxMetaspaceSize=1024m
   ```

### "Execution failed for task ':app:mergeDebugResources'"

1. **Clean project:**
   - Build → Clean Project
   - Build → Rebuild Project

2. **Check for resource conflicts:**
   - Look for duplicate resource names
   - Check `android/app/src/main/res/` folder

### Android Studio is slow

1. **Increase memory:**
   - Help → Edit Custom VM Options
   - Increase `-Xmx` value (e.g., `-Xmx4096m`)
   - Restart Android Studio

2. **Disable unnecessary plugins:**
   - File → Settings → Plugins
   - Disable unused plugins

## Next Steps

Once you have the APK:

1. **Test on device:**
   - Transfer APK to Android device
   - Install and test all features

2. **For Play Store:**
   - Build Android App Bundle (AAB) instead of APK
   - See `docs/BUILD_ANDROID_APK.md` for details

3. **Set up CI/CD:**
   - Automate builds with GitHub Actions
   - See documentation for CI/CD setup

## Quick Reference

```bash
# Open project in Android Studio
cd frontend
npm run open:android

# Build APK (after opening in Android Studio)
# Build → Build Bundle(s) / APK(s) → Build APK(s)

# APK location
frontend/android/app/build/outputs/apk/debug/app-debug.apk
```
