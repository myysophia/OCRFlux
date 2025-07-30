"""
OCRFlux API Service - Complete Main Application

FastAPI application for OCRFlux PDF and image to Markdown conversion.
This version integrates all implemented components.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add current directory to Python path
current_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(current_dir))

# Import core components
from api.core.config import settings
from api.core.model_manager import model_manager
from api.core.task_queue import task_queue
from api.middleware.error_handler import add_exception_handlers
from api.middleware.cors import setup_cors
from api.middleware.request_id import RequestIDMiddleware
from api.middleware.logging import LoggingMiddleware

# Import routes
from api.routes.ocr import router as ocr_router
from api.routes.health import router as health_router
from api.routes.tasks import router as tasks_router
from api.routes.docs import router as docs_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting OCRFlux API Service...")
    logger.info(f"Model path: {settings.model_path}")
    logger.info(f"Temp directory: {settings.temp_dir}")
    
    # Startup
    try:
        # Create temp directory
        settings.create_temp_dir()
        
        # Initialize model manager
        logger.info("Initializing model manager...")
        await model_manager.load_model()
        
        # Initialize task queue
        logger.info("Initializing task queue...")
        await task_queue.start()
        
        # Register task handlers
        from api.routes.ocr import ocr_single_file_handler, ocr_batch_files_handler
        task_queue.register_handler("ocr_single_file", ocr_single_file_handler)
        task_queue.register_handler("ocr_batch_files", ocr_batch_files_handler)
        
        logger.info("OCRFlux API Service startup complete")
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down OCRFlux API Service...")
        try:
            await task_queue.stop()
            await model_manager.unload_model()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Fast, efficient, and high-quality OCR powered by open visual language models",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url=settings.openapi_url
)

# Add middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)

# Setup CORS
setup_cors(app)

# Add exception handlers
add_exception_handlers(app)

# Include routers
app.include_router(ocr_router)
app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(docs_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "docs": settings.docs_url,
        "health": "/api/v1/health",
        "status": "running"
    }

# API info endpoint
@app.get("/api-info")
async def api_info():
    """API information endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "OCRFlux API Service for PDF and image to Markdown conversion",
        "endpoints": {
            "health": "/api/v1/health",
            "parse_single": "/api/v1/parse",
            "parse_async": "/api/v1/parse-async",
            "parse_batch": "/api/v1/batch",
            "parse_batch_async": "/api/v1/batch-async",
            "task_status": "/api/v1/tasks/{task_id}",
            "task_result": "/api/v1/tasks/{task_id}/result",
            "docs": settings.docs_url,
            "openapi": settings.openapi_url
        },
        "supported_formats": [".pdf", ".png", ".jpg", ".jpeg"],
        "max_file_size_mb": settings.max_file_size / (1024 * 1024),
        "model_path": settings.model_path,
        "model_loaded": model_manager.is_model_ready() if 'model_manager' in globals() else False
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )