from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger, request_logger
from app.core.middleware import (
    AuditMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.exceptions import (
    HTTPAuthenticationError,
    HTTPAuthorizationError,
    HTTPConflictError,
    HTTPNotFoundError,
    HTTPRateLimitError,
    HTTPValidationError,
)

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events"""
    # Startup
    logger.info("Starting MicroCore SaaS Backend")
    logger.info(
        "Environment initialized",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        project_name=settings.PROJECT_NAME,
    )

    yield

    # Shutdown
    logger.info("Shutting down MicroCore SaaS Backend")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="Backend API for MicroCore SaaS platform",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

# Add custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditMiddleware)


# Global exception handlers
@app.exception_handler(HTTPAuthenticationError)
async def auth_exception_handler(request: Request, exc: HTTPAuthenticationError):
    """Handle authentication exceptions"""
    logger.warning(
        "Authentication failed",
        path=request.url.path,
        method=request.method,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": "authentication_failed"},
    )


@app.exception_handler(HTTPAuthorizationError)
async def authorization_exception_handler(request: Request, exc: HTTPAuthorizationError):
    """Handle authorization exceptions"""
    logger.warning(
        "Authorization failed",
        path=request.url.path,
        method=request.method,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": "access_denied"},
    )


@app.exception_handler(HTTPNotFoundError)
async def not_found_exception_handler(request: Request, exc: HTTPNotFoundError):
    """Handle not found exceptions"""
    logger.info(
        "Resource not found",
        path=request.url.path,
        method=request.method,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": "not_found"},
    )


@app.exception_handler(HTTPConflictError)
async def conflict_exception_handler(request: Request, exc: HTTPConflictError):
    """Handle conflict exceptions"""
    logger.warning(
        "Resource conflict",
        path=request.url.path,
        method=request.method,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": "conflict"},
    )


@app.exception_handler(HTTPValidationError)
async def validation_exception_handler(request: Request, exc: HTTPValidationError):
    """Handle validation exceptions"""
    logger.warning(
        "Validation failed",
        path=request.url.path,
        method=request.method,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": "validation_failed"},
    )


@app.exception_handler(HTTPRateLimitError)
async def rate_limit_exception_handler(request: Request, exc: HTTPRateLimitError):
    """Handle rate limit exceptions"""
    logger.warning(
        "Rate limit exceeded",
        path=request.url.path,
        method=request.method,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": "rate_limit_exceeded"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "internal_error",
        } if not settings.DEBUG else {
            "error": str(exc),
            "code": "internal_error",
        },
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "0.1.0",
    }


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )