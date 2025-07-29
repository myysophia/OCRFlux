"""
Middleware configuration and setup
"""
import logging
from typing import Optional, List
from fastapi import FastAPI

from ..core.config import settings
from .cors import setup_cors
from .logging import RequestLoggingMiddleware
from .error_handler import ErrorHandlerMiddleware
from .file_cleanup import add_file_cleanup_middleware
from .request_size import add_request_size_limit_middleware
from .rate_limit import add_rate_limit_middleware
from .request_id import add_request_id_middleware
from .request_validation import add_request_validation_middleware

logger = logging.getLogger(__name__)


def setup_all_middleware(
    app: FastAPI,
    enable_rate_limiting: bool = False,
    rate_limit_per_minute: int = 60,
    rate_limit_per_hour: int = 1000,
    max_request_size: Optional[int] = None,
    rate_limit_exclude_paths: Optional[List[str]] = None,
    size_limit_exclude_paths: Optional[List[str]] = None,
    enable_request_id: bool = True,
    request_id_header: str = "X-Request-ID",
    enable_request_validation: bool = True,
    validation_exclude_paths: Optional[List[str]] = None
) -> None:
    """
    Set up all middleware for the FastAPI application.
    
    Middleware is added in the correct order (first added is outermost):
    1. Request ID Generation (outermost - for request tracking)
    2. Error Handler (catches all errors with request ID)
    3. Request Validation (validates headers, content-type, etc.)
    4. Rate Limiting (optional - before processing)
    5. Request Size Limiting (before file processing)
    6. Request Logging (logs all requests with ID)
    7. File Cleanup (background cleanup)
    8. CORS (innermost - handles cross-origin requests)
    
    Args:
        app: FastAPI application instance
        enable_rate_limiting: Whether to enable rate limiting
        rate_limit_per_minute: Requests per minute limit
        rate_limit_per_hour: Requests per hour limit
        max_request_size: Maximum request size in bytes
        rate_limit_exclude_paths: Paths to exclude from rate limiting
        size_limit_exclude_paths: Paths to exclude from size limiting
        enable_request_id: Whether to enable request ID middleware
        request_id_header: Header name for request ID
        enable_request_validation: Whether to enable request validation middleware
        validation_exclude_paths: Paths to exclude from request validation
    """
    logger.info("Setting up middleware stack...")
    
    # 1. Request ID Middleware (outermost - for request tracking)
    if enable_request_id:
        add_request_id_middleware(
            app,
            header_name=request_id_header,
            generate_if_missing=True,
            include_in_response=True
        )
        logger.info("✅ Request ID middleware added")
    else:
        logger.info("⏭️  Request ID middleware skipped (disabled)")
    
    # 2. Error Handler Middleware 
    # This catches all exceptions and uses request ID for correlation
    app.add_middleware(
        ErrorHandlerMiddleware, 
        include_debug_info=settings.debug
    )
    logger.info("✅ Error handler middleware added")
    
    # 3. Request Validation Middleware
    if enable_request_validation:
        add_request_validation_middleware(
            app,
            max_headers=settings.max_request_headers,
            max_header_size=settings.max_header_size,
            require_user_agent=False,  # Don't require User-Agent for API
            exclude_paths=validation_exclude_paths
        )
        logger.info("✅ Request validation middleware added")
    else:
        logger.info("⏭️  Request validation middleware skipped (disabled)")
    
    # 4. Rate Limiting Middleware (optional)
    if enable_rate_limiting:
        add_rate_limit_middleware(
            app,
            requests_per_minute=rate_limit_per_minute,
            requests_per_hour=rate_limit_per_hour,
            exclude_paths=rate_limit_exclude_paths,
            strategy=settings.rate_limit_strategy
        )
        logger.info("✅ Rate limiting middleware added")
    else:
        logger.info("⏭️  Rate limiting middleware skipped (disabled)")
    
    # 5. Request Size Limiting Middleware
    add_request_size_limit_middleware(
        app,
        max_size=max_request_size,
        exclude_paths=size_limit_exclude_paths
    )
    logger.info("✅ Request size limiting middleware added")
    
    # 6. Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("✅ Request logging middleware added")
    
    # 7. File Cleanup Middleware (background task)
    add_file_cleanup_middleware(
        app, 
        cleanup_interval_hours=1, 
        max_file_age_hours=24
    )
    logger.info("✅ File cleanup middleware added")
    
    # 8. CORS Middleware (innermost)
    setup_cors(app)
    logger.info("✅ CORS middleware added")
    
    logger.info("🎉 All middleware configured successfully")


