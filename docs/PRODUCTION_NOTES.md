# Production Deployment Notes

Important considerations and best practices for production deployment.

## Critical Configuration Changes

### 1. CORS Configuration
**Current**: Only allows `http://localhost:3000`  
**Production**: Must include your production frontend URL(s)

Update in `.env`:
```env
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://www.your-frontend-domain.com
```

### 2. JWT Secret Key
**Current**: Default or development key  
**Production**: Must use a strong, randomly generated secret

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Database Path
Ensure the database file is accessible and backed up regularly.

### 4. FAISS Index
The index file (`game_vectors.index`) must be accessible at the configured path.

## Performance Considerations

### Backend
- Use multiple workers for production: `uvicorn main:app --workers 4`
- Consider using a reverse proxy (Nginx) for better performance
- Enable caching for static responses
- Monitor database query performance
- Consider connection pooling for database

### Frontend
- Production build is optimized automatically (`npm run build`)
- Enable CDN for static assets
- Use compression (gzip/brotli)
- Enable browser caching for static assets

### Mobile
- APK size optimization (ProGuard/R8)
- Lazy loading for images
- Network request optimization

## Security Best Practices

1. **Never commit** `.env` files
2. **Use HTTPS** for all production deployments
3. **Rotate secrets** regularly
4. **Validate inputs** on backend (already implemented)
5. **Use parameterized queries** (already implemented)
6. **Implement rate limiting** if needed
7. **Monitor logs** for suspicious activity
8. **Keep dependencies updated**
9. **Use environment-specific configs**
10. **Backup database** regularly

## Scaling Considerations

### Current Setup (Single Server)
- SQLite database (good for < 100 concurrent users)
- In-memory FAISS index
- Single process

### When to Scale
- **Database**: Switch to PostgreSQL when SQLite becomes a bottleneck
- **Backend**: Add load balancer and multiple instances
- **Caching**: Add Redis for session/cache management
- **CDN**: Use CloudFront/Cloudflare for static assets

## Monitoring

### Essential Metrics
- API response times
- Error rates
- Database query performance
- Memory usage
- CPU usage
- Request volume

### Recommended Tools
- **Error Tracking**: Sentry (free tier available)
- **Analytics**: Google Analytics, Mixpanel
- **Uptime**: UptimeRobot (free), Pingdom
- **Logs**: Hosting service logs, or use Loggly/Papertrail

## Backup Strategy

### Database
- Backup `gen/bgg_semantic.db` daily
- Store backups in separate location
- Test restore process regularly

### FAISS Index
- Backup `gen/game_vectors.index` when updated
- Version control for index files

### Application Code
- Use Git for version control
- Tag releases for easy rollback

## Cost Estimation

### Free Tier Options
- **Railway**: $5/month free credit
- **Render**: Free tier available
- **Vercel**: Free tier for frontend
- **Netlify**: Free tier available

### Paid Options
- **AWS**: Pay-as-you-go, ~$10-50/month for small scale
- **DigitalOcean**: $6-12/month for basic droplet
- **Google Cloud Run**: Pay-per-use, very affordable

## Troubleshooting Common Issues

### Backend Won't Start
- Check environment variables are set
- Verify database file exists and is readable
- Check FAISS index file exists
- Review logs for specific errors

### Frontend Can't Connect to Backend
- Verify `REACT_APP_API_BASE_URL` is correct
- Check CORS configuration on backend
- Verify backend is running and accessible
- Check network/firewall settings

### Mobile App Can't Connect
- Update `capacitor.config.json` with production URL
- Remove or set `server.url` to empty string for production
- Check Android network permissions
- Verify backend CORS allows mobile app origin

### Database Errors
- Verify database file path is correct
- Check file permissions
- Ensure database schema is up-to-date
- Check disk space

## Maintenance Schedule

### Daily
- Monitor error logs
- Check uptime status
- Review user feedback

### Weekly
- Review performance metrics
- Check for dependency updates
- Backup database

### Monthly
- Update dependencies
- Review and rotate secrets
- Performance optimization review
- Security audit

## User Testing Considerations

### Beta Testing
- Use internal testing track (Play Store) or TestFlight (iOS)
- Collect feedback systematically
- Monitor crash reports
- Track feature usage

### Feedback Collection
- In-app feedback mechanism (already implemented)
- External survey tools
- User interviews
- Analytics data

## Launch Checklist

- [ ] All features tested and working
- [ ] Performance acceptable
- [ ] Security review completed
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Support channels ready
- [ ] Documentation complete
- [ ] User testing plan ready
- [ ] Marketing materials ready (if applicable)
- [ ] Legal/privacy policy in place (if applicable)
