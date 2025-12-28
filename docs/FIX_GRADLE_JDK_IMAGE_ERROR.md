# Fix Gradle JDK Image Transformation Error

## The Error
```
Execution failed for task ':app:compileDebugJavaWithJavac'.
> Could not resolve all files for configuration ':app:androidJdkImage'.
   > Failed to transform core-for-system-modules.jar to match attributes {artifactType=_internal_android_jdk_image, ...}
      > Error while executing process C:\Program Files\Android\Android Studio\jbr\bin\jlink.exe
```

## Root Cause
This error occurs when Gradle's JDK image transformation process fails, usually due to:
- Corrupted Gradle cache (especially the transforms cache)
- JDK compatibility issues
- Android SDK platform corruption

## Solution Steps (Try in Order)

### Step 1: Clean Gradle Cache (Most Common Fix)

**Option A: Clean Specific Cache (Recommended)**
```powershell
# Navigate to project
cd frontend\android

# Clean the transforms cache (this is where the error occurs)
Remove-Item -Recurse -Force "$env:USERPROFILE\.gradle\caches\transforms-3\*" -ErrorAction SilentlyContinue

# Clean build directories
.\gradlew clean
```

**Option B: Clean All Gradle Cache (If Option A doesn't work)**
```powershell
# Stop all Gradle daemons first
cd frontend\android
.\gradlew --stop

# Remove entire Gradle cache (WARNING: This will re-download everything)
Remove-Item -Recurse -Force "$env:USERPROFILE\.gradle\caches" -ErrorAction SilentlyContinue
```

### Step 2: Invalidate Android Studio Caches

1. Close Android Studio completely
2. Reopen Android Studio
3. Go to: **File → Invalidate Caches / Restart**
4. Select **"Invalidate and Restart"**
5. Wait for Android Studio to restart

### Step 3: Clean and Rebuild Project

In Android Studio:
1. **Build → Clean Project**
2. Wait for it to complete
3. **Build → Rebuild Project**

Or via command line:
```powershell
cd frontend\android
.\gradlew clean
.\gradlew assembleDebug
```

### Step 4: Check Android SDK Platform

The error mentions `android-33`. Verify the platform is installed correctly:

1. In Android Studio: **Tools → SDK Manager**
2. Go to **SDK Platforms** tab
3. Check that **Android 13.0 (Tiramisu) API Level 33** is installed
4. If not installed, install it
5. If installed but corrupted, uncheck it, click **Apply**, then re-check and install again

### Step 5: Update Gradle Configuration (If Above Steps Don't Work)

The `gradle.properties` file has been updated with additional properties to help with JDK image transformation. If issues persist, try:

1. Update Android Gradle Plugin version in `build.gradle`:
   ```gradle
   classpath 'com.android.tools.build:gradle:7.4.2'
   ```

2. Update Gradle wrapper version in `gradle/wrapper/gradle-wrapper.properties`:
   ```properties
   distributionUrl=https\://services.gradle.org/distributions/gradle-7.6-bin.zip
   ```

### Step 6: Check JDK Version

Ensure you're using a compatible JDK:

1. In Android Studio: **File → Settings → Build Tools → Gradle**
2. Check **Gradle JDK** setting
3. Should be: **JetBrains Runtime 17** or **21** (not 8 or 11)
4. If wrong, change it and sync project

### Step 7: Nuclear Option - Fresh Start

If nothing else works:

```powershell
# Stop Gradle daemons
cd frontend\android
.\gradlew --stop

# Remove all Gradle caches
Remove-Item -Recurse -Force "$env:USERPROFILE\.gradle" -ErrorAction SilentlyContinue

# Remove local build directories
Remove-Item -Recurse -Force "frontend\android\.gradle" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "frontend\android\app\build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "frontend\android\build" -ErrorAction SilentlyContinue

# Rebuild from scratch
cd frontend\android
.\gradlew clean
.\gradlew assembleDebug
```

## Prevention

1. **Don't interrupt Gradle builds** - Let them complete
2. **Keep Android Studio updated** - Newer versions fix compatibility issues
3. **Exclude build folders from OneDrive** - See `FIX_ONEDRIVE_BUILD_LOCK.md`
4. **Regularly clean cache** - Run `.\gradlew clean` periodically

## Still Having Issues?

1. Check Android Studio logs: **Help → Show Log in Explorer**
2. Check Gradle logs: `frontend\android\.gradle\`
3. Try building from command line with `--stacktrace`:
   ```powershell
   cd frontend\android
   .\gradlew assembleDebug --stacktrace
   ```
