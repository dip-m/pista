#!/bin/bash
# Build Debug APK for Android
# Usage: ./build-apk-debug.sh

echo "Building Android Debug APK..."

# Navigate to android directory
cd android

# Build debug APK
echo "Running Gradle build..."
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ APK built successfully!"
    APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
    if [ -f "$APK_PATH" ]; then
        FULL_PATH=$(realpath "$APK_PATH")
        echo ""
        echo "APK Location: $FULL_PATH"
        echo ""
        echo "To install on device:"
        echo "  adb install $FULL_PATH"
    fi
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi

# Return to original directory
cd ..
