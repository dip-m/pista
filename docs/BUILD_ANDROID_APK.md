# Building Android APK for Pista

This guide explains how to build an Android APK from the Capacitor project.

## Prerequisites

- ✅ `npm run build:android` completed successfully
- Android Studio installed (recommended) OR Android SDK with command line tools
- Java Development Kit (JDK) 11 or later

## Method 1: Using Android Studio (Recommended)

### Step 1: Open Project in Android Studio

```bash
cd frontend
npm run open:android
```

This will open the Android project in Android Studio.

### Step 2: Build APK

1. **For Debug APK (testing):**
   - In Android Studio, go to: **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - Wait for the build to complete
   - Click "locate" in the notification to find the APK
   - Location: `android/app/build/outputs/apk/debug/app-debug.apk`

2. **For Release APK (production):**
   - First, set up signing (see "Signing Configuration" below)
   - Go to: **Build → Generate Signed Bundle / APK**
   - Select **APK** (not Android App Bundle)
   - Choose your keystore file and enter passwords
   - Select release build variant
   - Click Finish
   - Location: `android/app/build/outputs/apk/release/app-release.apk`

## Method 2: Using Command Line (Gradle)

### Debug APK (No Signing Required)

```bash
cd frontend/android
./gradlew assembleDebug
```

**Windows:**
```bash
cd frontend\android
gradlew.bat assembleDebug
```

The APK will be at: `android/app/build/outputs/apk/debug/app-debug.apk`

### Release APK (Requires Signing)

1. **Set up signing first** (see below)
2. **Build release APK:**

```bash
cd frontend/android
./gradlew assembleRelease
```

**Windows:**
```bash
cd frontend\android
gradlew.bat assembleRelease
```

The APK will be at: `android/app/build/outputs/apk/release/app-release.apk`

## Signing Configuration (For Release APK)

### Step 1: Generate Keystore

```bash
keytool -genkey -v -keystore pista-release.keystore -alias pista -keyalg RSA -keysize 2048 -validity 10000
```

You'll be prompted for:
- Keystore password (remember this!)
- Key password (can be same as keystore password)
- Your name, organization, etc.

**Important:** Keep the keystore file safe! You'll need it for all future updates.

### Step 2: Configure Signing in Android Studio

1. Open `android/app/build.gradle`
2. Add signing config (see example below)
3. Update `buildTypes` to use the signing config

### Step 3: Alternative - Use gradle.properties (More Secure)

1. Create/update `android/keystore.properties`:
   ```properties
   storeFile=../pista-release.keystore
   storePassword=your-keystore-password
   keyAlias=pista
   keyPassword=your-key-password
   ```

2. Add to `.gitignore`:
   ```
   android/keystore.properties
   android/*.keystore
   ```

3. Update `android/app/build.gradle` to load from properties file

## Quick Build Script

Create a helper script for easier building:

### Windows (`build-apk.ps1`)

```powershell
# build-apk.ps1
cd frontend
npm run build
cd android
.\gradlew.bat assembleDebug
Write-Host "APK location: android\app\build\outputs\apk\debug\app-debug.apk"
```

### Linux/Mac (`build-apk.sh`)

```bash
#!/bin/bash
# build-apk.sh
cd frontend
npm run build
cd android
./gradlew assembleDebug
echo "APK location: android/app/build/outputs/apk/debug/app-debug.apk"
```

## Installing the APK

### On Device

1. **Enable Developer Options:**
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
   - Go back to Settings → Developer Options
   - Enable "USB Debugging" (optional, for ADB)

2. **Transfer APK:**
   - Copy APK to device via USB, email, or cloud storage
   - Open file manager on device
   - Tap the APK file
   - Allow installation from unknown sources if prompted
   - Install

### Using ADB (Android Debug Bridge)

```bash
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

## Troubleshooting

### "Gradle sync failed"

- Make sure Android Studio is up to date
- Check internet connection (Gradle downloads dependencies)
- Try: **File → Invalidate Caches / Restart**

### "SDK location not found"

- Set `ANDROID_HOME` environment variable:
  - Windows: `C:\Users\YourName\AppData\Local\Android\Sdk`
  - Mac/Linux: `~/Library/Android/sdk` or `/opt/android-sdk`
- Or set in `local.properties` in `android/` folder:
  ```properties
  sdk.dir=C\:\\Users\\YourName\\AppData\\Local\\Android\\Sdk
  ```

### "Keystore file not found"

- Make sure keystore path in `build.gradle` is correct
- Use relative path from `android/app/` directory
- Or use absolute path

### Build fails with "OutOfMemoryError"

- Increase Gradle memory in `android/gradle.properties`:
  ```properties
  org.gradle.jvmargs=-Xmx2048m -XX:MaxMetaspaceSize=512m
  ```

### "Execution failed for task ':app:mergeDebugResources'"

- Clean and rebuild:
  ```bash
  cd android
  ./gradlew clean
  ./gradlew assembleDebug
  ```

## Building for Google Play Store

For Play Store, you need an **Android App Bundle (AAB)**, not APK:

1. In Android Studio: **Build → Generate Signed Bundle / APK**
2. Select **Android App Bundle**
3. Choose release variant
4. Upload the `.aab` file to Play Console

Or via command line:
```bash
cd frontend/android
./gradlew bundleRelease
```

Location: `android/app/build/outputs/bundle/release/app-release.aab`

## Next Steps

- Test the APK on multiple devices
- Set up CI/CD for automated builds
- Configure app signing for production releases
- Prepare store listings (screenshots, descriptions, etc.)
