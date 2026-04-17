import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import get_config


security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    config = get_config()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=config.security.jwt_expiration_hours)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.security.jwt_secret, algorithm=config.security.jwt_algorithm)


def verify_token(token: str) -> dict:
    config = get_config()
    try:
        payload = jwt.decode(token, config.security.jwt_secret, algorithms=[config.security.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return verify_token(credentials.credentials)


def create_initial_user():
    from app.db.database import get_db
    from app.db.models import User
    
    db = next(get_db())
    existing = db.query(User).first()
    if not existing:
        import secrets
        temp_password = secrets.token_urlsafe(16)
        user = User(
            username="admin", 
            hashed_password=get_password_hash(temp_password),
            must_change_password=True
        )
        db.add(user)
        db.commit()
        logger.warning("=" * 60)
        logger.warning("INITIAL USER CREATED - CHANGE PASSWORD IMMEDIATELY")
        logger.warning(f"Username: admin")
        logger.warning(f"Temporary Password: {temp_password}")
        logger.warning("=" * 60)