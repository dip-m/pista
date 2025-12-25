"""
Configuration management for Pista backend.
Loads environment variables and provides configuration settings.
"""
import os
from typing import List

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Server Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# CORS Configuration
ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://pistatabletop.netlify.app")
ALLOWED_ORIGINS: List[str] = [
    origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()
]

# Database
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # 'sqlite' or 'postgres'
DATABASE_URL = os.getenv("DATABASE_URL", "")  # PostgreSQL connection string
DB_PATH = os.getenv("DB_PATH", "./gen/bgg_semantic.db")

# Security
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
META_CLIENT_ID = os.getenv("META_CLIENT_ID", "")
META_CLIENT_SECRET = os.getenv("META_CLIENT_SECRET", "")

# OAuth Redirect URLs (frontend URLs)
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:3000")
GOOGLE_REDIRECT_URI = f"{OAUTH_REDIRECT_BASE}/auth/callback/google"
MICROSOFT_REDIRECT_URI = f"{OAUTH_REDIRECT_BASE}/auth/callback/microsoft"
META_REDIRECT_URI = f"{OAUTH_REDIRECT_BASE}/auth/callback/meta"

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

# BEARER_TOKEN for external API calls (moved to env)
BEARER_TOKEN = os.getenv("BEARER_TOKEN", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Development vs Production
IS_PRODUCTION = ENVIRONMENT.lower() == "production"

