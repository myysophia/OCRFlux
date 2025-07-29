"""
Request ID middleware for request tracking and correlation
"""
import uuid
import logging
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and track request IDs for correlation.
    
    This middleware generates a unique request ID for each incoming request
    and adds it to the request state and response headers for tracking.
    It also supports accepting existing request IDs from clients.
    """
    
    def __init__(
        self, 
        app,
        header_name: str = "X-Request-ID",
        generate_if_missing: bool = True,
        include_in_response: bool = True
    ):
        """
        Initialize request ID middleware.
        
        Args:
            app: FastAPI application instance
            header_name: Header name for request ID
            generate_if_missing: Generate new ID if not provided by client
            include_in_response: Include request ID in response headers
        """
        super().__init__(app)
        self.header_name = header_name
        self.generate_if_missing = generate_if_missing
        self.include_in_response = include_in_response
        
        logger.info(
            f"Request ID middleware initialized: "
            f"header={header_name}, generate={generate_if_missing}, "
            f"include_response={include_in_response}"
        )
    
    async def dispatch(self, request: Request, call_next):
        """
        Generate or extract request ID and add to request state.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain
            
        Returns:
            HTTP response with request ID header
        """
        # Try to get existing request ID from headers
        request_id = request.headers.get(self.header_name)
        
        # Validate existing request ID format
        if request_id:
            request_id = self._validate_request_id(request_id)
        
        # Generate new request ID if needed
        if not request_id and self.generate_if_missing:
            request_id = self._generate_request_id()
            logger.debug(f"Generated new request ID: {request_id}")
        elif request_id:
            logger.debug(f"Using client-provided request ID: {request_id}")
        
        # Store request ID in request state for other middleware/handlers
        if request_id:
            request.state.request_id = request_id
        
        # Process request
        response: Response = await call_next(request)
        
        # Add request ID to response headers
        if request_id and self.include_in_response:
            response.headers[self.header_name] = request_id
        
        return response
    
    def _generate_request_id(self) -> str:
        """
        Generate a new unique request ID.
        
        Returns:
            UUID4 string as request ID
        """
        return str(uuid.uuid4())
    
    def _validate_request_id(self, request_id: str) -> Optional[str]:
        """
        Validate request ID format and length.
        
        Args:
            request_id: Request ID to validate
            
        Returns:
            Valid request ID or None if invalid
        """
        if not request_id:
            return None
        
        # Remove whitespace
        request_id = request_id.strip()
        
        # Check length (reasonable limits)
        if len(request_id) < 8 or len(request_id) > 128:
            logger.warning(f"Invalid request ID length: {len(request_id)}")
            return None
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not all(c.isalnum() or c in '-_' for c in request_id):
            logger.warning(f"Invalid request ID characters: {request_id}")
            return None
        
        return request_id


def add_request_id_middleware(
    app,
    header_name: str = "X-Request-ID",
    generate_if_missing: bool = True,
    include_in_response: bool = True
) -> None:
    """
    Add request ID middleware to FastAPI app.
    
    Args:
        app: FastAPI application instance
        header_name: Header name for request ID
        generate_if_missing: Generate new ID if not provided by client
        include_in_response: Include request ID in response headers
    """
    app.add_middleware(
        RequestIDMiddleware,
        header_name=header_name,
        generate_if_missing=generate_if_missing,
        include_in_response=include_in_response
    )
    
    logger.info(f"Request ID middleware added with header: {header_name}")


class RequestCorrelationContext:
    """
    Context manager for request correlation in async operations.
    
    This helps maintain request ID context across async operations
    and background tasks.
    """
    
    def __init__(self, request_id: str):
        """
        Initialize correlation context.
        
        Args:
            request_id: Request ID for correlation
        """
        self.request_id = request_id
        self._previous_id = None
    
    def __enter__(self):
        """Enter correlation context."""
        # Store current context if any
        import contextvars
        try:
            self._previous_id = _request_id_context.get()
        except LookupError:
            self._previous_id = None
        
        # Set new context
        _request_id_context.set(self.request_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit correlation context."""
        # Restore previous context
        if self._previous_id is not None:
            _request_id_context.set(self._previous_id)
        else:
            try:
                _request_id_context.delete()
            except LookupError:
                pass


# Context variable for request ID tracking across async operations
import contextvars
_request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar('request_id')


def get_current_request_id() -> Optional[str]:
    """
    Get current request ID from context.
    
    Returns:
        Current request ID or None if not available
    """
    try:
        return _request_id_context.get()
    except LookupError:
        return None


def set_request_id_context(request_id: str) -> None:
    """
    Set request ID in current context.
    
    Args:
        request_id: Request ID to set
    """
    _request_id_context.set(request_id)


def create_correlation_context(request_id: str) -> RequestCorrelationContext:
    """
    Create a correlation context for the given request ID.
    
    Args:
        request_id: Request ID for correlation
        
    Returns:
        Correlation context manager
    """
    return RequestCorrelationContext(request_id)