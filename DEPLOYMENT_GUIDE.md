# Pista Deployment Guide

Complete guide for deploying Pista web app and mobile app for user testing.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Web App Deployment](#web-app-deployment)
3. [Mobile App Deployment](#mobile-app-deployment)
4. [Backend Deployment](#backend-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Testing Checklist](#testing-checklist)

---

## Prerequisites

### Required Software
- **Node.js** (v16 or higher) and npm
- **Python** (v3.8 or higher) and pip
- **Git** for version control
- **Android Studio** (for mobile app builds)
- **Java JDK** (v8 or higher, for Android builds)

### Required Accounts/Services
- **Web Hosting**: Choose one:
  - Vercel (recommended for React apps)
  - Netlify
  - AWS S3 + CloudFront
  - Any static hosting service
- **Backend Hosting**: Choose one:
  - Railway
  - Render
  - AWS EC2/ECS
  - DigitalOcean
  - Heroku
  - Google Cloud Run
- **Database**: SQLite (included) or PostgreSQL (for production scale)
- **Domain Name** (optional but recommended)

---

## Environment Configuration

### Backend Environment Variables

Create a `.env` file in the project root:

```env
# Backend Configuration
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000

# CORS - Add your frontend URLs
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://www.your-frontend-domain.com

# Database
DB_PATH=./gen/bgg_semantic.db

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# OpenAI API (for image generation)
OPENAI_API_KEY=your-openai-api-key

# Replicate API (for image generation)
REPLICATE_API_TOKEN=your-replicate-token

# Logging
LOG_LEVEL=INFO
```

### Frontend Environment Variables

Create `.env.production` in the `frontend/` directory:

```env
REACT_APP_API_BASE_URL=https://your-backend-api-domain.com
```

---

## Backend Deployment

### Option 1: Railway (Recommended for Quick Deployment)

1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Initialize Railway Project**:
   ```bash
   cd C:\Users\dipmu\OneDrive\Documents\GitHub\pista
   railway init
   ```

3. **Set Environment Variables** in Railway dashboard:
   - Add all variables from `.env` file
   - Set `ALLOWED_ORIGINS` to your frontend URL

4. **Deploy**:
   ```bash
   railway up
   ```

### Option 2: Render

1. **Create New Web Service** in Render dashboard
2. **Connect your GitHub repository**
3. **Configure**:
   - **Build Command**: `pip install -r update_utils/requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3
4. **Add Environment Variables** from `.env` file
5. **Deploy**

### Option 3: AWS EC2

1. **Launch EC2 Instance** (Ubuntu 22.04 LTS recommended)
2. **SSH into instance** and run:
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python and dependencies
   sudo apt install python3-pip python3-venv nginx -y
   
   # Clone repository
   git clone https://github.com/your-username/pista.git
   cd pista
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r update_utils/requirements.txt
   
   # Set up systemd service (see backend/systemd/pista.service)
   sudo cp backend/systemd/pista.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable pista
   sudo systemctl start pista
   
   # Configure Nginx (see backend/nginx/pista.conf)
   sudo cp backend/nginx/pista.conf /etc/nginx/sites-available/pista
   sudo ln -s /etc/nginx/sites-available/pista /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Option 4: Docker (Any Platform)

1. **Build Docker image**:
   ```bash
   docker build -t pista-backend -f Dockerfile.backend .
   ```

2. **Run container**:
   ```bash
   docker run -d \
     --name pista-backend \
     -p 8000:8000 \
     --env-file .env \
     -v $(pwd)/gen:/app/gen \
     pista-backend
   ```

---

## Web App Deployment

### Step 1: Update API Configuration

1. **Update `frontend/src/config/api.js`** (already uses environment variable)
2. **Create `.env.production`**:
   ```env
   REACT_APP_API_BASE_URL=https://your-backend-api-domain.com
   ```

### Step 2: Build Production Bundle

```bash
cd frontend
npm install
npm run build
```

This creates a `build/` directory with optimized production files.

### Step 3: Deploy to Hosting Service

#### Option A: Vercel (Recommended)

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Deploy**:
   ```bash
   cd frontend
   vercel --prod
   ```

3. **Set Environment Variable** in Vercel dashboard:
   - `REACT_APP_API_BASE_URL` = your backend URL

#### Option B: Netlify

1. **Install Netlify CLI**:
   ```bash
   npm install -g netlify-cli
   ```

2. **Deploy**:
   ```bash
   cd frontend
   netlify deploy --prod --dir=build
   ```

3. **Set Environment Variable** in Netlify dashboard

#### Option C: AWS S3 + CloudFront

1. **Create S3 bucket**:
   ```bash
   aws s3 mb s3://pista-frontend
   ```

2. **Upload build files**:
   ```bash
   aws s3 sync frontend/build/ s3://pista-frontend --delete
   ```

3. **Enable static website hosting** in S3 bucket settings

4. **Create CloudFront distribution** pointing to S3 bucket

#### Option D: Any Static Hosting

Simply upload the contents of `frontend/build/` to your hosting service.

---

## Mobile App Deployment (Android)

### Prerequisites

1. **Install Capacitor**:
   ```bash
   cd frontend
   npm install -g @capacitor/cli
   npm install @capacitor/core @capacitor/cli @capacitor/android
   ```

2. **Update Capacitor Config**:
   - Edit `frontend/capacitor.config.json`
   - Update `server.url` to your production backend URL (remove for production)
   - Or set it to empty string `""` for production builds

### Step 1: Build React App

```bash
cd frontend
npm run build
```

### Step 2: Sync to Android

```bash
npx cap sync android
```

### Step 3: Configure Android App

1. **Update API URL** in `frontend/android/app/src/main/java/.../MainActivity.java` if needed
2. **Update app icons** in `frontend/android/app/src/main/res/`
3. **Update version** in `frontend/android/app/build.gradle`:
   ```gradle
   versionCode 2  // Increment for each release
   versionName "1.0.1"
   ```

### Step 4: Build Release APK

#### Using Android Studio (Recommended)

1. **Open project**:
   ```bash
   npx cap open android
   ```

2. **Generate Signed Bundle/APK**:
   - Build > Generate Signed Bundle / APK
   - Select **APK** (for direct distribution) or **Android App Bundle** (for Play Store)
   - Create keystore if first time:
     - Key store path: `android/app/pista-release-key.jks`
     - Password: (save securely!)
     - Key alias: `pista-key`
     - Validity: 25 years
   - Choose **release** build variant
   - Finish

3. **APK location**: `android/app/release/app-release.apk`

#### Using Command Line

1. **Create keystore** (first time only):
   ```bash
   keytool -genkey -v -keystore android/app/pista-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias pista-key
   ```

2. **Create `android/key.properties`**:
   ```properties
   storePassword=your-keystore-password
   keyPassword=your-key-password
   keyAlias=pista-key
   storeFile=pista-release-key.jks
   ```

3. **Update `android/app/build.gradle`** to use keystore (see provided example)

4. **Build**:
   ```bash
   cd android
   ./gradlew assembleRelease
   ```

### Step 5: Distribute APK

#### For Internal Testing

1. **Upload APK** to:
   - Google Drive
   - Firebase App Distribution
   - TestFlight (iOS) or Google Play Internal Testing
   - Direct download link

2. **Share download link** with testers

#### For Google Play Store

1. **Create app** in Google Play Console
2. **Upload AAB** (Android App Bundle) file
3. **Complete store listing**
4. **Submit for review**

---

## iOS Deployment (Optional)

### Prerequisites

- **macOS** with Xcode installed
- **Apple Developer Account** ($99/year)

### Steps

1. **Add iOS platform**:
   ```bash
   cd frontend
   npm install @capacitor/ios
   npx cap add ios
   ```

2. **Build and sync**:
   ```bash
   npm run build
   npx cap sync ios
   ```

3. **Open in Xcode**:
   ```bash
   npx cap open ios
   ```

4. **Configure signing** in Xcode
5. **Build and archive** for App Store or TestFlight

---

## Production Checklist

### Backend

- [ ] Environment variables configured
- [ ] CORS origins updated to production URLs
- [ ] Database file (`bgg_semantic.db`) uploaded/copied to server
- [ ] FAISS index file (`game_vectors.index`) uploaded/copied to server
- [ ] JWT secret key changed from default
- [ ] API keys (OpenAI, Replicate) configured
- [ ] Logging configured
- [ ] HTTPS/SSL enabled
- [ ] Rate limiting configured (if needed)
- [ ] Backup strategy in place

### Frontend (Web)

- [ ] `.env.production` created with correct API URL
- [ ] Production build created (`npm run build`)
- [ ] Build files deployed to hosting service
- [ ] Environment variable set in hosting dashboard
- [ ] Custom domain configured (if applicable)
- [ ] HTTPS enabled
- [ ] Analytics/tracking added (if needed)

### Mobile App

- [ ] Capacitor config updated with production API URL
- [ ] App icons updated
- [ ] App name and version updated
- [ ] Keystore created and secured
- [ ] Release APK/AAB built
- [ ] Tested on physical devices
- [ ] Permissions configured correctly
- [ ] App signing verified

### Testing

- [ ] Backend API accessible from frontend
- [ ] Authentication flow works
- [ ] Game search works
- [ ] Feature search works
- [ ] Chat functionality works
- [ ] Image upload works (if applicable)
- [ ] Mobile app connects to backend
- [ ] Mobile app works offline (if applicable)
- [ ] Error handling works correctly
- [ ] Loading states display correctly

---

## Troubleshooting

### Backend Issues

**CORS Errors**:
- Ensure `ALLOWED_ORIGINS` includes your frontend URL
- Check that backend allows credentials if using cookies

**Database Not Found**:
- Ensure `bgg_semantic.db` is in the correct path
- Check file permissions

**FAISS Index Not Found**:
- Ensure `game_vectors.index` is in `gen/` directory
- Verify file path in `main.py`

### Frontend Issues

**API Connection Failed**:
- Verify `REACT_APP_API_BASE_URL` is set correctly
- Check CORS configuration on backend
- Verify backend is running and accessible

**Build Fails**:
- Clear cache: `npm run build -- --no-cache`
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

### Mobile App Issues

**App Can't Connect to Backend**:
- Update `capacitor.config.json` `server.url` to production URL
- For production, remove `server.url` or set to empty string
- Ensure backend CORS allows mobile app origin

**Build Errors**:
- Clean Android project: `cd android && ./gradlew clean`
- Update Capacitor: `npx cap update`
- Sync assets: `npx cap sync android`

---

## Security Considerations

1. **Never commit** `.env` files or API keys to git
2. **Use HTTPS** for all production deployments
3. **Rotate JWT secret keys** regularly
4. **Implement rate limiting** on API endpoints
5. **Validate all user inputs** on backend
6. **Use parameterized queries** (already implemented)
7. **Keep dependencies updated**
8. **Monitor logs** for suspicious activity
9. **Backup database** regularly
10. **Use environment-specific configurations**

---

## Monitoring and Maintenance

### Recommended Tools

- **Error Tracking**: Sentry, Rollbar
- **Analytics**: Google Analytics, Mixpanel
- **Uptime Monitoring**: UptimeRobot, Pingdom
- **Log Aggregation**: Loggly, Papertrail

### Regular Tasks

- Monitor error logs daily
- Review user feedback
- Update dependencies monthly
- Backup database weekly
- Review security patches
- Monitor API usage and costs

---

## Support

For issues or questions:
1. Check logs in backend hosting service
2. Review browser console for frontend errors
3. Check network tab for API call failures
4. Review this deployment guide
5. Check GitHub issues (if public)
