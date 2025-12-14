# Pista - Game Sommelier Frontend

A React application for the Pista game recommendation system.

## Project Structure

```
src/
├── components/
│   ├── features/      # Feature-specific components
│   │   ├── Login.jsx
│   │   ├── Profile.jsx
│   │   └── PistaChat.jsx
│   └── common/         # Shared/reusable components
├── services/           # API services
│   └── auth.js
├── config/             # Configuration files
│   └── api.js
├── styles/             # CSS files
│   └── index.css
├── utils/              # Utility functions
├── App.jsx
└── index.js
```

## Environment Configuration

The app uses environment variables for configuration. Create a `.env` file in the root directory:

```
REACT_APP_API_BASE_URL=http://localhost:8000
```

For production, set:
```
REACT_APP_API_BASE_URL=https://api.pista.com
```

## Development

```bash
npm install
npm start
```

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build/` directory.

## Android Deployment

This project is configured for Android deployment using Capacitor.

### Prerequisites
- Android Studio
- Java Development Kit (JDK)
- Android SDK

### Setup

1. Install Capacitor CLI:
```bash
npm install -g @capacitor/cli
```

2. Add Android platform:
```bash
npx cap add android
```

3. Build the React app:
```bash
npm run build
```

4. Sync with Capacitor:
```bash
npx cap sync android
```

5. Open in Android Studio:
```bash
npx cap open android
```

### Building APK

1. Open the project in Android Studio
2. Build > Generate Signed Bundle / APK
3. Follow the wizard to create your release APK

## Configuration

- API base URL is configured in `src/config/api.js`
- Environment variables are loaded from `.env` files
- Android configuration is in `android/` directory
- Capacitor configuration is in `capacitor.config.json`
