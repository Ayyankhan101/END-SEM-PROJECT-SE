import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from pathlib import Path
from .config import get_config

from cryptography.fernet import Fernet
import os
import base64
import hashlib

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Encryption key for TOTP secrets
_encryption_key = os.environ.get("DOCKWATCH_ENCRYPTION_KEY")
if not _encryption_key:
    raise ValueError(
        "DOCKWATCH_ENCRYPTION_KEY is required for TOTP encryption. "
        "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

_fernet = Fernet(_encryption_key.encode())


def encrypt_secret(secret: str) -> str:
    """Encrypt a secret string."""
    if not secret:
        return None
    return _fernet.encrypt(secret.encode()).decode()


def decrypt_secret(encrypted_secret: str) -> str:
    """Decrypt an encrypted secret string."""
    if not encrypted_secret:
        return None
    try:
        return _fernet.decrypt(encrypted_secret.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt secret: {e}")
        return None


# Token blacklist for revocation (local cache for performance)
_token_blacklist_cache: set = set()


def _generate_rsa_keys():
    """Generate RSA key pair for JWT signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_pem.decode(), public_pem.decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash password with bcrypt (cost factor 14)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=14)).decode("utf-8")


def _get_key_dir() -> Path:
    """Get or create directory for JWT keys."""
    from pathlib import Path
    key_dir = Path("/var/run/dockwatch")
    key_dir.mkdir(parents=True, exist_ok=True)
    return key_dir


def _get_private_key() -> str:
    """Get or generate RSA private key."""
    from pathlib import Path
    key_dir = _get_key_dir()
    key_file = key_dir / "jwt_private.pem"
    pub_file = key_dir / "jwt_public.pem"
    if key_file.exists() and pub_file.exists():
        return key_file.read_text()
    private_pem, public_pem = _generate_rsa_keys()
    key_file.write_text(private_pem)
    pub_file.write_text(public_pem)
    try:
        key_file.chmod(0o600)
        pub_file.chmod(0o644)
    except PermissionError:
        pass
    logger.info("Generated RSA key pair for JWT")
    return private_pem


def _get_public_key() -> str:
    """Get RSA public key."""
    from pathlib import Path
    pub_file = Path("/var/run/dockwatch/jwt_public.pem")
    if pub_file.exists():
        return pub_file.read_text()
    # Fallback: generate keys
    private_pem, public_pem = _generate_rsa_keys()
    Path("/var/run/dockwatch").mkdir(parents=True, exist_ok=True)
    Path("/var/run/dockwatch/jwt_private.pem").write_text(private_pem)
    Path("/var/run/dockwatch/jwt_private.pem").chmod(0o600)
    pub_file.write_text(public_pem)
    pub_file.chmod(0o644)
    logger.info("Generated new RSA key pair for JWT")
    return public_pem


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, fresh: bool = False) -> str:
    """Create JWT access token with RSA signing."""
    config = get_config()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=60)  # 1 hour short expiry
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "fresh": fresh
    })
    private_key = _get_private_key()
    token = jwt.encode(
        to_encode, private_key, algorithm="RS256", headers={"kid": "dockwatch-rsa-2026"}
    )
    return token


def create_refresh_token(data: dict) -> str:
    """Create long-lived refresh token."""
    config = get_config()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
    private_key = _get_private_key()
    return jwt.encode(to_encode, private_key, algorithm="RS256")


def verify_token(token: str) -> dict:
    """Verify JWT token and check blacklist."""
    # Check cache first
    if token in _token_blacklist_cache:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check DB if not in cache
    from app.db.models import get_session, RevokedToken
    db = get_session()
    try:
        revoked = db.query(RevokedToken).filter(RevokedToken.token == token).first()
        if revoked:
            _token_blacklist_cache.add(token)  # Cache it
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    finally:
        db.close()

    public_key = _get_public_key()
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"require": ["exp", "iat", "type"]},
        )
        # Check per-user revocation timestamp
        username = payload.get("sub")
        iat = payload.get("iat")
        if username and iat:
            from app.db.models import get_session, User
            db = get_session()
            try:
                user = db.query(User).filter(User.username == username).first()
                if user and getattr(user, "tokens_revoked_at", None):
                    if datetime.utcfromtimestamp(iat) < user.tokens_revoked_at:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token has been revoked",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
            finally:
                db.close()
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def revoke_token(token: str):
    """Add token to persistent blacklist."""
    _token_blacklist_cache.add(token)
    
    from app.db.models import get_session, RevokedToken
    db = get_session()
    try:
        # Get expiry from token to allow auto-cleanup later
        public_key = _get_public_key()
        payload = jwt.decode(token, public_key, algorithms=["RS256"], options={"verify_exp": False})
        exp = payload.get("exp")
        if exp:
            expires_at = datetime.fromtimestamp(exp)
            revoked = RevokedToken(token=token, expires_at=expires_at)
            db.add(revoked)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to persist token revocation: {e}")
    finally:
        db.close()


def revoke_all_user_tokens(username: str):
    """Revoke all tokens for a specific user by storing a per-user revocation timestamp in the DB.
    Tokens issued before that timestamp will be rejected on next use.
    """
    from app.db.models import get_session, User
    db = get_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            user.tokens_revoked_at = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.error(f"Failed to revoke user tokens for {username}: {e}")
    finally:
        db.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current user from token."""
    token = credentials.credentials
    payload = verify_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """Optional user auth for public endpoints."""
    if not credentials:
        return None
    return await get_current_user(credentials)


def get_user_role(token_data: dict) -> Optional[str]:
    """Extract role from token."""
    return token_data.get("role")


def require_role(required_role: str):
    """Dependency that checks if user has required role."""
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = get_user_role(current_user)
        if user_role != required_role and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' or 'admin' required"
            )
        return current_user
    return role_checker


def create_initial_user():
    import secrets
    from app.db import get_db
    from app.db.models import User

    db = next(get_db())
    existing = db.query(User).first()
    if not existing:
        password = secrets.token_urlsafe(12)
        user = User(
            username="admin",
            hashed_password=get_password_hash(password),
            role="admin",
            must_change_password=True,
        )
        db.add(user)
        db.commit()
        logger.warning("=" * 60)
        logger.warning("INITIAL USER CREATED - PASSWORD CHANGE REQUIRED")
        logger.warning("Username: admin")
        logger.warning("Password: %s", password)
        logger.warning("=" * 60)
