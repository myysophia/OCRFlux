"""
OCRFlux API Service - Enhanced Main Application

Enhanced version with more endpoints but simplified imports.
"""
import logging
import os
import sys
import time
import tempfile
import asyncio
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
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
        self.log_level = os.getenv("LOG_LEVEL", "DEBUG")
        self.gpu_memory_utilization = float(os.getenv("GPU_MEMORY_UTILIZATION", 0.9))
        self.max_concurrent_tasks = int(os.getenv("MAX_CONCURRENT_TASKS", 8))
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", 209715200))
        self.temp_dir = os.getenv("TEMP_DIR", "/tmp/ocrflux")
        
        # Create temp directory
        os.makedirs(self.temp_dir, exist_ok=True)

# Global config
config = SimpleConfig()

# Simple task storage (in-memory for demo)
tasks = {}

# Background OCR processing function
async def process_ocr_background(task_id: str, file_path: str, file_name: str, file_size: int, options: dict):
    """Background OCR processing function"""
    try:
        # Update task status to processing
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = 0.1
        tasks[task_id]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        logger.info(f"Starting background OCR processing for task {task_id}: {file_name}")
        
        start_time = time.time()
        
        # Import OCRFlux
        from ocrflux.inference import parse as ocrflux_parse
        from vllm import LLM
        
        # Load model if not already loaded
        if not hasattr(app.state, 'model') or app.state.model is None:
            logger.info(f"Loading OCRFlux model for task {task_id}...")
            tasks[task_id]["progress"] = 0.2
            app.state.model = LLM(
                model=config.model_path,
                gpu_memory_utilization=config.gpu_memory_utilization,
                trust_remote_code=True,
                enforce_eager=False,
                disable_log_stats=True,
            )
            logger.info("Model loaded successfully")
        
        # Update progress
        tasks[task_id]["progress"] = 0.3
        tasks[task_id]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        # Process with OCRFlux
        logger.info(f"Starting OCRFlux processing for task {task_id}: {file_name}")
        tasks[task_id]["progress"] = 0.5
        
        ocr_result = ocrflux_parse(
            llm=app.state.model,
            file_path=file_path,
            skip_cross_page_merge=options.get("skip_cross_page_merge", False),
            max_page_retries=options.get("max_page_retries", 1)
        )
        
        processing_time = time.time() - start_time
        
        if ocr_result:
            # Extract results from OCRFlux
            document_text = ocr_result.get("document_text", "")
            page_texts = ocr_result.get("page_texts", {})
            fallback_pages = ocr_result.get("fallback_pages", [])
            num_pages = len(page_texts) if page_texts else 1
            
            # Store successful result
            result = {
                "success": True,
                "file_name": file_name,
                "file_size": file_size,
                "num_pages": num_pages,
                "document_text": document_text,
                "page_texts": page_texts,
                "fallback_pages": fallback_pages,
                "processing_time": processing_time,
                "error_message": None
            }
            
            # Update task with result
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["progress"] = 1.0
            tasks[task_id]["result"] = result
            tasks[task_id]["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            tasks[task_id]["processing_time"] = processing_time
            
            logger.info(f"Background OCR processing completed for task {task_id}: {file_name}, pages: {num_pages}, time: {processing_time:.2f}s")
            
        else:
            raise Exception("OCRFlux returned empty result")
            
    except Exception as e:
        logger.error(f"Background OCR processing failed for task {task_id}: {e}")
        processing_time = time.time() - start_time if 'start_time' in locals() else 0
        
        # Store error result
        error_result = {
            "success": False,
            "file_name": file_name,
            "file_size": file_size,
            "num_pages": 0,
            "document_text": "",
            "page_texts": {},
            "fallback_pages": [],
            "processing_time": processing_time,
            "error_message": f"OCR processing failed: {str(e)}"
        }
        
        # Update task with error
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["progress"] = 1.0
        tasks[task_id]["result"] = error_result
        tasks[task_id]["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        tasks[task_id]["error_message"] = str(e)
        
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up temp file for task {task_id}: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file for task {task_id}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Enhanced OCRFlux API Service...")
    logger.info(f"Model path: {config.model_path}")
    logger.info(f"Temp directory: {config.temp_dir}")
    
    # Startup
    try:
        # Initialize model state
        app.state.model = None
        
        # Optionally preload model (uncomment if you want to preload)
        # logger.info("Preloading OCRFlux model...")
        # try:
        #     from vllm import LLM
        #     app.state.model = LLM(
        #         model=config.model_path,
        #         gpu_memory_utilization=config.gpu_memory_utilization,
        #         trust_remote_code=True,
        #         enforce_eager=False,
        #         disable_log_stats=True,
        #     )
        #     logger.info("Model preloaded successfully")
        # except Exception as e:
        #     logger.warning(f"Model preload failed: {e}")
        
        logger.info("OCRFlux API Service ready (model will load on first request)")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Enhanced OCRFlux API Service...")

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

# Root endpoint
@app.get("/", tags=["General"])
async def root():
    """Root endpoint with service information"""
    return {
        "message": "OCRFlux API Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "status": "running"
    }

# API info endpoint
@app.get("/api-info", tags=["General"])
async def api_info():
    """API information endpoint"""
    return {
        "name": "OCRFlux API Service",
        "version": "1.0.0",
        "description": "OCRFlux API Service for PDF and image to Markdown conversion",
        "endpoints": {
            "health": "/api/v1/health",
            "health_detailed": "/api/v1/health/detailed",
            "parse_single": "/api/v1/parse",
            "parse_async": "/api/v1/parse-async",
            "parse_batch": "/api/v1/batch",
            "task_status": "/api/v1/tasks/{task_id}",
            "task_result": "/api/v1/tasks/{task_id}/result",
            "docs": "/docs",
            "openapi": "/openapi.json"
        },
        "supported_formats": [".pdf", ".png", ".jpg", ".jpeg"],
        "max_file_size_mb": config.max_file_size / (1024 * 1024),
        "model_path": config.model_path,
        "model_exists": os.path.exists(config.model_path)
    }

# Health check endpoints
@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": "1.0.0",
        "model_path": config.model_path,
        "model_exists": os.path.exists(config.model_path)
    }

@app.get("/api/v1/health/detailed", tags=["Health"])
async def health_check_detailed():
    """Detailed health check endpoint"""
    import psutil
    
    # Get system info
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": "1.0.0",
        "uptime": time.time(),
        "model": {
            "path": config.model_path,
            "exists": os.path.exists(config.model_path),
            "loaded": hasattr(app.state, 'model') and app.state.model is not None,
            "gpu_memory_utilization": config.gpu_memory_utilization
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": round((disk.used / disk.total) * 100, 2)
            }
        },
        "tasks": {
            "active": len([t for t in tasks.values() if t.get("status") == "processing"]),
            "pending": len([t for t in tasks.values() if t.get("status") == "pending"]),
            "completed": len([t for t in tasks.values() if t.get("status") == "completed"]),
            "total": len(tasks)
        }
    }

