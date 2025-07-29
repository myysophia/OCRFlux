"""
CORS middleware configuration with enhanced security
"""
import logging
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import settings

logger = logging.getLogger(__name__)


def setup_cors(
    app: FastAPI,
    allow_origins: Optional[List[str]] = None,
    allow_methods: Optional[List[str]] = None,
    allow_headers: Optional[List[str]] = None,
    allow_credentials: bool = True,
    expose_headers: Optional[List[str]] = None,
    max_age: int = 600
) -> None:
    """
    Setup CORS middleware for FastAPI app with enhanced security.
    
    Args:
        app: FastAPI application instance
        allow_origins: List of allowed origins (defaults to settings.cors_origins)
        allow_methods: List of allowed HTTP methods (defaults to settings.cors_methods)
        allow_headers: List of allowed headers (defaults to settings.cors_headers)
        allow_credentials: Whether to allow credentials in CORS requests
        expose_headers: List of headers to expose to the client
        max_age: Maximum age for preflight cache in seconds
    """
    # Use settings defaults if not provided
    origins = allow_origins or settings.cors_origins
    methods = allow_methods or settings.cors_methods
    headers = allow_headers or settings.cors_headers
    
    # Enhanced security: Don't allow wildcard origins with credentials
    if allow_credentials and "*" in origins:
        logger.warning(
            "CORS configured with wildcard origins and credentials enabled. "
            "This is a security risk in production. Consider specifying explicit origins."
        )
        
        # In production, we should be more restrictive
        if not settings.debug:
            logger.error(
                "Wildcard CORS origins not allowed in production with credentials. "
                "Please configure specific origins in CORS_ORIGINS environment variable."
            )
            # Use more restrictive defaults for production
            origins = [
                "http://localhost:3000",
                "http://localhost:8080", 
                "https://localhost:3000",
                "https://localhost:8080"
            ]
    
    # Default exposed headers for API functionality
    default_expose_headers = [
        "X-Request-ID",
        "X-Process-Time", 
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset"
    ]
    
    if expose_headers:
        expose_headers.extend(default_expose_headers)
    else:
        expose_headers = default_expose_headers
    
    # Enhanced default headers for API functionality
    if "*" in headers:
        # If wildcard is used, specify common headers explicitly for better security
        api_headers = [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID",
            "X-API-Key",
            "Cache-Control"
        ]
        
        if settings.debug:
            # Allow all headers in development
            headers = ["*"]
        else:
            # Use specific headers in production
            headers = api_headers
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=methods,
        allow_headers=headers,
        expose_headers=expose_headers,
        max_age=max_age
    )
    
    logger.info(
        f"CORS middleware configured: "
        f"origins={len(origins)} {'(wildcard)' if '*' in origins else '(specific)'}, "
        f"methods={len(methods)} {'(wildcard)' if '*' in methods else '(specific)'}, "
        f"headers={len(headers)} {'(wildcard)' if '*' in headers else '(specific)'}, "
        f"credentials={allow_credentials}"
    )
    
    # Log security warnings
    if "*" in origins and not settings.debug:
        logger.warning("Wildcard CORS origins detected in production environment")
    
    if allow_credentials and not any(origin.startswith("https://") for origin in origins if origin != "*"):
        logger.warning("CORS credentials enabled but no HTTPS origins configured")


def get_cors_info() -> dict:
    """
    Get information about CORS configuration.
    
    Returns:
        Dictionary with CORS configuration details
    """
    return {
        "cors_configuration": {
            "allowed_origins": settings.cors_origins,
            "allowed_methods": settings.cors_methods, 
            "allowed_headers": settings.cors_headers,
            "credentials_enabled": True,
            "security_level": "development" if settings.debug else "production"
        },
        "security_notes": {
            "wildcard_origins": "*" in settings.cors_origins,
            "wildcard_methods": "*" in settings.cors_methods,
            "wildcard_headers": "*" in settings.cors_headers,
            "https_origins": any(
                origin.startswith("https://") 
                for origin in settings.cors_origins 
                if origin != "*"
            )
        },
        "recommendations": {
            "production": [
                "Use specific origins instead of wildcard (*)",
                "Ensure HTTPS origins for credential requests",
                "Limit allowed methods to required ones only",
                "Specify explicit headers instead of wildcard"
            ],
            "development": [
                "Current configuration is suitable for development",
                "Consider testing with production-like CORS settings"
            ]
        }
    }