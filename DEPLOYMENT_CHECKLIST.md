# Pista Deployment Checklist

Use this checklist to ensure everything is ready for deployment.

## Pre-Deployment

### Code Preparation
- [ ] All code committed to version control
- [ ] No debug/instrumentation code remaining
- [ ] No hardcoded API keys or secrets
- [ ] Environment variables documented
- [ ] `.gitignore` updated to exclude sensitive files

### Backend Preparation
- [ ] Database file (`gen/bgg_semantic.db`) exists and is up-to-date
- [ ] FAISS index file (`gen/game_vectors.index`) exists
- [ ] Game ID mapping file (`gen/game_ids.json`) exists (if used)
- [ ] `.env` file created with production values
- [ ] CORS origins configured for production frontend URL
- [ ] JWT secret key changed from default
- [ ] API keys (OpenAI, Replicate) configured
- [ ] Health check endpoint tested (`/health`)

### Frontend Preparation
- [ ] `frontend/.env.production` created with backend API URL
- [ ] API configuration uses environment variable (not hardcoded)
- [ ] Production build tested locally
- [ ] All assets load correctly
- [ ] No console errors in production build

### Mobile App Preparation
- [ ] Capacitor installed and configured
- [ ] `capacitor.config.json` updated with production API URL
- [ ] App icons created and added
- [ ] App name and version updated
- [ ] Android permissions configured correctly
- [ ] Keystore created for signing (if releasing to Play Store)

## Deployment Steps

### Backend Deployment
- [ ] Backend hosting service selected and account created
- [ ] Repository connected (if using Git-based deployment)
- [ ] Environment variables set in hosting dashboard
- [ ] Database file uploaded/copied to server
- [ ] FAISS index file uploaded/copied to server
- [ ] Backend deployed and running
- [ ] Health check endpoint accessible
- [ ] CORS working (test from frontend)
- [ ] API endpoints responding correctly

### Frontend Deployment
- [ ] Frontend hosting service selected and account created
- [ ] Production build created (`npm run build`)
- [ ] Environment variable set in hosting dashboard
- [ ] Build files deployed
- [ ] Custom domain configured (if applicable)
- [ ] HTTPS enabled
- [ ] Frontend accessible and loads correctly
- [ ] Frontend connects to backend API
- [ ] All features working (login, search, chat, etc.)

### Mobile App Deployment
- [ ] React app built for production
- [ ] Capacitor sync completed
- [ ] Android project opened in Android Studio
- [ ] App signed with release keystore
- [ ] Release APK/AAB built
- [ ] APK tested on physical device
- [ ] App connects to production backend
- [ ] All features working on mobile
- [ ] APK distributed to testers (or uploaded to Play Store)

## Post-Deployment Testing

### Backend Testing
- [ ] Health endpoint: `GET /health` returns 200
- [ ] Authentication: Login/Register works
- [ ] Game search: `GET /games/search?q=test` works
- [ ] Chat endpoint: `POST /chat` works
- [ ] CORS: Frontend can make requests
- [ ] Error handling: Appropriate error responses

### Frontend Testing
- [ ] Homepage loads
- [ ] Login/Register flow works
- [ ] Game search works
- [ ] Feature search works (@ mentions)
- [ ] Chat functionality works
- [ ] Dark mode works
- [ ] Responsive design works on mobile browsers
- [ ] No console errors
- [ ] Loading states display correctly

### Mobile App Testing
- [ ] App installs successfully
- [ ] App launches without crashes
- [ ] Login/Register works
- [ ] Game search works
- [ ] Feature search works
- [ ] Chat functionality works
- [ ] App works in portrait and landscape
- [ ] Back button navigation works
- [ ] App handles network errors gracefully
- [ ] App works offline (if applicable)

## Security Checklist

- [ ] `.env` files not committed to Git
- [ ] API keys not in code
- [ ] JWT secret is strong and unique
- [ ] HTTPS enabled for all services
- [ ] CORS configured correctly (not `*` in production)
- [ ] Database file permissions restricted
- [ ] Error messages don't expose sensitive info
- [ ] Input validation on all endpoints
- [ ] Rate limiting configured (if needed)
- [ ] Logs don't contain sensitive data

## Monitoring Setup

- [ ] Error tracking configured (Sentry, etc.)
- [ ] Analytics configured (Google Analytics, etc.)
- [ ] Uptime monitoring configured
- [ ] Log aggregation set up
- [ ] Alerts configured for critical errors
- [ ] Performance monitoring enabled

## Documentation

- [ ] Deployment guide reviewed
- [ ] Environment variables documented
- [ ] API endpoints documented
- [ ] Troubleshooting guide available
- [ ] Support contact information available

## Final Verification

- [ ] All tests pass
- [ ] No critical bugs known
- [ ] Performance acceptable
- [ ] User testing plan ready
- [ ] Feedback collection mechanism in place
- [ ] Backup strategy in place
- [ ] Rollback plan ready

---

## Quick Test Commands

```bash
# Test backend health
curl https://your-backend.com/health

# Test backend API
curl https://your-backend.com/games/search?q=test

# Test frontend
# Open https://your-frontend.com in browser
# Check browser console for errors
# Test login, search, chat features

# Test mobile app
# Install APK on device
# Test all features
# Check device logs for errors
```

---

## Rollback Plan

If issues occur:

1. **Backend**: Revert to previous deployment or disable new features
2. **Frontend**: Deploy previous build version
3. **Mobile**: Distribute previous APK version
4. **Database**: Restore from backup if needed

---

## Support Contacts

- **Backend Issues**: Check hosting service logs
- **Frontend Issues**: Check browser console and network tab
- **Mobile Issues**: Check Android Studio logs and device logs

