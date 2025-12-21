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
ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS: List[str] = [
    origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()
]

# Database
DB_PATH = os.getenv("DB_PATH", "./gen/bgg_semantic.db")

# Security
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Development vs Production
IS_PRODUCTION = ENVIRONMENT.lower() == "production"