def get_middleware_info() -> dict:
    """
    Get information about configured middleware.
    
    Returns:
        Dictionary with middleware configuration details
    """
    return {
        "middleware_stack": [
            {
                "name": "RequestIDMiddleware",
                "description": "Request ID generation and tracking for correlation",
                "position": 1,
                "always_enabled": True,
                "configurable": True
            },
            {
                "name": "ErrorHandlerMiddleware",
                "description": "Global error handling and standardized error responses",
                "position": 2,
                "always_enabled": True
            },
            {
                "name": "RequestValidationMiddleware",
                "description": "Request validation including headers, content-type, and security checks",
                "position": 3,
                "always_enabled": True,
                "configurable": True,
                "max_headers": settings.max_request_headers,
                "max_header_size": settings.max_header_size
            },
            {
                "name": "RateLimitMiddleware",
                "description": "Request rate limiting per IP address",
                "position": 4,
                "always_enabled": False,
                "configurable": True
            },
            {
                "name": "RequestSizeLimitMiddleware",
                "description": "Request size validation and limiting",
                "position": 5,
                "always_enabled": True,
                "max_size_mb": settings.max_file_size // (1024*1024)
            },
            {
                "name": "RequestLoggingMiddleware",
                "description": "Request and response logging with timing",
                "position": 6,
                "always_enabled": True
            },
            {
                "name": "FileCleanupMiddleware",
                "description": "Background cleanup of temporary files",
                "position": 7,
                "always_enabled": True
            },
            {
                "name": "CORSMiddleware",
                "description": "Cross-Origin Resource Sharing support",
                "position": 8,
                "always_enabled": True,
                "allowed_origins": settings.cors_origins
            }
        ],
        "configuration": {
            "debug_mode": settings.debug,
            "max_file_size_bytes": settings.max_file_size,
            "max_file_size_mb": settings.max_file_size // (1024*1024),
            "cors_origins": settings.cors_origins,
            "cors_methods": settings.cors_methods,
            "cors_headers": settings.cors_headers
        },
        "features": {
            "request_id_tracking": True,
            "detailed_error_responses": True,
            "request_timing": True,
            "client_ip_detection": True,
            "proxy_support": True,
            "automatic_file_cleanup": True,
            "configurable_rate_limiting": True,
            "request_size_validation": True
        }
    }


# Default middleware configuration for different environments
DEVELOPMENT_MIDDLEWARE_CONFIG = {
    "enable_rate_limiting": False,  # Disabled for development
    "rate_limit_per_minute": 120,
    "rate_limit_per_hour": 2000,
    "rate_limit_exclude_paths": [
        "/docs", "/redoc", "/openapi.json", 
        "/api/v1/health", "/api-info"
    ],
    "size_limit_exclude_paths": [
        "/docs", "/redoc", "/openapi.json",
        "/api/v1/health", "/api-info", "/schema-stats"
    ],
    "enable_request_id": True,
    "request_id_header": "X-Request-ID",
    "enable_request_validation": True,
    "validation_exclude_paths": [
        "/docs", "/redoc", "/openapi.json",
        "/api/v1/health", "/api-info", "/schema-stats"
    ]
}

PRODUCTION_MIDDLEWARE_CONFIG = {
    "enable_rate_limiting": True,   # Enabled for production
    "rate_limit_per_minute": 60,
    "rate_limit_per_hour": 1000,
    "rate_limit_exclude_paths": [
        "/api/v1/health/simple"  # Only allow simple health check
    ],
    "size_limit_exclude_paths": [
        "/api/v1/health"
    ],
    "enable_request_id": True,
    "request_id_header": "X-Request-ID",
    "enable_request_validation": True,
    "validation_exclude_paths": [
        "/api/v1/health"  # Only exclude basic health check
    ]
}

TESTING_MIDDLEWARE_CONFIG = {
    "enable_rate_limiting": False,  # Disabled for testing
    "rate_limit_per_minute": 1000,  # High limits for testing
    "rate_limit_per_hour": 10000,
    "rate_limit_exclude_paths": [],
    "size_limit_exclude_paths": [],
    "enable_request_id": True,
    "request_id_header": "X-Request-ID",
    "enable_request_validation": False,  # Disabled for testing to avoid interference
    "validation_exclude_paths": []
}