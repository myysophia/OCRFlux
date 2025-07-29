"""
OCRFlux API Service - Main application entry point
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.core.config import settings
from api.core.logging import setup_logging
from api.core.exception_handlers import setup_exception_handlers
from api.core.openapi import setup_openapi_customization
from api.middleware.config import setup_all_middleware, DEVELOPMENT_MIDDLEWARE_CONFIG, PRODUCTION_MIDDLEWARE_CONFIG
from api.routes import health, files, ocr, tasks, docs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    
    Handles startup and shutdown events for the FastAPI application.
    """
    import logging
    import signal
    import asyncio
    from api.core.model_manager import model_manager
    from api.core.task_queue import task_queue
    
    logger = logging.getLogger(__name__)
    
    # Startup
    logger.info("🚀 Starting OCRFlux API Service...")
    
    try:
        # Setup logging
        setup_logging()
        logger.info("✅ Logging configured")
        
        # Create temporary directory
        settings.create_temp_dir()
        logger.info(f"✅ Temporary directory created: {settings.temp_dir}")
        
        # Initialize model manager (but don't load model yet)
        logger.info("🔧 Initializing model manager...")
        # Model will be loaded on first request to avoid startup delays
        
        # Start task queue
        logger.info("🔧 Starting task queue...")
        await task_queue.start()
        logger.info("✅ Task queue started")
        
        # Register signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("🎉 OCRFlux API Service startup completed successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    # Shutdown
    logger.info("🛑 Shutting down OCRFlux API Service...")
    
    try:
        # Stop task queue
        logger.info("🔧 Stopping task queue...")
        await task_queue.stop()
        logger.info("✅ Task queue stopped")
        
        # Unload model if loaded
        if model_manager.is_model_ready():
            logger.info("🔧 Unloading model...")
            await model_manager.unload_model()
            logger.info("✅ Model unloaded")
        
        # Cleanup temporary files
        logger.info("🔧 Cleaning up temporary files...")
        from api.core.file_handler import file_handler
        cleaned_count = file_handler.cleanup_old_files(max_age_hours=0)  # Clean all files
        logger.info(f"✅ Cleaned up {cleaned_count} temporary files")
        
        logger.info("✅ OCRFlux API Service shutdown completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")
        # Don't raise during shutdown to avoid masking the original issue


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
# OCRFlux API Service

**Fast, efficient, and high-quality OCR powered by open visual language models.**

Transform your PDF documents and images into structured Markdown text with advanced OCR capabilities. Built on state-of-the-art vision-language models, OCRFlux delivers superior text extraction with intelligent document structure recognition.

## 🚀 Key Features

### Core Processing Capabilities
- **📄 Single File Processing**: Upload PDF or image files for immediate OCR processing with real-time results
- **📚 Batch Processing**: Process multiple files simultaneously with intelligent resource management
- **⚡ Asynchronous Processing**: Submit large files for background processing with comprehensive status tracking
- **🔄 Smart Retry Logic**: Configurable retry mechanisms for robust processing of challenging documents

### File Format Support
- **PDF Documents**: Multi-page PDF files with complex layouts, tables, and mixed content
- **Image Files**: PNG, JPG, JPEG images containing text, documents, receipts, and forms
- **Quality Optimization**: Automatic image preprocessing for optimal text recognition

### Advanced Processing Options
- **🔗 Cross-page Merging**: Intelligently merge text elements that span across page boundaries
- **📐 Image Processing**: Adjustable resolution and rotation for optimal OCR accuracy  
- **🎯 Quality Control**: Fallback handling and quality assessment for each processed page
- **⚙️ Configurable Parameters**: Fine-tune processing behavior for different document types

### Enterprise Features
- **📊 Health Monitoring**: Comprehensive system health checks and performance metrics
- **📋 Task Management**: Full lifecycle management for asynchronous processing tasks
- **🔍 Detailed Logging**: Complete audit trail and debugging information
- **📈 Performance Analytics**: Processing statistics and optimization insights

## 📋 Supported File Types

| Format | Extensions | Max Size | Notes |
|--------|------------|----------|-------|
| **PDF** | `.pdf` | 100MB | Multi-page documents, forms, reports |
| **Images** | `.png`, `.jpg`, `.jpeg` | 100MB | Scanned documents, photos, screenshots |

## ⚙️ Processing Options

### Cross-page Merging
Intelligently combines text elements that span multiple pages, such as:
- Tables that continue across pages
- Paragraphs split by page breaks  
- Multi-page forms and documents

### Quality & Performance Tuning
- **Image Resolution**: Balance processing speed vs. text recognition quality
- **Retry Behavior**: Configure retry attempts for challenging or corrupted pages
- **Rotation Correction**: Automatic or manual rotation for scanned documents
- **Fallback Processing**: Graceful degradation for problematic content

## 🔐 Security & Authentication

**Current Status**: No authentication required for development/testing environments.

**Production Recommendations**:
- Implement API key authentication
- Add rate limiting per client
- Use HTTPS for all communications
- Consider IP whitelisting for sensitive deployments

## 📊 Rate Limits & Quotas

**Current Status**: No rate limits enforced.

**Recommended Production Limits**:
- 100 requests per minute per client
- 1000 requests per hour per client  
- 10 concurrent async tasks per client
- 100MB total upload size per request

## 🚦 Getting Started

1. **Health Check**: Verify service status at `/api/v1/health`
2. **Single File**: Upload a test document to `/api/v1/parse`
3. **Batch Processing**: Try multiple files with `/api/v1/batch`
4. **Async Processing**: Use `/api/v1/parse-async` for large files
5. **Documentation**: Explore interactive docs at `/docs`

