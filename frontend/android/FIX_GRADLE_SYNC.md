# Fix Gradle Sync Issues

## Common Issues and Solutions

### 1. Missing Gradle Wrapper

If you see "Gradle wrapper not found":

**Solution:**
```bash
cd frontend/android
gradle wrapper --gradle-version 7.5
```

Or let Android Studio create it:
- File → Settings → Build, Execution, Deployment → Build Tools → Gradle
- Select "Use Gradle from: 'wrapper' task in build script"
- Click "OK" and sync again

### 2. SDK Location Error

If you see "SDK location not found":

**Check local.properties:**
- File should exist at: `frontend/android/local.properties`
- Should contain: `sdk.dir=C\:\\Users\\dipmu\\AppData\\Local\\Android\\Sdk`

**Fix:**
1. File → Settings → Appearance & Behavior → System Settings → Android SDK
2. Note the "Android SDK Location" path
3. Create/update `local.properties` with that path

### 3. Network/Dependency Download Issues

**Symptoms:**
- "Failed to resolve dependencies"
- "Connection timeout"
- "Could not download..."

**Solutions:**

1. **Check internet connection**
2. **Use Gradle offline mode (if dependencies already downloaded):**
   - File → Settings → Build, Execution, Deployment → Build Tools → Gradle
   - Check "Offline work"
   - Uncheck after sync succeeds

3. **Clear Gradle cache:**
   ```bash
   cd frontend/android
   ./gradlew clean --refresh-dependencies
   ```

4. **Use proxy if behind firewall:**
   - File → Settings → Appearance & Behavior → System Settings → HTTP Proxy
   - Configure proxy settings

### 4. Java Version Issues

**Check Java version:**
- File → Settings → Build, Execution, Deployment → Build Tools → Gradle
- Check "Gradle JDK" version
- Should be JDK 11 or later

**Fix:**
- Download JDK 11+ from: https://adoptium.net/
- Point Gradle JDK to the new installation

### 5. Capacitor Dependencies Missing

**Symptoms:**
- "Could not find com.getcapacitor:capacitor-android"
- Missing Capacitor classes

**Fix:**
1. Ensure `@capacitor/android` is installed:
   ```bash
   cd frontend
   npm install @capacitor/android
   ```

2. Sync Capacitor:
   ```bash
   npm run sync:android
   ```

### 6. Build Tools Version Mismatch

**Symptoms:**
- "Build tools version X.X.X is missing"
- "Failed to find Build Tools revision"

**Fix:**
1. File → Settings → Appearance & Behavior → System Settings → Android SDK
2. Go to "SDK Tools" tab
3. Check "Android SDK Build-Tools"
4. Install the version specified in `app/build.gradle` (33.0.0)

### 7. AndroidX Migration Issues

**Symptoms:**
- "package android.support does not exist"
- AndroidX conflicts

**Fix:**
The project uses AndroidX. Ensure:
- `gradle.properties` has:
  ```
  android.useAndroidX=true
  android.enableJetifier=true
  ```

### 8. Clean and Rebuild

**Nuclear option (fixes many issues):**

1. **In Android Studio:**
   - File → Invalidate Caches / Restart
   - Select "Invalidate and Restart"

2. **After restart:**
   - Build → Clean Project
   - Build → Rebuild Project

3. **If still failing:**
   ```bash
   cd frontend/android
   ./gradlew clean
   ./gradlew --stop
   ```
   Then sync again in Android Studio

## Quick Diagnostic Steps

1. **Check Build tab:**
   - View → Tool Windows → Build
   - Look for specific error messages

2. **Check Gradle Console:**
   - View → Tool Windows → Gradle
   - Look for error details

3. **Check Event Log:**
   - Bottom right corner → Event Log
   - Review sync errors

## Get Detailed Error

1. In Android Studio: **Help → Show Log in Explorer**
2. Open `idea.log` or `gradle-*.log`
3. Search for "ERROR" or "FAILED"
4. Share the error message for specific help

## Still Not Working?

Try these in order:

1. File → Invalidate Caches / Restart
2. Delete `.gradle` folder in `android/` directory
3. Delete `android/.idea` folder
4. Re-import project: File → Close Project, then Open the `android` folder again
