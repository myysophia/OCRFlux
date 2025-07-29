"""
File cleanup middleware for automatic temporary file management
"""
import asyncio
import logging
from datetime import datetime, timedelta
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.file_handler import file_handler

logger = logging.getLogger(__name__)


class FileCleanupMiddleware(BaseHTTPMiddleware):
    """Middleware to handle automatic cleanup of temporary files"""
    
    def __init__(self, app, cleanup_interval_hours: int = 1, max_file_age_hours: int = 24):
        """
        Initialize file cleanup middleware
        
        Args:
            app: FastAPI application
            cleanup_interval_hours: How often to run cleanup (in hours)
            max_file_age_hours: Maximum age of files to keep (in hours)
        """
        super().__init__(app)
        self.cleanup_interval = cleanup_interval_hours * 3600  # Convert to seconds
        self.max_file_age = max_file_age_hours
        self.last_cleanup = datetime.utcnow()
        
    async def dispatch(self, request: Request, call_next):
        """Process request and handle cleanup"""
        
        # Check if it's time for cleanup
        current_time = datetime.utcnow()
        if (current_time - self.last_cleanup).total_seconds() > self.cleanup_interval:
            # Run cleanup in background
            asyncio.create_task(self._background_cleanup())
            self.last_cleanup = current_time
        
        # Process the request
        response = await call_next(request)
        
        return response
    
    async def _background_cleanup(self):
        """Run file cleanup in background"""
        try:
            cleaned_count = file_handler.cleanup_old_files(self.max_file_age)
            if cleaned_count > 0:
                logger.info(f"Background cleanup removed {cleaned_count} old files")
        except Exception as e:
            logger.error(f"Error during background file cleanup: {e}")


def add_file_cleanup_middleware(app, cleanup_interval_hours: int = 1, max_file_age_hours: int = 24):
    """
    Add file cleanup middleware to FastAPI app
    
    Args:
        app: FastAPI application
        cleanup_interval_hours: How often to run cleanup
        max_file_age_hours: Maximum age of files to keep
    """
    app.add_middleware(
        FileCleanupMiddleware,
        cleanup_interval_hours=cleanup_interval_hours,
        max_file_age_hours=max_file_age_hours
    )