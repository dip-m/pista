# PWA Setup Guide for Android and iOS

This guide explains how to set up and deploy Pista as a Progressive Web App (PWA) for Android and iOS.

## Features

- ✅ **Offline Support**: Service worker caches assets and API responses
- ✅ **Install Prompts**: Automatic install prompts for Android and iOS
- ✅ **Standalone Mode**: Runs as a native-like app when installed
- ✅ **App Icons**: Custom icons for home screen
- ✅ **Splash Screen**: Custom splash screen on launch
- ✅ **Dark Mode**: Full dark mode support

## Web PWA (Browser-based)

The app is already configured as a PWA and can be installed directly from browsers:

### Android (Chrome/Edge)
1. Visit the app in Chrome/Edge
2. Tap the menu (three dots)
3. Select "Install app" or "Add to Home screen"
4. Or wait for the automatic install prompt

### iOS (Safari)
1. Visit the app in Safari
2. Tap the Share button
3. Select "Add to Home Screen"
4. Or follow the on-screen instructions

## Native Apps with Capacitor

### Prerequisites

```bash
# Install Capacitor CLI globally (optional, but recommended)
npm install -g @capacitor/cli

# Install Capacitor dependencies in the project
cd frontend
npm install

# The following packages should be in package.json:
# - @capacitor/core
# - @capacitor/cli
# - @capacitor/android (for Android)
# - @capacitor/ios (for iOS)
```

### Android Setup

1. **Build the web app:**
   ```bash
   npm run build
   ```

2. **Sync with Android:**
   ```bash
   npm run sync:android
   # Or use the combined command:
   npm run build:android
   ```

3. **Build APK:**

   **Option A: Command Line (Quick)**
   ```bash
   # Debug APK (no signing required)
   cd android
   gradlew.bat assembleDebug  # Windows
   ./gradlew assembleDebug     # Mac/Linux
   ```
   
   Or use the helper script:
   ```bash
   # Windows
   .\build-apk-debug.ps1
   
   # Mac/Linux
   chmod +x build-apk-debug.sh
   ./build-apk-debug.sh
   ```
   
   APK will be at: `android/app/build/outputs/apk/debug/app-debug.apk`

   **Option B: Android Studio (Recommended for Release)**
   ```bash
   npm run open:android
   ```
   - In Android Studio: **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - For release builds: **Build → Generate Signed Bundle / APK**

4. **For Release APK (Production):**
   - See `docs/BUILD_ANDROID_APK.md` for detailed signing instructions
   - Requires keystore setup for signing

### iOS Setup

1. **Add iOS platform (if not already added):**
   ```bash
   npx cap add ios
   ```
   
   Note: `@capacitor/ios` should already be in package.json. If not, install it:
   ```bash
   npm install @capacitor/ios
   ```

2. **Build the web app:**
   ```bash
   npm run build
   ```

3. **Sync with iOS:**
   ```bash
   npm run sync:ios
   # Or use the combined command:
   npm run build:ios
   ```

4. **Open in Xcode:**
   ```bash
   npm run open:ios
   ```

5. **Build in Xcode:**
   - Select your development team
   - Choose a device or simulator
   - Click Run or Product → Archive for App Store

## Configuration Files

### `capacitor.config.json`
- **appId**: `com.pista.app` - Unique app identifier
- **appName**: `Pista` - Display name
- **webDir**: `build` - Web assets directory
- **android/ios**: Platform-specific settings

### `public/manifest.json`
- PWA manifest with app metadata
- Icons, theme colors, display mode
- Shortcuts and share target configuration

### `public/service-worker.js`
- Service worker for offline support
- Caching strategy (network-first with cache fallback)
- Background sync for offline messages

## Building for Production

### Android APK/AAB

1. **Generate keystore** (first time only):
   ```bash
   keytool -genkey -v -keystore pista-release.keystore -alias pista -keyalg RSA -keysize 2048 -validity 10000
   ```

2. **Update `capacitor.config.json`** with keystore path and passwords

3. **Build in Android Studio:**
   - Build → Generate Signed Bundle / APK
   - Select "Android App Bundle" for Play Store
   - Or "APK" for direct distribution

### iOS App Store

1. **Open in Xcode:**
   ```bash
   npm run open:ios
   ```

2. **Configure signing:**
   - Select your development team
   - Set bundle identifier
   - Configure capabilities

3. **Archive:**
   - Product → Archive
   - Upload to App Store Connect
   - Submit for review

## Environment Variables

Make sure to set these in your build environment:

- `REACT_APP_API_BASE_URL`: Backend API URL
- `REACT_APP_GOOGLE_CLIENT_ID`: Google OAuth client ID (optional)
- Other OAuth credentials as needed

## Testing PWA Features

### Test Service Worker
1. Open DevTools → Application → Service Workers
2. Check registration status
3. Test offline mode (Network tab → Offline)

### Test Install Prompt
1. Use Chrome DevTools → Application → Manifest
2. Check installability
3. Test on real device for best results

### Test Offline Mode
1. Load the app
2. Go offline (airplane mode)
3. Verify cached pages load
4. Check service worker cache in DevTools

## Troubleshooting

### Service Worker Not Registering
- Check browser console for errors
- Verify `service-worker.js` is in `public/` folder
- Ensure HTTPS (required for service workers in production)

### Install Prompt Not Showing
- Must be served over HTTPS (or localhost)
- Must have valid manifest.json
- Must have service worker registered
- User must visit site multiple times (browser requirement)

### Capacitor Build Issues
- Ensure `npm run build` completed successfully
- Check `capacitor.config.json` syntax
- Verify platform was added: `npx cap add android` or `npx cap add ios`

### iOS Build Issues
- Requires macOS and Xcode
- Need Apple Developer account for device testing
- Check signing certificates in Xcode

## Additional Resources

- [Capacitor Documentation](https://capacitorjs.com/docs)
- [PWA Best Practices](https://web.dev/pwa-checklist/)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
