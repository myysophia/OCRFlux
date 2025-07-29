"""
Request validation middleware for enhanced security and validation
"""
import logging
import re
from typing import Optional, List, Dict, Set
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..core.config import settings
from ..models.error import ErrorResponse, ErrorDetail, ErrorType

logger = logging.getLogger(__name__)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request validation including:
    - Content-Type validation
    - Header validation and limits
    - User-Agent validation
    - Request method validation
    - Path validation and sanitization
    """
    
    def __init__(
        self,
        app,
        allowed_content_types: Optional[List[str]] = None,
        max_headers: Optional[int] = None,
        max_header_size: Optional[int] = None,
        require_user_agent: bool = False,
        allowed_methods: Optional[Set[str]] = None,
        blocked_user_agents: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None
    ):
        """
        Initialize request validation middleware.
        
        Args:
            app: FastAPI application instance
            allowed_content_types: List of allowed Content-Type values
            max_headers: Maximum number of headers allowed
            max_header_size: Maximum size of individual headers
            require_user_agent: Whether User-Agent header is required
            allowed_methods: Set of allowed HTTP methods
            blocked_user_agents: List of blocked User-Agent patterns
            exclude_paths: List of paths to exclude from validation
        """
        super().__init__(app)
        
        # Content type validation
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "multipart/form-data",
            "application/x-www-form-urlencoded",
            "text/plain",
            "application/octet-stream"
        ]
        
        # Header validation
        self.max_headers = max_headers or settings.max_request_headers
        self.max_header_size = max_header_size or settings.max_header_size
        
        # User-Agent validation
        self.require_user_agent = require_user_agent
        self.blocked_user_agents = blocked_user_agents or [
            r".*bot.*",
            r".*crawler.*",
            r".*spider.*",
            r".*scraper.*"
        ]
        self.blocked_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.blocked_user_agents]
        
        # Method validation
        self.allowed_methods = allowed_methods or {
            "GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"
        }
        
        # Path exclusions
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/api/v1/health",
            "/api-info"
        ]
        
        logger.info(
            f"Request validation middleware initialized: "
            f"content_types={len(self.allowed_content_types)}, "
            f"max_headers={self.max_headers}, "
            f"require_user_agent={self.require_user_agent}"
        )
    
    async def dispatch(self, request: Request, call_next):
        """
        Validate request and process or reject it.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain
            
        Returns:
            HTTP response
        """
        # Skip validation for excluded paths
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        try:
            # Validate HTTP method
            self._validate_method(request)
            
            # Validate headers
            self._validate_headers(request)
            
            # Validate User-Agent
            self._validate_user_agent(request)
            
            # Validate Content-Type for requests with body
            if request.method in ["POST", "PUT", "PATCH"]:
                self._validate_content_type(request)
            
            # Validate request path
            self._validate_path(request)
            
        except HTTPException as e:
            # Convert HTTPException to our error format
            return await self._create_validation_error_response(request, str(e.detail), e.status_code)
        except Exception as e:
            logger.error(f"Unexpected error in request validation: {str(e)}")
            return await self._create_validation_error_response(
                request, "Request validation failed", 400
            )
        
        # Process request
        return await call_next(request)
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if a path should be excluded from validation."""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    def _validate_method(self, request: Request) -> None:
        """Validate HTTP method."""
        if request.method not in self.allowed_methods:
            logger.warning(f"Blocked request with invalid method: {request.method}")
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail=f"Method {request.method} not allowed. Allowed methods: {', '.join(self.allowed_methods)}"
            )
    
    def _validate_headers(self, request: Request) -> None:
        """Validate request headers."""
        headers = dict(request.headers)
        
        # Check number of headers
        if len(headers) > self.max_headers:
            logger.warning(f"Too many headers: {len(headers)} > {self.max_headers}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many headers. Maximum {self.max_headers} headers allowed, got {len(headers)}"
            )
        
        # Check individual header sizes
        for name, value in headers.items():
            header_size = len(name) + len(value)
            if header_size > self.max_header_size:
                logger.warning(f"Header too large: {name} ({header_size} bytes)")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Header '{name}' too large. Maximum {self.max_header_size} bytes allowed"
                )
        
        # Validate specific headers
        self._validate_specific_headers(headers)
    
    def _validate_specific_headers(self, headers: Dict[str, str]) -> None:
        """Validate specific header values."""
        # Validate Content-Length if present
        content_length = headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length < 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Content-Length cannot be negative"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Content-Length header value"
                )
        
        # Validate Host header format
        host = headers.get("host")
        if host and not self._is_valid_host(host):
            logger.warning(f"Invalid Host header: {host}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Host header format"
            )
    
    def _is_valid_host(self, host: str) -> bool:
        """Validate Host header format."""
        # Basic validation for host header
        if not host or len(host) > 253:
            return False
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9.-]+(?::[0-9]+)?$', host):
            return False
        
        return True
    
    def _validate_user_agent(self, request: Request) -> None:
        """Validate User-Agent header."""
        user_agent = request.headers.get("user-agent", "")
        
        # Check if User-Agent is required
        if self.require_user_agent and not user_agent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User-Agent header is required"
            )
        
        # Check against blocked patterns
        if user_agent:
            for pattern in self.blocked_patterns:
                if pattern.search(user_agent):
                    logger.warning(f"Blocked request with User-Agent: {user_agent}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: automated requests not allowed"
                    )
    
    def _validate_content_type(self, request: Request) -> None:
        """Validate Content-Type header for requests with body."""
        content_type = request.headers.get("content-type", "")
        
        if not content_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content-Type header is required for requests with body"
            )
        
        # Extract main content type (ignore parameters like charset)
        main_content_type = content_type.split(";")[0].strip().lower()
        
        # Check if content type is allowed
        allowed = False
        for allowed_type in self.allowed_content_types:
            if main_content_type == allowed_type.lower():
                allowed = True
                break
            # Also check for wildcard matches (e.g., "image/*")
            if allowed_type.endswith("/*"):
                type_prefix = allowed_type[:-2]
                if main_content_type.startswith(type_prefix):
                    allowed = True
                    break
        
        if not allowed:
            logger.warning(f"Unsupported Content-Type: {content_type}")
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported Content-Type: {main_content_type}. "
                       f"Supported types: {', '.join(self.allowed_content_types)}"
            )
    
    def _validate_path(self, request: Request) -> None:
        """Validate request path for security issues."""
        path = request.url.path
        
        # Check for path traversal attempts
        if ".." in path or "~" in path:
            logger.warning(f"Path traversal attempt detected: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path: path traversal not allowed"
            )
        
        # Check for null bytes
        if "\x00" in path:
            logger.warning(f"Null byte in path: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path: null bytes not allowed"
            )
        
        # Check path length
        if len(path) > 2048:
            logger.warning(f"Path too long: {len(path)} characters")
            raise HTTPException(
                status_code=status.HTTP_414_URI_TOO_LONG,
                detail="Request path too long"
            )
    
    async def _create_validation_error_response(
        self, 
        request: Request, 
        message: str, 
        status_code: int
    ) -> Response:
        """Create an error response for validation failures."""
        # Get request ID if available
        request_id = getattr(request.state, 'request_id', None)
        
        # Create detailed error response
        error_response = ErrorResponse(
            error_type=ErrorType.VALIDATION_ERROR,
            message=message,
            details=[
                ErrorDetail(
                    field="request",
                    message=message,
                    code="VALIDATION_FAILED",
                    context={
                        "method": request.method,
                        "path": str(request.url.path),
                        "user_agent": request.headers.get("user-agent", ""),
                        "content_type": request.headers.get("content-type", "")
                    }
                )
            ],
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump(mode='json')
        )


