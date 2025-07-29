#!/usr/bin/env python3
"""
OCRFlux API Service startup script
"""
import uvicorn
from api.main import app
from api.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )