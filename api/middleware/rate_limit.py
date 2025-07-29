"""
Rate limiting middleware
"""
import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..models.error import ErrorResponse, ErrorDetail, ErrorType
from ..middleware.error_handler import RateLimitError

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    
    This implements a token bucket algorithm that allows for burst traffic
    while maintaining an average rate limit.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens in the bucket
            refill_rate: Rate at which tokens are added (tokens per second)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens available
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill the bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def time_until_available(self, tokens: int = 1) -> float:
        """
        Calculate time until enough tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time in seconds until tokens are available
        """
        self._refill()
        
        if self.tokens >= tokens:
            return 0.0
        
        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class SlidingWindowCounter:
    """
    Sliding window counter for rate limiting.
    
    This implementation uses a sliding window to track requests
    over a specific time period.
    """
    
    def __init__(self, window_size: int, max_requests: int):
        """
        Initialize sliding window counter.
        
        Args:
            window_size: Size of the time window in seconds
            max_requests: Maximum requests allowed in the window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
    
    def is_allowed(self) -> Tuple[bool, Optional[int]]:
        """
        Check if a request is allowed.
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        
        # Remove old requests outside the window
        while self.requests and self.requests[0] <= now - self.window_size:
            self.requests.popleft()
        
        # Check if we're under the limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True, None
        
        # Calculate retry after time
        oldest_request = self.requests[0]
        retry_after = int(oldest_request + self.window_size - now) + 1
        
        return False, retry_after


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with multiple strategies.
    
    Supports both token bucket and sliding window rate limiting
    with per-IP and global rate limits.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: Optional[int] = None,
        exclude_paths: Optional[list] = None,
        strategy: str = "sliding_window"  # "token_bucket" or "sliding_window"
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application instance
            requests_per_minute: Maximum requests per minute per IP
            requests_per_hour: Maximum requests per hour per IP
            burst_size: Maximum burst size for token bucket (defaults to requests_per_minute)
            exclude_paths: List of paths to exclude from rate limiting
            strategy: Rate limiting strategy ("token_bucket" or "sliding_window")
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size or requests_per_minute
        self.exclude_paths = exclude_paths or []
        self.strategy = strategy
        
        # Storage for rate limit data per IP
        self.ip_data: Dict[str, Dict] = defaultdict(dict)
        
        # Cleanup old data periodically
        self.last_cleanup = time.time()
        self.cleanup_interval = 3600  # 1 hour
        
        logger.info(
            f"Rate limit middleware initialized: "
            f"{requests_per_minute}/min, {requests_per_hour}/hour, "
            f"strategy={strategy}"
        )
    
    async def dispatch(self, request: Request, call_next):
        """
        Check rate limits and process or reject the request.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain
            
        Returns:
            HTTP response
        """
        # Skip rate limiting for excluded paths
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Cleanup old data periodically
        await self._cleanup_old_data()
        
        # Check rate limits
        is_allowed, retry_after = self._check_rate_limit(client_ip)
        
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}: "
                f"{request.method} {request.url.path}"
            )
            
            raise RateLimitError(
                message=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute allowed.",
                retry_after=retry_after
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, client_ip)
        
        return response
    
    def _should_exclude_path(self, path: str) -> bool:
        """
        Check if a path should be excluded from rate limiting.
        
        Args:
            path: Request path
            
        Returns:
            True if path should be excluded
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
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
    
    def _check_rate_limit(self, client_ip: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limits.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if self.strategy == "token_bucket":
            return self._check_token_bucket_limit(client_ip)
        else:
            return self._check_sliding_window_limit(client_ip)
    
    def _check_token_bucket_limit(self, client_ip: str) -> Tuple[bool, Optional[int]]:
        """Check rate limit using token bucket algorithm."""
        ip_data = self.ip_data[client_ip]
        
        # Initialize token buckets if not exists
        if "minute_bucket" not in ip_data:
            ip_data["minute_bucket"] = TokenBucket(
                capacity=self.burst_size,
                refill_rate=self.requests_per_minute / 60.0  # tokens per second
            )
        
        if "hour_bucket" not in ip_data:
            ip_data["hour_bucket"] = TokenBucket(
                capacity=self.requests_per_hour,
                refill_rate=self.requests_per_hour / 3600.0  # tokens per second
            )
        
        minute_bucket = ip_data["minute_bucket"]
        hour_bucket = ip_data["hour_bucket"]
        
        # Check both buckets
        if not minute_bucket.consume():
            retry_after = int(minute_bucket.time_until_available()) + 1
            return False, retry_after
        
        if not hour_bucket.consume():
            # Refund the minute bucket token
            minute_bucket.tokens += 1
            retry_after = int(hour_bucket.time_until_available()) + 1
            return False, retry_after
        
        return True, None
    
    def _check_sliding_window_limit(self, client_ip: str) -> Tuple[bool, Optional[int]]:
        """Check rate limit using sliding window algorithm."""
        ip_data = self.ip_data[client_ip]
        
        # Initialize sliding windows if not exists
        if "minute_window" not in ip_data:
            ip_data["minute_window"] = SlidingWindowCounter(60, self.requests_per_minute)
        
        if "hour_window" not in ip_data:
            ip_data["hour_window"] = SlidingWindowCounter(3600, self.requests_per_hour)
        
        minute_window = ip_data["minute_window"]
        hour_window = ip_data["hour_window"]
        
        # Check minute window
        minute_allowed, minute_retry = minute_window.is_allowed()
        if not minute_allowed:
            return False, minute_retry
        
        # Check hour window
        hour_allowed, hour_retry = hour_window.is_allowed()
        if not hour_allowed:
            # Remove the request from minute window since we're rejecting
            if minute_window.requests:
                minute_window.requests.pop()
            return False, hour_retry
        
        return True, None
    
    def _add_rate_limit_headers(self, response: Response, client_ip: str):
        """
        Add rate limit headers to response.
        
        Args:
            response: HTTP response
            client_ip: Client IP address
        """
        ip_data = self.ip_data[client_ip]
        
        if self.strategy == "token_bucket":
            if "minute_bucket" in ip_data:
                minute_bucket = ip_data["minute_bucket"]
                response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
                response.headers["X-RateLimit-Remaining"] = str(int(minute_bucket.tokens))
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        else:
            if "minute_window" in ip_data:
                minute_window = ip_data["minute_window"]
                remaining = max(0, self.requests_per_minute - len(minute_window.requests))
                response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
    
    async def _cleanup_old_data(self):
        """Clean up old rate limit data to prevent memory leaks."""
        now = time.time()
        
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remove data for IPs that haven't been seen recently
        cutoff_time = now - 7200  # 2 hours
        ips_to_remove = []
        
        for ip, data in self.ip_data.items():
            # Check if any recent activity
            has_recent_activity = False
            
            if self.strategy == "sliding_window":
                if "minute_window" in data and data["minute_window"].requests:
                    if data["minute_window"].requests[-1] > cutoff_time:
                        has_recent_activity = True
            else:
                if "minute_bucket" in data:
                    if data["minute_bucket"].last_refill > cutoff_time:
                        has_recent_activity = True
            
            if not has_recent_activity:
                ips_to_remove.append(ip)
        
        # Remove old data
        for ip in ips_to_remove:
            del self.ip_data[ip]
        
        self.last_cleanup = now
        
        if ips_to_remove:
            logger.debug(f"Cleaned up rate limit data for {len(ips_to_remove)} IPs")


def add_rate_limit_middleware(
    app,
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    burst_size: Optional[int] = None,
    exclude_paths: Optional[list] = None,
    strategy: str = "sliding_window"
) -> None:
    """
    Add rate limiting middleware to FastAPI app.
    
    Args:
        app: FastAPI application instance
        requests_per_minute: Maximum requests per minute per IP
        requests_per_hour: Maximum requests per hour per IP
        burst_size: Maximum burst size for token bucket
        exclude_paths: List of paths to exclude from rate limiting
        strategy: Rate limiting strategy
    """
    exclude_paths = exclude_paths or [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health/simple",  # Allow health checks
        "/api-info",
        "/schema-stats"
    ]
    
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        burst_size=burst_size,
        exclude_paths=exclude_paths,
        strategy=strategy
    )
    
    logger.info(
        f"Rate limiting middleware added: "
        f"{requests_per_minute}/min, {requests_per_hour}/hour"
    )