"""
Request logging middleware
"""
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses with request tracking.
    
    This middleware logs all incoming requests and outgoing responses,
    including timing information and request IDs for correlation.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get request ID if available (set by error handler middleware)
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Get client IP with proxy support
        client_ip = self._get_client_ip(request)
        
        # Get request size
        content_length = request.headers.get("content-length", "unknown")
        
        # Log request with detailed information
        logger.info(
            f"Request [{request_id}]: {request.method} {request.url.path} "
            f"from {client_ip} (size: {content_length} bytes)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "content_length": content_length,
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        # Process request
        response: Response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response with detailed information
        logger.info(
            f"Response [{request_id}]: {response.status_code} "
            f"processed in {process_time:.4f}s",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": process_time,
                "response_size": response.headers.get("content-length", "unknown")
            }
        )
        
        # Add headers for debugging and monitoring
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address with proxy support.
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers first (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"