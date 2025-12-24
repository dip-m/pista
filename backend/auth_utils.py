# backend/auth_utils.py
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import requests
from backend.config import (
    JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET,
    META_CLIENT_ID, META_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI, MICROSOFT_REDIRECT_URI, META_REDIRECT_URI
)

SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = JWT_ACCESS_TOKEN_EXPIRE_MINUTES


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash."""
    try:
        salt, stored_hash = password_hash.split(":", 1)
        computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return secrets.compare_digest(computed_hash, stored_hash)
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_google_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify Google OAuth token and return user info."""
    try:
        response = requests.get(
            f"https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "oauth_id": data.get("id"),
                "email": data.get("email"),
                "username": data.get("name") or data.get("email"),
            }
    except Exception:
        pass
    return None


def verify_microsoft_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify Microsoft OAuth token and return user info."""
    try:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "oauth_id": data.get("id"),
                "email": data.get("userPrincipalName") or data.get("mail"),
                "username": data.get("displayName") or data.get("userPrincipalName"),
            }
    except Exception:
        pass
    return None


def verify_meta_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify Meta (Facebook) OAuth token and return user info."""
    try:
        response = requests.get(
            f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}"
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "oauth_id": data.get("id"),
                "email": data.get("email"),
                "username": data.get("name") or data.get("email"),
            }
    except Exception:
        pass
    return None

