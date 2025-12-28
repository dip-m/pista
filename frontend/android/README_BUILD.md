# Building APK - Quick Start

## Prerequisites

1. ✅ Android Studio installed
2. ✅ `npm run build:android` completed successfully
3. ✅ Java JDK 11+ installed

## Quick Build Steps

### Option 1: Using Android Studio (Recommended)

1. **Open project:**
   ```bash
   cd frontend
   npm run open:android
   ```

2. **Build APK:**
   - In Android Studio: **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - Wait for completion
   - Click "locate" in notification

3. **APK Location:**
   ```
   android/app/build/outputs/apk/debug/app-debug.apk
   ```

### Option 2: Command Line

```bash
cd frontend/android
gradlew.bat assembleDebug  # Windows
./gradlew assembleDebug     # Mac/Linux
```

## Troubleshooting

### First Time Setup

If Android Studio shows "SDK location not found":

1. Create `local.properties` in this directory (`android/`)
2. Add your SDK path:
   ```properties
   sdk.dir=C\:\\Users\\YourName\\AppData\\Local\\Android\\Sdk
   ```
   (Windows - adjust path for your system)

   ```properties
   sdk.dir=/Users/YourName/Library/Android/sdk
   ```
   (Mac)

   ```properties
   sdk.dir=/home/YourName/Android/Sdk
   ```
   (Linux)

### Gradle Sync Issues

- Check internet connection
- File → Invalidate Caches / Restart
- Wait for all downloads to complete

## Need Help?

See full documentation:
- `docs/INSTALL_ANDROID_STUDIO.md` - Installation guide
- `docs/BUILD_ANDROID_APK.md` - Detailed build instructions