## 📚 API Documentation

- **Swagger UI**: Interactive API testing at `/docs`
- **ReDoc**: Comprehensive documentation at `/redoc`  
- **OpenAPI Schema**: Machine-readable spec at `/openapi.json`
- **API Information**: Service details at `/api-info`
        """.strip(),
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        lifespan=lifespan,
        contact={
            "name": "OCRFlux API Support Team",
            "url": "https://github.com/your-org/ocrflux-api",
            "email": "support@ocrflux.example.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
            "identifier": "MIT"
        },
        terms_of_service="https://ocrflux.example.com/terms",
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.ocrflux.example.com",
                "description": "Production server"
            }
        ],
        tags_metadata=[
            {
                "name": "Documentation",
                "description": """
**API Documentation and Schema**

Access comprehensive API documentation, interactive testing interfaces, and machine-readable schemas.

**Available Endpoints:**
- `/docs` - Interactive Swagger UI for testing APIs
- `/redoc` - Comprehensive ReDoc documentation  
- `/openapi.json` - Complete OpenAPI 3.0 schema
- `/api-info` - Service information and capabilities
- `/schema-stats` - API schema statistics and metrics

**Use Cases:**
- Explore available endpoints and parameters
- Test API functionality interactively
- Generate client SDKs in various languages
- Integrate with API testing tools (Postman, Insomnia)
- Validate request/response formats
                """.strip()
            },
            {
                "name": "Health Check", 
                "description": """
**Service Health Monitoring**

Monitor service availability, system resources, and operational status for production deployments.

**Health Check Types:**
- **Comprehensive**: Full system health with detailed metrics
- **Simple**: Basic status for load balancer health checks
- **Model**: OCR model loading status and performance
- **System**: Hardware resources and capacity information

**Monitoring Integration:**
- Prometheus metrics collection
- Grafana dashboard compatibility  
- Alerting system integration
- Load balancer health checks

**Key Metrics:**
- Model loading status and memory usage
- Active task count and queue depth
- System resource utilization
- Processing performance statistics
                """.strip()
            },
            {
                "name": "OCR Processing",
                "description": """
**Core OCR Processing Capabilities**

Transform PDF documents and images into structured Markdown text using advanced vision-language models.

**Processing Modes:**
- **Synchronous**: Immediate processing with real-time results (< 10MB files)
- **Asynchronous**: Background processing for large files with status tracking
- **Batch**: Multiple file processing with optimized resource utilization

**Supported Formats:**
- PDF documents (multi-page, complex layouts)
- PNG images (high quality, lossless)
- JPG/JPEG images (photos, scanned documents)

**Advanced Features:**
- Cross-page text merging for tables and paragraphs
- Intelligent document structure recognition
- Configurable quality vs. speed optimization
- Automatic rotation correction for scanned documents
- Robust error handling with fallback processing

**Quality Control:**
- Page-level success tracking
- Fallback page identification
- Processing time optimization
- Retry logic for failed pages
                """.strip()
            },
            {
                "name": "Task Management",
                "description": """
**Asynchronous Task Processing**

Manage long-running OCR tasks with comprehensive status tracking and result retrieval.

**Task Lifecycle:**
1. **Submission** - Upload files and receive task ID
2. **Queuing** - Task enters processing queue with priority
3. **Processing** - Real-time progress updates and ETA
4. **Completion** - Results available for retrieval
5. **Cleanup** - Automatic result expiration and cleanup

**Task Operations:**
- Submit single file or batch processing tasks
- Query task status with progress percentage
- Retrieve completed results
- Cancel pending or running tasks
- List and filter task history

**Status Tracking:**
- Real-time progress updates (0-100%)
- Estimated completion time
- Processing stage information
- Error details for failed tasks

**Use Cases:**
- Large document processing (> 10MB)
- Batch processing workflows
- Background processing integration
- Long-running document analysis
                """.strip()
            },
            {
                "name": "File Management",
                "description": """
**File Handling and Validation**

Utilities for file upload validation, temporary storage management, and processing preparation.

**File Validation:**
- Format verification (PDF, PNG, JPG, JPEG)
- Size limit enforcement (100MB maximum)
- Content integrity checking
- Security scanning for malicious content

**Temporary Storage:**
- Secure temporary file storage
- Automatic cleanup after processing
- Configurable retention policies
- Storage quota management

**Processing Preparation:**
- File format optimization
- Image preprocessing and enhancement
- Document structure analysis
- Metadata extraction

**Management Features:**
- Upload progress tracking
- File information extraction
- Storage usage monitoring
- Cleanup and maintenance utilities

**Security Considerations:**
- File type validation beyond extensions
- Virus scanning integration points
- Secure temporary storage isolation
- Automatic sensitive data cleanup
                """.strip()
            }
        ]
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Setup custom OpenAPI documentation
    setup_openapi_customization(app)
    
    # Setup all middleware with environment-specific configuration
    middleware_config = PRODUCTION_MIDDLEWARE_CONFIG if not settings.debug else DEVELOPMENT_MIDDLEWARE_CONFIG
    setup_all_middleware(app, **middleware_config)
    
    # Include routers
    app.include_router(docs.router, tags=["Documentation"])
    app.include_router(health.router, tags=["Health Check"])
    app.include_router(ocr.router, tags=["OCR Processing"])
    app.include_router(tasks.router, tags=["Task Management"])
    app.include_router(files.router, prefix=settings.api_prefix, tags=["File Management"])
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )