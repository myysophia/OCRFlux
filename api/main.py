"""
OCRFlux API Service - Main Application

FastAPI application for OCRFlux PDF and image to Markdown conversion.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
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

# File upload and OCR processing endpoint
@app.post("/api/v1/parse")
async def parse_file(
    file: UploadFile = File(...),
    skip_cross_page_merge: bool = Form(False),
    max_page_retries: int = Form(1)
):
    """
    Parse a single file (PDF or image) and convert to Markdown
    
    - **file**: PDF or image file to process
    - **skip_cross_page_merge**: Skip cross-page merging (default: False)
    - **max_page_retries**: Maximum retry attempts per page (default: 1)
    """
    import time
    import tempfile
    import os
    from pathlib import Path
    
    # Validate file type
    allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check file size (200MB limit)
    if file.size and file.size > config.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size {file.size} bytes exceeds maximum limit of {config.max_file_size} bytes"
        )
    
    start_time = time.time()
    temp_file_path = None
    
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, dir=config.temp_dir) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Processing file: {file.filename} ({len(content)} bytes)")
        
        # For now, return a mock response
        # TODO: Integrate with actual OCRFlux processing
        processing_time = time.time() - start_time
        
        # Mock OCR result
        mock_result = {
            "success": True,
            "file_name": file.filename,
            "file_path": temp_file_path,
            "num_pages": 1,
            "document_text": f"# Mock OCR Result\n\nThis is a mock OCR result for file: {file.filename}\n\nProcessing options:\n- Skip cross-page merge: {skip_cross_page_merge}\n- Max page retries: {max_page_retries}\n\nActual OCR processing will be implemented next.",
            "page_texts": {
                "0": f"Mock content for {file.filename}"
            },
            "fallback_pages": [],
            "processing_time": processing_time,
            "error_message": None
        }
        
        return mock_result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        
        return {
            "success": False,
            "file_name": file.filename,
            "file_path": temp_file_path or "",
            "num_pages": 0,
            "document_text": "",
            "page_texts": {},
            "fallback_pages": [],
            "processing_time": processing_time,
            "error_message": str(e)
        }
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_file_path}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower()
    )