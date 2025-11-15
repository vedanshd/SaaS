import time
import uuid
from typing import Callable

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.logging import (
    audit_logger,
    request_logger,
    security_logger,
)
from app.core.security import verify_token


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if not settings.DEBUG:
            # HSTS in production
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            # CSP in production
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' https://api.stripe.com"
            )

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect metrics for HTTP requests"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log request
        request_logger.log_request(
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration=duration,
            user_id=getattr(request.state, "user_id", None),
            request_id=request_id,
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting for API endpoints"""

    def __init__(self, app):
        super().__init__(app)
        # In production, use Redis for distributed rate limiting
        self.requests = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        endpoint = f"{request.method}:{request.url.path}"

        # Check rate limits
        if not await self._check_rate_limit(client_ip, endpoint):
            security_logger.log_rate_limit_exceeded(
                identifier=client_ip,
                endpoint=endpoint,
                ip_address=client_ip,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded"},
            )

        response = await call_next(request)
        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host

    async def _check_rate_limit(self, client_ip: str, endpoint: str) -> bool:
        """Check if client has exceeded rate limit"""
        # Simple in-memory rate limiting
        # In production, use Redis with sliding window algorithm

        current_time = time.time()
        window = 60  # 1 minute window

        # Different rate limits for different endpoints
        if endpoint.startswith("POST:/api/v1/auth"):
            limit = settings.RATE_LIMIT_AUTH_PER_MINUTE
        else:
            limit = settings.RATE_LIMIT_PER_MINUTE

        key = f"{client_ip}:{endpoint}"

        if key not in self.requests:
            self.requests[key] = []

        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if current_time - req_time < window
        ]

        # Check limit
        if len(self.requests[key]) >= limit:
            return False

        # Add current request
        self.requests[key].append(current_time)
        return True


class AuditMiddleware(BaseHTTPMiddleware):
    """Audit logging for user actions"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip certain endpoints from audit logging
        skip_patterns = ["/health", "/metrics", "/openapi.json", "/docs", "/redoc"]

        should_skip = any(
            request.url.path.startswith(pattern) for pattern in skip_patterns
        )

        response = await call_next(request)

        if not should_skip:
            await self._log_request(request, response)

        return response

    async def _log_request(self, request: Request, response: Response):
        """Log request for audit"""
        user_id = getattr(request.state, "user_id", None)
        method = request.method
        path = request.url.path

        # Determine action and resource type
        action = method.lower()
        resource_type = self._get_resource_type(path)

        # Log successful requests (non-error responses)
        if 200 <= response.status_code < 400:
            audit_logger.log_action(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=self._get_resource_id(request),
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent"),
            )
        else:
            # Log errors separately
            audit_logger.log_action(
                user_id=user_id,
                action=f"{action}_error",
                resource_type=resource_type,
                metadata={
                    "status_code": response.status_code,
                    "path": path,
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent"),
            )

    def _get_resource_type(self, path: str) -> str:
        """Extract resource type from path"""
        segments = path.strip("/").split("/")
        if len(segments) >= 2:
            return segments[-2] if segments[-1].isdigit() else segments[-1]
        return segments[0] if segments else "unknown"

    def _get_resource_id(self, request: Request) -> str:
        """Extract resource ID from request"""
        path_segments = request.url.path.strip("/").split("/")
        for segment in path_segments:
            if segment.isdigit():
                return segment
        return None

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Handle JWT authentication for protected endpoints"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for certain endpoints
        skip_patterns = [
            "/health",
            "/metrics",
            "/api/v1/auth/login",
            "/api/v1/auth/signup",
            "/api/v1/auth/refresh",
            "/api/v1/stripe/webhook",
            "/openapi.json",
            "/docs",
            "/redoc",
        ]

        should_skip = any(
            request.url.path.startswith(pattern) for pattern in skip_patterns
        )

        if should_skip:
            return await call_next(request)

        # Extract and verify token
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            request.state.user_id = None
            request.state.user_role = None
            return await call_next(request)

        token = authorization.split(" ")[1]
        user_id = verify_token(token, "access")

        if user_id:
            request.state.user_id = user_id
            # In a real implementation, fetch user role from database
            request.state.user_role = "user"  # Placeholder
        else:
            request.state.user_id = None
            request.state.user_role = None

        return await call_next(request)