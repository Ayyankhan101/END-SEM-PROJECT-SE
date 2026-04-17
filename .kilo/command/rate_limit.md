# Rate Limiting Implementation

You need to implement API rate limiting for the DockWatch backend. Follow these steps:

## Step 1: Add slowapi to backend/requirements.txt
Add the following line to the file:
```
slowapi>=0.1.9
```

## Step 2: Update backend/app/main.py
Make these changes:
- Import SlowAPI and rate limiters:
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address
  from slowapi.errors import RateLimitExceeded
  ```
- Import the exceptions handler:
  ```python
  from app.api.exceptions import rate_limit_exceeded_handler
  ```
- Create a limiter instance:
  ```python
  limiter = Limiter(key_func=get_remote_address)
  ```
- Add state to app:
  ```python
  app.state.limiter = limiter
  ```
- Add the rate limit exception handler:
  ```python
  app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
  ```

## Step 3: Add rate limit decorators to endpoints in backend/app/api/endpoints.py
Make these changes:
- Import the limiter from main:
  ```python
  from app.main import limiter
  ```
- Add `@limiter.limit("10/minute")` decorator to the `/auth/token` endpoint (login function)
- Add `@limiter.limit("30/minute")` decorator to the `/containers/{container_id}/restart` endpoint

## Step 4: Create backend/app/api/exceptions.py
Create a new file with:
```python
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "retry_after": exc.detail,
        },
    )
```

## Step 5: Update config/config.yaml
Add the rate_limiting section at the end:
```yaml
rate_limiting:
  enabled: true
  default_limit: "100/minute"
  auth_limit: "10/minute"
```

Complete all these changes to implement rate limiting.