def add_request_validation_middleware(
    app,
    allowed_content_types: Optional[List[str]] = None,
    max_headers: Optional[int] = None,
    max_header_size: Optional[int] = None,
    require_user_agent: bool = False,
    allowed_methods: Optional[Set[str]] = None,
    blocked_user_agents: Optional[List[str]] = None,
    exclude_paths: Optional[List[str]] = None
) -> None:
    """
    Add request validation middleware to FastAPI app.
    
    Args:
        app: FastAPI application instance
        allowed_content_types: List of allowed Content-Type values
        max_headers: Maximum number of headers allowed
        max_header_size: Maximum size of individual headers
        require_user_agent: Whether User-Agent header is required
        allowed_methods: Set of allowed HTTP methods
        blocked_user_agents: List of blocked User-Agent patterns
        exclude_paths: List of paths to exclude from validation
    """
    # Add file upload content types for OCR service
    default_content_types = [
        "application/json",
        "multipart/form-data",
        "application/x-www-form-urlencoded",
        "text/plain",
        "application/octet-stream",
        "application/pdf",
        "image/*"  # Allow all image types
    ]
    
    if allowed_content_types:
        # Merge with defaults
        content_types = list(set(default_content_types + allowed_content_types))
    else:
        content_types = default_content_types
    
    # Default exclude paths for API documentation and health checks
    default_exclude_paths = [
        "/docs",
        "/redoc",
        "/openapi.json", 
        "/api/v1/health",
        "/api-info",
        "/schema-stats"
    ]
    
    if exclude_paths:
        exclude_paths.extend(default_exclude_paths)
    else:
        exclude_paths = default_exclude_paths
    
    app.add_middleware(
        RequestValidationMiddleware,
        allowed_content_types=content_types,
        max_headers=max_headers,
        max_header_size=max_header_size,
        require_user_agent=require_user_agent,
        allowed_methods=allowed_methods,
        blocked_user_agents=blocked_user_agents,
        exclude_paths=exclude_paths
    )
    
    logger.info("Request validation middleware added to application")