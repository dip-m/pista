# Fix Gradle Version Compatibility Issue

## Problem
The error `Unable to find method 'org.gradle.api.artifacts.Dependency org.gradle.api.artifacts.dsl.DependencyHandler.module(java.lang.Object)'` occurs when:
- Gradle version is too new for the Android Gradle Plugin version
- Or Gradle cache is corrupt

## Solution Applied
✅ Changed Gradle version from 9.0-milestone-1 to 7.5 (compatible with Android Gradle Plugin 7.4.2)

## Compatibility Matrix
- Android Gradle Plugin 7.4.2 → Requires Gradle 7.5 or 7.6
- Gradle 9.0 → Requires Android Gradle Plugin 8.0+

## Next Steps

### 1. Stop Gradle Daemons
In Android Studio:
- **View → Tool Windows → Terminal**
- Run: `./gradlew --stop` (or `gradlew.bat --stop` on Windows)

Or manually:
```bash
cd frontend/android
./gradlew --stop
```

### 2. Clear Gradle Cache
```bash
cd frontend/android
./gradlew clean --refresh-dependencies
```

### 3. Invalidate Caches in Android Studio
- **File → Invalidate Caches / Restart**
- Select **"Invalidate and Restart"**
- Wait for Android Studio to restart

### 4. Delete Gradle Cache (if still failing)
Close Android Studio, then:
```bash
# Windows
rmdir /s "%USERPROFILE%\.gradle\caches"

# Mac/Linux
rm -rf ~/.gradle/caches
```

### 5. Sync Again
After restart:
- **File → Sync Project with Gradle Files**
- Or let Android Studio auto-sync

## Alternative: Upgrade Android Gradle Plugin

If you want to use Gradle 9.0, you need to upgrade:

1. **Update `build.gradle`:**
   ```gradle
   dependencies {
       classpath 'com.android.tools.build:gradle:8.0.0'
   }
   ```

2. **Update `app/build.gradle`:**
   ```gradle
   compileSdkVersion 34
   targetSdkVersion 34
   ```

3. **Update Gradle wrapper to 8.0+**

But for now, Gradle 7.5 is the safest option.
