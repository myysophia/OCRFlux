"""
OCRFlux API Service - Main Application

FastAPI application for OCRFlux PDF and image to Markdown conversion.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add current directory to Python path
current_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(current_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Simple configuration class
class SimpleConfig:
    def __init__(self):
        self.model_path = os.getenv("MODEL_PATH", "/var/lib/gpustack/cache/model_scope/ChatDOC/OCRFlux-3B")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", 8000))
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.gpu_memory_utilization = float(os.getenv("GPU_MEMORY_UTILIZATION", 0.9))
        self.max_concurrent_tasks = int(os.getenv("MAX_CONCURRENT_TASKS", 8))
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", 209715200))
        self.temp_dir = os.getenv("TEMP_DIR", "/tmp/ocrflux")
        
        # Create temp directory
        os.makedirs(self.temp_dir, exist_ok=True)

# Global config
config = SimpleConfig()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting OCRFlux API Service...")
    logger.info(f"Model path: {config.model_path}")
    logger.info(f"Temp directory: {config.temp_dir}")
    
    # Startup
    try:
        # Initialize model manager (simplified)
        logger.info("Initializing model manager...")
        # We'll add model loading here later
        yield
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down OCRFlux API Service...")

# Create FastAPI app
app = FastAPI(
    title="OCRFlux API Service",
    description="Fast, efficient, and high-quality OCR powered by open visual language models",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic health check endpoint
@app.get("/api/v1/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "model_path": config.model_path,
        "model_exists": os.path.exists(config.model_path)
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OCRFlux API Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

# Simple file upload endpoint (placeholder)
@app.post("/api/v1/parse")
async def parse_file():
    """Parse file endpoint (placeholder)"""
    return {
        "message": "OCR parsing endpoint - implementation in progress",
        "status": "placeholder"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower()
    )