#!/bin/bash
# Android Build Script
# Usage: ./scripts/build-android.sh

set -e

echo "Building Android APK..."

cd frontend

# Install dependencies
echo "Installing npm dependencies..."
npm install

# Build React app
echo "Building React app..."
npm run build

# Sync to Android
echo "Syncing to Android..."
npx cap sync android

# Build release APK
echo "Building release APK..."
cd android
./gradlew assembleRelease

echo ""
echo "APK built successfully!"
echo "Location: android/app/build/outputs/apk/release/app-release.apk"
echo ""
echo "To build signed APK for Play Store:"
echo "1. Open Android Studio: npx cap open android"
echo "2. Build > Generate Signed Bundle / APK"
echo "3. Select Android App Bundle (AAB) for Play Store"