# Single file processing endpoint
@app.post("/api/v1/parse", tags=["OCR Processing"])
async def parse_file(
    file: UploadFile = File(..., description="PDF or image file to process"),
    skip_cross_page_merge: bool = Form(False, description="Skip cross-page merging"),
    max_page_retries: int = Form(1, description="Maximum retry attempts per page")
):
    """
    Parse a single file (PDF or image) and convert to Markdown
    
    - **file**: PDF or image file to process
    - **skip_cross_page_merge**: Skip cross-page merging (default: False)
    - **max_page_retries**: Maximum retry attempts per page (default: 1)
    """
    # Validate file type
    allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
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
        
        # Real OCRFlux processing
        try:
            # Import OCRFlux
            from ocrflux.inference import parse as ocrflux_parse
            from vllm import LLM
            
            # Load model if not already loaded
            if not hasattr(app.state, 'model') or app.state.model is None:
                logger.info("Loading OCRFlux model...")
                app.state.model = LLM(
                    model=config.model_path,
                    gpu_memory_utilization=config.gpu_memory_utilization,
                    trust_remote_code=True,
                    enforce_eager=False,
                    disable_log_stats=True,
                )
                logger.info("Model loaded successfully")
            
            # Process with OCRFlux
            logger.info(f"Starting OCRFlux processing for: {file.filename}")
            ocr_result = ocrflux_parse(
                llm=app.state.model,
                file_path=temp_file_path,
                skip_cross_page_merge=skip_cross_page_merge,
                max_page_retries=max_page_retries
            )
            
            processing_time = time.time() - start_time
            
            if ocr_result:
                # Extract results from OCRFlux
                document_text = ocr_result.get("document_text", "")
                page_texts = ocr_result.get("page_texts", {})
                fallback_pages = ocr_result.get("fallback_pages", [])
                
                # Count pages
                num_pages = len(page_texts) if page_texts else 1
                
                real_result = {
                    "success": True,
                    "file_name": file.filename,
                    "file_path": temp_file_path,
                    "file_size": len(content),
                    "num_pages": num_pages,
                    "document_text": document_text,
                    "page_texts": page_texts,
                    "fallback_pages": fallback_pages,
                    "processing_time": processing_time,
                    "error_message": None
                }
                
                logger.info(f"OCRFlux processing completed: {file.filename}, pages: {num_pages}, time: {processing_time:.2f}s")
                return real_result
            else:
                raise Exception("OCRFlux returned empty result")
                
        except Exception as ocr_error:
            logger.error(f"OCRFlux processing failed: {ocr_error}")
            processing_time = time.time() - start_time
            
            # Return error result
            error_result = {
                "success": False,
                "file_name": file.filename,
                "file_path": temp_file_path,
                "file_size": len(content),
                "num_pages": 0,
                "document_text": "",
                "page_texts": {},
                "fallback_pages": [],
                "processing_time": processing_time,
                "error_message": f"OCR processing failed: {str(ocr_error)}"
            }
            return error_result
        
        return mock_result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        
        return {
            "success": False,
            "file_name": file.filename,
            "file_path": temp_file_path or "",
            "file_size": 0,
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

# Async single file processing
@app.post("/api/v1/parse-async", tags=["OCR Processing"])
async def parse_file_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF or image file to process"),
    skip_cross_page_merge: bool = Form(False, description="Skip cross-page merging"),
    max_page_retries: int = Form(1, description="Maximum retry attempts per page")
):
    """
    Submit a single file for asynchronous OCR processing
    
    This endpoint immediately returns a task ID and processes the file in the background.
    Use this for large files or when you want to avoid timeout issues with proxies like Cloudflare.
    
    Returns a task ID that can be used to check processing status and retrieve results.
    """
    import uuid
    
    # Validate file type
    allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
    if file.size and file.size > config.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size {file.size} bytes exceeds maximum limit of {config.max_file_size} bytes"
        )
    
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, dir=config.temp_dir) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Store task info
        tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "file_name": file.filename,
            "file_size": len(content),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "progress": 0.0,
            "options": {
                "skip_cross_page_merge": skip_cross_page_merge,
                "max_page_retries": max_page_retries
            }
        }
        
        # Start background processing
        background_tasks.add_task(
            process_ocr_background,
            task_id,
            temp_file_path,
            file.filename,
            len(content),
            {
                "skip_cross_page_merge": skip_cross_page_merge,
                "max_page_retries": max_page_retries
            }
        )
        
        logger.info(f"Created async task {task_id} for file: {file.filename} ({len(content)} bytes)")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Task submitted successfully for background processing",
            "file_name": file.filename,
            "file_size": len(content),
            "status_url": f"/api/v1/tasks/{task_id}",
            "result_url": f"/api/v1/tasks/{task_id}/result",
            "estimated_time": "Processing time varies based on file size and complexity"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit async task for {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit file for processing: {str(e)}"
        )

