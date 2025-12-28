# Fix JAVA_HOME Not Set Error

## The Error
```
ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH.
Please set the JAVA_HOME variable in your environment to match the location of your Java installation.
```

## Root Cause
Gradle needs to know where Java is installed. If `JAVA_HOME` is not set, Gradle cannot find the Java installation.

## Quick Fix (Current Session Only)

### PowerShell
```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
```

### Verify It Works
```powershell
java -version
```

## Permanent Fix (Recommended)

### Option 1: Set JAVA_HOME in gradle.properties (Already Done)
The `gradle.properties` file has been updated with:
```properties
org.gradle.java.home=C\:\\Program Files\\Android\\Android Studio\\jbr
```

This tells Gradle where to find Java, even if JAVA_HOME is not set in the environment.

### Option 2: Set JAVA_HOME Environment Variable (System-Wide)

**Windows:**
1. Right-click **"This PC"** → **Properties**
2. Click **"Advanced system settings"**
3. Click **"Environment Variables"**
4. Under **"User variables"**, click **"New"**
5. Variable name: `JAVA_HOME`
6. Variable value: `C:\Program Files\Android\Android Studio\jbr`
7. Click **OK** on all dialogs
8. **Restart Android Studio**

**Verify:**
```powershell
echo $env:JAVA_HOME
```

### Option 3: Configure in Android Studio
1. **File → Settings → Build Tools → Gradle**
2. Set **"Gradle JDK"** to: **"JetBrains Runtime"** (or the JDK version you want)
3. Click **OK**
4. Sync project

## What Was Fixed

1. ✅ **Updated `gradle.properties`**
   - Added `org.gradle.java.home` pointing to Android Studio's JDK
   - This ensures Gradle can find Java even without JAVA_HOME set

2. ✅ **Cleaned Gradle cache**
   - Removed corrupted transform cache entries
   - Cleaned local build directories

## Next Steps

1. **In Android Studio:**
   - **File → Invalidate Caches / Restart → Invalidate and Restart**
   - Wait for Android Studio to restart
   - **File → Sync Project with Gradle Files**

2. **Build the project:**
   - **Build → Clean Project**
   - **Build → Rebuild Project**

3. **Or from command line:**
   ```powershell
   cd frontend\android
   .\gradlew.bat clean
   .\gradlew.bat assembleDebug
   ```

## Troubleshooting

### "JAVA_HOME is still not set"
**Solution:** The `gradle.properties` setting should work. If not:
1. Verify the path in `gradle.properties` is correct
2. Check that Android Studio is installed at `C:\Program Files\Android\Android Studio`
3. If Android Studio is elsewhere, update the path in `gradle.properties`

### "Java version mismatch"
**Solution:** Ensure you're using Java 17 or 21:
1. Check `gradle.properties` - `org.gradle.java.home` should point to a JDK 17 or 21
2. In Android Studio: **File → Settings → Build Tools → Gradle**
3. Set **Gradle JDK** to a compatible version

### Build still fails with JDK image transformation error
**Solution:** This is a separate issue. See `FIX_GRADLE_JDK_IMAGE_ERROR.md` for steps to:
1. Clean the Gradle cache again
2. Check Android SDK platform installation
3. Verify JDK compatibility

## Summary

The `gradle.properties` file now includes `org.gradle.java.home`, which tells Gradle where to find Java. This should resolve the JAVA_HOME error. If you still see the error, set the JAVA_HOME environment variable permanently using Option 2 above.
