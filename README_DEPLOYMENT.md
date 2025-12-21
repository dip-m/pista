# Pista Deployment Documentation

This document provides comprehensive deployment instructions for the Pista application.

## 📚 Documentation Files

- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Complete deployment guide with all options
- **[DEPLOYMENT_QUICKSTART.md](./DEPLOYMENT_QUICKSTART.md)** - Quick reference for fast deployment
- **[DEPLOYMENT.md](./frontend/DEPLOYMENT.md)** - Original frontend deployment guide

## 🎯 Quick Start

1. **Prepare environment**:
   ```bash
   # Windows
   .\scripts\prepare-deployment.ps1
   
   # Linux/Mac
   ./scripts/prepare-deployment.sh
   ```

2. **Configure environment variables**:
   - Copy `.env.example` to `.env` and fill in values
   - Copy `frontend/.env.production.example` to `frontend/.env.production` and set API URL

3. **Deploy backend** (choose one):
   - Railway: `railway up`
   - Render: Use `render.yaml` configuration
   - Docker: `docker-compose up -d`

4. **Deploy frontend**:
   ```bash
   cd frontend
   npm run build
   vercel --prod  # or deploy build/ folder to your hosting
   ```

5. **Build mobile app**:
   ```bash
   cd frontend
   npm run build
   npx cap sync android
   npx cap open android
   # Build > Generate Signed Bundle / APK
   ```

## 📦 Required Files for Deployment

Ensure these files exist before deployment:

- `gen/bgg_semantic.db` - SQLite database
- `gen/game_vectors.index` - FAISS index file
- `gen/game_ids.json` - Game ID mapping (if exists)

## 🔧 Configuration Files

- `.env` - Backend environment variables
- `frontend/.env.production` - Frontend production environment
- `frontend/capacitor.config.json` - Mobile app configuration
- `backend/config.py` - Backend configuration loader

## 🚀 Deployment Platforms

### Backend
- **Railway** (Recommended) - Easiest, auto-deploys from Git
- **Render** - Free tier available, easy setup
- **AWS EC2** - Full control, requires server management
- **Docker** - Works on any platform

### Frontend
- **Vercel** (Recommended) - Optimized for React, free tier
- **Netlify** - Easy deployment, good free tier
- **AWS S3 + CloudFront** - Scalable, requires AWS account

### Mobile
- **Google Play Store** - For Android distribution
- **TestFlight** - For iOS beta testing
- **Direct APK distribution** - For internal testing

## 📝 Environment Variables Reference

See `.env.example` and `frontend/.env.production.example` for all required variables.

## 🆘 Need Help?

1. Check [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for detailed instructions
2. Review error logs in your hosting service
3. Verify all environment variables are set correctly
4. Ensure database and index files are accessible

