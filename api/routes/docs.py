"""
Documentation and OpenAPI schema endpoints
"""
from typing import Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from ..core.config import settings
from ..middleware.config import get_middleware_info

router = APIRouter(tags=["Documentation"])


@router.get(
    "/openapi.json",
    include_in_schema=False,
    summary="OpenAPI Schema",
    description="Get the complete OpenAPI 3.0 schema for this API"
)
async def get_openapi_schema(request: Request) -> Dict[str, Any]:
    """
    Get the complete OpenAPI 3.0 schema for this API.
    
    This endpoint returns the full OpenAPI specification including:
    - All endpoint definitions with parameters and responses
    - Data model schemas with examples
    - Authentication schemes (for future use)
    - Common response definitions
    - API usage guidelines and examples
    
    The schema can be used to:
    - Generate client SDKs in various programming languages
    - Import into API testing tools like Postman or Insomnia
    - Generate documentation in different formats
    - Validate API requests and responses
    """
    return request.app.openapi()


@router.get(
    "/docs",
    include_in_schema=False,
    summary="Swagger UI Documentation",
    description="Interactive API documentation using Swagger UI"
)
async def get_swagger_ui():
    """
    Interactive API documentation using Swagger UI.
    
    Provides a web-based interface to:
    - Browse all available endpoints
    - View request/response schemas and examples
    - Test API endpoints directly from the browser
    - Download the OpenAPI schema
    
    This is the recommended way to explore and test the API.
    """
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.app_name} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png"
    )


@router.get(
    "/redoc",
    include_in_schema=False,
    summary="ReDoc Documentation",
    description="API documentation using ReDoc"
)
async def get_redoc():
    """
    API documentation using ReDoc.
    
    Provides an alternative documentation interface with:
    - Clean, responsive design
    - Detailed schema information
    - Code samples in multiple languages
    - Downloadable OpenAPI schema
    
    ReDoc is particularly good for comprehensive API reference documentation.
    """
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{settings.app_name} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
        redoc_favicon_url="https://fastapi.tiangolo.com/img/favicon.png"
    )


@router.get(
    "/api-info",
    summary="API Information",
    description="Get general information about this API"
)
async def get_api_info():
    """
    Get general information about this API.
    
    Returns metadata about the API including version, capabilities,
    limits, and usage guidelines.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "OCR API service for extracting text from PDF and image files",
        "capabilities": {
            "file_formats": ["PDF", "PNG", "JPG", "JPEG"],
            "processing_modes": ["synchronous", "asynchronous", "batch"],
            "output_format": "Markdown",
            "max_file_size": f"{settings.max_file_size // (1024*1024)}MB",
            "max_batch_size": 10,
            "cross_page_merging": True,
            "retry_logic": True,
            "health_monitoring": True,
            "task_management": True
        },
        "limits": {
            "max_file_size_bytes": settings.max_file_size,
            "max_batch_files": 10,
            "supported_extensions": settings.allowed_extensions,
            "task_timeout_seconds": settings.task_timeout,
            "max_concurrent_tasks": settings.max_concurrent_tasks
        },
        "endpoints": {
            "documentation": {
                "swagger_ui": "/docs",
                "redoc": "/redoc",
                "openapi_schema": "/openapi.json"
            },
            "health": {
                "comprehensive": "/api/v1/health",
                "simple": "/api/v1/health/simple",
                "model": "/api/v1/health/model",
                "system": "/api/v1/health/system"
            },
            "processing": {
                "single_sync": "/api/v1/parse",
                "single_async": "/api/v1/parse-async",
                "batch_sync": "/api/v1/batch",
                "batch_async": "/api/v1/batch-async"
            },
            "tasks": {
                "status": "/api/v1/tasks/{task_id}",
                "result": "/api/v1/tasks/{task_id}/result",
                "cancel": "/api/v1/tasks/{task_id}",
                "queue_stats": "/api/v1/tasks"
            }
        },
        "usage_guidelines": {
            "small_files": "Use synchronous endpoints for files < 10MB",
            "large_files": "Use asynchronous endpoints for files > 10MB",
            "batch_processing": "Batch multiple small files for better throughput",
            "monitoring": "Use health endpoints to monitor service status",
            "error_handling": "Check success field and error_type for proper error handling"
        },
        "examples": {
            "curl_single_file": 'curl -X POST "http://localhost:8000/api/v1/parse" -F "file=@document.pdf"',
            "curl_batch": 'curl -X POST "http://localhost:8000/api/v1/batch" -F "files=@doc1.pdf" -F "files=@doc2.pdf"',
            "curl_async": 'curl -X POST "http://localhost:8000/api/v1/parse-async" -F "file=@large_document.pdf"',
            "curl_health": 'curl -X GET "http://localhost:8000/api/v1/health"'
        }
    }


@router.get(
    "/schema-stats",
    summary="Schema Statistics",
    description="Get statistics about the OpenAPI schema"
)
async def get_schema_stats(request: Request):
    """
    Get statistics about the OpenAPI schema.
    
    Returns information about the number of endpoints, models,
    and other schema components for API analytics.
    """
    schema = request.app.openapi()
    
    # Count endpoints
    endpoint_count = 0
    methods = set()
    tags = set()
    
    for path_info in schema.get("paths", {}).values():
        for method, operation in path_info.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                endpoint_count += 1
                methods.add(method.upper())
                if "tags" in operation:
                    tags.update(operation["tags"])
    
    # Count models
    models = schema.get("components", {}).get("schemas", {})
    model_count = len(models)
    
    # Count examples
    examples = schema.get("components", {}).get("examples", {})
    example_count = len(examples)
    
    return {
        "schema_version": "3.0.0",
        "api_version": schema.get("info", {}).get("version"),
        "endpoints": {
            "total": endpoint_count,
            "methods": sorted(list(methods)),
            "tags": sorted(list(tags))
        },
        "models": {
            "total": model_count,
            "names": sorted(list(models.keys()))
        },
        "examples": {
            "total": example_count,
            "names": sorted(list(examples.keys()))
        },
        "components": {
            "schemas": len(schema.get("components", {}).get("schemas", {})),
            "responses": len(schema.get("components", {}).get("responses", {})),
            "parameters": len(schema.get("components", {}).get("parameters", {})),
            "examples": len(schema.get("components", {}).get("examples", {})),
            "security_schemes": len(schema.get("components", {}).get("securitySchemes", {}))
        }
    }


@router.get(
    "/middleware-info",
    summary="Middleware Information",
    description="Get information about configured middleware stack"
)
async def get_middleware_information():
    """
    Get detailed information about the configured middleware stack.
    
    Returns information about:
    - Middleware execution order and configuration
    - Enabled features and capabilities
    - Security and validation settings
    - Rate limiting and size restrictions
    
    Useful for understanding the request processing pipeline
    and debugging middleware-related issues.
    """
    return get_middleware_info()