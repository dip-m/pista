# Deployment Guide

## React Web Deployment

### Production Build

1. Set environment variables:
   - Create `.env.production` file or set `REACT_APP_API_BASE_URL` environment variable
   - Example: `REACT_APP_API_BASE_URL=https://api.pista.com`

2. Build the application:
   ```bash
   npm run build
   ```

3. Deploy the `build/` directory to your hosting service:
   - Netlify: Drag and drop the `build` folder
   - Vercel: Connect your repo and set build command to `npm run build`
   - AWS S3 + CloudFront: Upload `build/` contents to S3 bucket
   - Any static hosting service

### Environment Variables

The app uses `REACT_APP_API_BASE_URL` to configure the API endpoint. Make sure this is set correctly for your environment.

## Android Deployment

### Prerequisites

- Node.js and npm installed
- Android Studio installed
- Java Development Kit (JDK) 8 or higher
- Android SDK installed via Android Studio

### Setup Steps

1. Install Capacitor CLI globally:
   ```bash
   npm install -g @capacitor/cli
   ```

2. Install Capacitor dependencies:
   ```bash
   cd frontend
   npm install @capacitor/core @capacitor/cli @capacitor/android
   ```

3. Build the React app:
   ```bash
   npm run build
   ```

4. Initialize Capacitor (if not already done):
   ```bash
   npx cap init
   ```
   - App name: Pista
   - App ID: com.pista.app
   - Web dir: build

5. Add Android platform:
   ```bash
   npx cap add android
   ```

6. Sync web assets to Android:
   ```bash
   npx cap sync android
   ```

7. Open in Android Studio:
   ```bash
   npx cap open android
   ```

### Building Release APK

1. In Android Studio:
   - Build > Generate Signed Bundle / APK
   - Select APK
   - Create or select a keystore
   - Choose release build variant
   - Finish the wizard

2. The APK will be generated at:
   `android/app/release/app-release.apk`

### Building AAB (Android App Bundle)

For Google Play Store:

1. In Android Studio:
   - Build > Generate Signed Bundle / APK
   - Select Android App Bundle
   - Follow the same signing process

2. Upload the generated `.aab` file to Google Play Console

### Configuration

- Update `capacitor.config.json` with your production API URL
- Update `android/app/src/main/AndroidManifest.xml` if needed
- Configure app icons in `android/app/src/main/res/`

### Troubleshooting

- If build fails, ensure all dependencies are installed: `npm install`
- Clear build cache: `npm run build -- --no-cache`
- For Android: Clean project in Android Studio (Build > Clean Project)
- Check that API URL is accessible from Android device/emulator

