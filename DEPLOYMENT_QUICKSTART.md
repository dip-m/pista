# Pista Deployment Quick Start

Quick reference guide for deploying Pista for user testing.

## 🚀 Quick Deployment Steps

### 1. Backend Setup (5 minutes)

#### Option A: Railway (Easiest)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

#### Option B: Render
1. Go to render.com
2. Create new Web Service
3. Connect GitHub repo
4. Set:
   - Build: `pip install -r update_utils/requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (see below)

### 2. Frontend Setup (3 minutes)

```bash
cd frontend

# Create production environment file
echo "REACT_APP_API_BASE_URL=https://your-backend-url.com" > .env.production

# Build
npm install
npm run build

# Deploy to Vercel
npm install -g vercel
vercel --prod
```

### 3. Mobile App Build (10 minutes)

```bash
cd frontend

# Install Capacitor
npm install @capacitor/core @capacitor/cli @capacitor/android

# Update capacitor.config.json - set server.url to your backend URL
# Or leave empty for production builds

# Build and sync
npm run build
npx cap sync android

# Open in Android Studio
npx cap open android

# Build > Generate Signed Bundle / APK
```

---

## 📋 Required Environment Variables

### Backend (.env)
```env
ALLOWED_ORIGINS=https://your-frontend-url.com
JWT_SECRET_KEY=your-random-secret-key
OPENAI_API_KEY=your-key
REPLICATE_API_TOKEN=your-token
```

### Frontend (.env.production)
```env
REACT_APP_API_BASE_URL=https://your-backend-url.com
```

---

## ✅ Pre-Deployment Checklist

- [ ] Database file (`gen/bgg_semantic.db`) exists
- [ ] FAISS index (`gen/game_vectors.index`) exists
- [ ] Backend CORS configured with frontend URL
- [ ] Frontend API URL configured
- [ ] Environment variables set
- [ ] Test backend health: `curl https://your-backend.com/health`
- [ ] Test frontend connects to backend
- [ ] Mobile app API URL configured

---

## 🔗 Useful Commands

```bash
# Backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend build
cd frontend && npm run build

# Android sync
cd frontend && npx cap sync android

# Android build
cd frontend/android && ./gradlew assembleRelease
```

---

For detailed instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