# Batch processing endpoint
@app.post("/api/v1/batch", tags=["OCR Processing"])
async def parse_batch_files(
    files: List[UploadFile] = File(..., description="List of PDF or image files to process"),
    skip_cross_page_merge: bool = Form(False, description="Skip cross-page merging"),
    max_page_retries: int = Form(1, description="Maximum retry attempts per page")
):
    """
    Process multiple PDF or image files and extract text content in Markdown format
    
    Maximum 10 files per batch request.
    """
    # Check batch size limit
    MAX_BATCH_SIZE = 10
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files in batch. Maximum {MAX_BATCH_SIZE} files allowed."
        )
    
    logger.info(f"Starting batch processing for {len(files)} files")
    
    batch_start_time = time.time()
    results = []
    
    for i, file in enumerate(files):
        logger.info(f"Processing file {i+1}/{len(files)}: {file.filename}")
        
        try:
            # Simulate processing each file
            file_start_time = time.time()
            content = await file.read()
            file_processing_time = time.time() - file_start_time
            
            result = {
                "success": True,
                "file_name": file.filename,
                "file_size": len(content),
                "num_pages": 1,
                "document_text": f"# Batch OCR Result for {file.filename}\n\nThis is a mock batch OCR result for file {i+1} of {len(files)}.",
                "page_texts": {"0": f"Mock content for {file.filename}"},
                "fallback_pages": [],
                "processing_time": file_processing_time,
                "error_message": None
            }
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            error_result = {
                "success": False,
                "file_name": file.filename,
                "file_size": 0,
                "num_pages": 0,
                "document_text": "",
                "page_texts": {},
                "fallback_pages": [],
                "processing_time": 0.0,
                "error_message": str(e)
            }
            results.append(error_result)
    
    # Calculate batch statistics
    total_processing_time = time.time() - batch_start_time
    successful_files = sum(1 for r in results if r["success"])
    failed_files = len(results) - successful_files
    
    return {
        "total_files": len(files),
        "successful_files": successful_files,
        "failed_files": failed_files,
        "results": results,
        "total_processing_time": total_processing_time
    }

