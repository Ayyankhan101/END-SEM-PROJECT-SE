from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}",
            "retry_after": exc.detail,
        },
    )


def get_rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return f"user:{auth_header[7:20]}"
    return get_remote_address(request)
