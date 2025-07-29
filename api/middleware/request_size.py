"""
Request size limiting middleware
"""
import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..core.config import settings
from ..models.error import ErrorResponse, ErrorDetail, ErrorType

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit the size of incoming requests.
    
    This middleware checks the Content-Length header and rejects requests
    that exceed the configured maximum size before they are processed.
    """
    
    def __init__(
        self, 
        app, 
        max_size: Optional[int] = None,
        exclude_paths: Optional[list] = None
    ):
        """
        Initialize the request size limit middleware.
        
        Args:
            app: FastAPI application instance
            max_size: Maximum request size in bytes (defaults to settings.max_file_size)
            exclude_paths: List of paths to exclude from size checking
        """
        super().__init__(app)
        self.max_size = max_size or settings.max_file_size
        self.exclude_paths = exclude_paths or []
        
        logger.info(f"Request size limit middleware initialized with max_size={self.max_size} bytes")
    
    async def dispatch(self, request: Request, call_next):
        """
        Check request size and process or reject the request.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain
            
        Returns:
            HTTP response
        """
        # Skip size checking for excluded paths
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # Skip size checking for GET requests and other methods without body
        if request.method in ["GET", "HEAD", "OPTIONS", "DELETE"]:
            return await call_next(request)
        
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        
        if content_length is not None:
            try:
                content_length = int(content_length)
                
                if content_length > self.max_size:
                    logger.warning(
                        f"Request size limit exceeded: {content_length} bytes > {self.max_size} bytes "
                        f"for {request.method} {request.url.path} "
                        f"from {request.client.host if request.client else 'unknown'}"
                    )
                    
                    return await self._create_size_limit_error_response(
                        request, content_length, self.max_size
                    )
                    
            except ValueError:
                logger.warning(
                    f"Invalid Content-Length header: {content_length} "
                    f"for {request.method} {request.url.path}"
                )
                
                # Allow request to proceed if Content-Length is invalid
                # The actual size will be checked during processing
        
        # For requests without Content-Length header (e.g., chunked transfer),
        # we'll let them proceed and rely on FastAPI's built-in limits
        
        return await call_next(request)
    
    def _should_exclude_path(self, path: str) -> bool:
        """
        Check if a path should be excluded from size checking.
        
        Args:
            path: Request path
            
        Returns:
            True if path should be excluded
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    async def _create_size_limit_error_response(
        self, 
        request: Request, 
        actual_size: int, 
        max_size: int
    ) -> Response:
        """
        Create an error response for size limit exceeded.
        
        Args:
            request: HTTP request
            actual_size: Actual request size in bytes
            max_size: Maximum allowed size in bytes
            
        Returns:
            JSON error response
        """
        # Get request ID if available
        request_id = getattr(request.state, 'request_id', None)
        
        # Create detailed error response
        error_response = ErrorResponse(
            error_type=ErrorType.FILE_ERROR,
            message=f"Request size exceeds maximum limit of {max_size // (1024*1024)}MB",
            details=[
                ErrorDetail(
                    field="content-length",
                    message=f"Request size is {actual_size} bytes, maximum allowed is {max_size} bytes",
                    code="REQUEST_TOO_LARGE",
                    context={
                        "actual_size_bytes": actual_size,
                        "actual_size_mb": round(actual_size / (1024*1024), 2),
                        "max_size_bytes": max_size,
                        "max_size_mb": round(max_size / (1024*1024), 2),
                        "suggestion": "Reduce file size or use chunked upload for large files"
                    }
                )
            ],
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=error_response.model_dump(mode='json'),
            headers={
                "Connection": "close",  # Close connection for large requests
                "Retry-After": "3600"   # Suggest retry after 1 hour
            }
        )


def add_request_size_limit_middleware(
    app, 
    max_size: Optional[int] = None,
    exclude_paths: Optional[list] = None
) -> None:
    """
    Add request size limit middleware to FastAPI app.
    
    Args:
        app: FastAPI application instance
        max_size: Maximum request size in bytes
        exclude_paths: List of paths to exclude from size checking
    """
    exclude_paths = exclude_paths or [
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/api/v1/health",
        "/api-info",
        "/schema-stats"
    ]
    
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size=max_size,
        exclude_paths=exclude_paths
    )
    
    logger.info("Request size limit middleware added to application")