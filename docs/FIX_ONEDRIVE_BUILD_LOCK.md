# Fix OneDrive Build Lock Issue

## Problem
Android build fails with `AccessDeniedException` because OneDrive is syncing/locking build files.

## Quick Fix (Choose One)

### Option 1: Pause OneDrive Sync (Fastest)
1. Right-click OneDrive icon in system tray (bottom-right)
2. Click **"Pause syncing"** → Select **"2 hours"**
3. Try building again in Android Studio

### Option 2: Exclude Build Folder from OneDrive
1. Right-click OneDrive icon → **Settings**
2. Go to **Account** tab → Click **"Choose folders"**
3. Uncheck the entire **GitHub** folder, OR
4. Navigate to `pista/frontend/android` and uncheck it specifically
5. Click **OK**

### Option 3: Move Project Outside OneDrive (Permanent Fix)
1. Move the entire `pista` project to a non-OneDrive location:
   - Example: `C:\Projects\pista` or `D:\Dev\pista`
2. Update any shortcuts/bookmarks
3. Reopen project in Android Studio from new location

### Option 4: Use OneDrive "Files On-Demand" (If Available)
1. Right-click OneDrive icon → **Settings**
2. Go to **Settings** tab
3. Enable **"Files On-Demand"** (downloads files only when accessed)
4. This reduces file locking issues

## After Fixing
1. Close Android Studio completely
2. Wait 10 seconds
3. Reopen Android Studio
4. File → Invalidate Caches / Restart → **Invalidate and Restart**
5. Build → Clean Project
6. Build → Rebuild Project

## Prevention
- Keep build directories (`build/`, `.gradle/`) excluded from OneDrive
- Consider moving development projects outside OneDrive folders
- Use Git for version control, not OneDrive sync