# Task status endpoint
@app.get("/api/v1/tasks/{task_id}", tags=["Task Management"])
async def get_task_status(task_id: str):
    """Get the status of an asynchronous task"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    # Return current task status (no simulation, real status)
    response = {
        "task_id": task["task_id"],
        "status": task["status"],
        "progress": task["progress"],
        "file_name": task["file_name"],
        "file_size": task.get("file_size", 0),
        "created_at": task["created_at"],
        "updated_at": task.get("updated_at", task["created_at"])
    }
    
    # Add completion info if available
    if "completed_at" in task:
        response["completed_at"] = task["completed_at"]
    
    if "processing_time" in task:
        response["processing_time"] = task["processing_time"]
    
    if "error_message" in task:
        response["error_message"] = task["error_message"]
    
    return response

# Task result endpoint
@app.get("/api/v1/tasks/{task_id}/result", tags=["Task Management"])
async def get_task_result(task_id: str):
    """Get the result of a completed asynchronous task"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    if task["status"] == "pending":
        raise HTTPException(status_code=202, detail="Task is still pending")
    elif task["status"] == "processing":
        raise HTTPException(status_code=202, detail=f"Task is still processing (progress: {task['progress']*100:.1f}%)")
    elif task["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Task failed: {task.get('error_message', 'Unknown error')}")
    elif task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task status is {task['status']}")
    
    # Return real OCR result
    if "result" not in task:
        raise HTTPException(status_code=500, detail="Task completed but result not found")
    
    return task["result"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower()
    )