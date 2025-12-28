# Mobile App API Configuration

## Production API URL

The mobile app (Android/iOS) **always** uses the production server URL, regardless of build environment.

### Configuration

The API base URL is configured in `src/config/api.js`:

- **Mobile (Capacitor)**: Always uses `https://web-production-f74f5.up.railway.app`
- **Web**: Uses environment variable `REACT_APP_API_BASE_URL` or defaults to `http://localhost:8000`

### Why This Design?

1. **Consistency**: Mobile apps should always connect to production servers
2. **Security**: Prevents accidental connections to development/local servers
3. **Simplicity**: No need to manage different API URLs for mobile builds

### Updating the Production URL

If the production API URL changes, update it in `src/config/api.js`:

```javascript
const PRODUCTION_API_URL = "https://your-new-production-url.com";
```

Then rebuild and sync:
```bash
npm run build
npx cap sync android  # or ios
```

### Testing

To verify the mobile app is using the production URL:

1. Build and install the app on a device
2. Open browser DevTools (if using Chrome remote debugging) or check network logs
3. Verify API calls are going to `https://web-production-f74f5.up.railway.app`

### Development Note

For local development/testing of the mobile app with a local backend:
- You can temporarily modify `src/config/api.js` to use a local IP address
- Remember to revert before committing or deploying
