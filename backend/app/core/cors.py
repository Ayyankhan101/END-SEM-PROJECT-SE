"""
CORS Configuration Module

This module provides CORS configuration for the FastAPI application.

Configuration:
-------------
CORS can be configured via:
1. config.yaml - Add a `cors` section with `allowed_origins` and `allow_credentials`
2. Environment variable `CORS_ORIGINS` - Comma-separated list of allowed origins

Example config.yaml:
```yaml
cors:
  allowed_origins:
    - "http://localhost:3000"
    - "http://localhost:5173"
  allow_credentials: true
```

Environment variable:
```bash
export CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
```

Security Warning:
----------------
The default fallback origins (localhost:3000, localhost:5173) are for DEVELOPMENT ONLY.
In production, always explicitly configure allowed origins in config.yaml or via
environment variable to prevent unauthorized cross-origin requests.
"""

import os
import logging
from typing import List

from app.core.config import get_config

logger = logging.getLogger(__name__)

DEFAULT_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]


def get_cors_origins() -> List[str]:
    """
    Get CORS allowed origins from config or environment.

    Priority:
    1. CORS_ORIGINS environment variable (comma-separated)
    2. config.yaml cors.allowed_origins
    3. Default dev origins (with warning)
    """
    env_origins = os.environ.get("CORS_ORIGINS")
    if env_origins:
        origins = [
            origin.strip() for origin in env_origins.split(",") if origin.strip()
        ]
        logger.info(f"Using CORS origins from environment variable: {origins}")
        return origins

    try:
        config = get_config()
        if (
            hasattr(config, "cors")
            and config.cors
            and hasattr(config.cors, "allowed_origins")
        ):
            if config.cors.allowed_origins:
                logger.info(
                    f"Using CORS origins from config: {config.cors.allowed_origins}"
                )
                return config.cors.allowed_origins
    except Exception:
        pass

    logger.warning(
        "Using default development CORS origins. "
        "This is NOT secure for production. "
        "Configure cors.allowed_origins in config.yaml or set CORS_ORIGINS environment variable."
    )
    return DEFAULT_DEV_ORIGINS


def get_cors_allow_credentials() -> bool:
    """Get CORS allow_credentials setting from config or environment."""
    try:
        config = get_config()
        if (
            hasattr(config, "cors")
            and config.cors
            and hasattr(config.cors, "allow_credentials")
        ):
            return config.cors.allow_credentials
    except Exception:
        pass

    env_value = os.environ.get("CORS_ALLOW_CREDENTIALS", "true").lower()
    return env_value in ("true", "1", "yes")


def get_cors_config() -> dict:
    """Get complete CORS configuration dictionary."""
    return {
        "allow_origins": get_cors_origins(),
        "allow_credentials": get_cors_allow_credentials(),
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-Requested-With"],
        "expose_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining"],
        "max_age": 600,
    }
