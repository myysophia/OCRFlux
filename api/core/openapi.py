"""
OpenAPI schema customization and documentation enhancements
"""
from typing import Dict, Any, Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with enhanced documentation.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Enhanced OpenAPI schema dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    # Generate base schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers,
        tags=app.openapi_tags
    )
    
    # Add custom extensions and enhancements
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png",
        "altText": "OCRFlux API Logo"
    }
    
    # Add security schemes (for future authentication)
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication (not currently required)"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for authentication (not currently required)"
        }
    }
    
    # Add common response examples
    _add_common_responses(openapi_schema)
    
    # Add request/response examples
    _enhance_examples(openapi_schema)
    
    # Add custom extensions
    _add_custom_extensions(openapi_schema)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _add_common_responses(schema: Dict[str, Any]) -> None:
    """Add common response definitions to the schema."""
    if "components" not in schema:
        schema["components"] = {}
    
    if "responses" not in schema["components"]:
        schema["components"]["responses"] = {}
    
    # Common error responses
    schema["components"]["responses"].update({
        "BadRequest": {
            "description": "Bad Request - Invalid input parameters",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "success": False,
                        "error_type": "validation_error",
                        "message": "Invalid input parameters",
                        "details": [
                            {
                                "field": "file",
                                "message": "File is required",
                                "code": "MISSING_FIELD"
                            }
                        ],
                        "timestamp": "2024-01-15T14:30:45.123Z"
                    }
                }
            }
        },
        "Unauthorized": {
            "description": "Unauthorized - Authentication required",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "success": False,
                        "error_type": "authentication_error",
                        "message": "Authentication required",
                        "timestamp": "2024-01-15T14:30:45.123Z"
                    }
                }
            }
        },
        "Forbidden": {
            "description": "Forbidden - Insufficient permissions",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "success": False,
                        "error_type": "authorization_error",
                        "message": "Insufficient permissions",
                        "timestamp": "2024-01-15T14:30:45.123Z"
                    }
                }
            }
        },
        "NotFound": {
            "description": "Not Found - Resource does not exist",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "success": False,
                        "error_type": "not_found_error",
                        "message": "Resource not found",
                        "timestamp": "2024-01-15T14:30:45.123Z"
                    }
                }
            }
        },
        "PayloadTooLarge": {
            "description": "Payload Too Large - File size exceeds limit",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/FileErrorResponse"},
                    "example": {
                        "success": False,
                        "error_type": "file_error",
                        "message": "File size exceeds maximum limit of 100MB",
                        "filename": "large_document.pdf",
                        "file_size": 157286400,
                        "timestamp": "2024-01-15T14:30:45.123Z"
                    }
                }
            }
        },
        "UnprocessableEntity": {
            "description": "Unprocessable Entity - Invalid file format",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/FileErrorResponse"},
                    "example": {
                        "success": False,
                        "error_type": "file_error",
                        "message": "File format not supported",
                        "filename": "document.txt",
                        "details": [
                            {
                                "message": "Only PDF, PNG, JPG, and JPEG files are supported",
                                "code": "UNSUPPORTED_FORMAT"
                            }
                        ],
                        "timestamp": "2024-01-15T14:30:45.123Z"
                    }
                }
            }
        },
        "InternalServerError": {
            "description": "Internal Server Error - Unexpected server error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/SystemErrorResponse"},
                    "example": {
                        "success": False,
                        "error_type": "system_error",
                        "message": "An internal error occurred",
                        "request_id": "req_550e8400-e29b-41d4-a716-446655440000",
                        "timestamp": "2024-01-15T14:30:45.123Z"
                    }
                }
            }
        },
        "ServiceUnavailable": {
            "description": "Service Unavailable - Service temporarily unavailable",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ModelErrorResponse"},
                    "example": {
                        "success": False,
                        "error_type": "model_error",
                        "message": "OCR model is not loaded and ready for processing",
                        "model_status": "loading",
                        "timestamp": "2024-01-15T14:30:45.123Z"
                    }
                }
            }
        },
        "GatewayTimeout": {
            "description": "Gateway Timeout - Request processing timeout",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "success": False,
                        "error_type": "timeout_error",
                        "message": "Request processing timeout",
                        "timestamp": "2024-01-15T14:30:45.123Z"
                    }
                }
            }
        }
    })


def _enhance_examples(schema: Dict[str, Any]) -> None:
    """Add enhanced examples to schema components."""
    # Add example files for documentation
    if "components" not in schema:
        schema["components"] = {}
    
    if "examples" not in schema["components"]:
        schema["components"]["examples"] = {}
    
    schema["components"]["examples"].update({
        "SingleFileSuccess": {
            "summary": "Successful single file processing",
            "description": "Example of a successful PDF processing result with complete document structure",
            "value": {
                "success": True,
                "file_name": "quarterly_report.pdf",
                "file_size": 2048576,
                "num_pages": 8,
                "document_text": "# Quarterly Report Q3 2024\n\n## Executive Summary\n\nThis quarter showed exceptional growth across all business segments, with revenue increasing by 25% and profit margins expanding significantly.\n\n## Financial Highlights\n\n| Metric | Q2 2024 | Q3 2024 | Change |\n|--------|---------|---------|--------|\n| Revenue | $1.2M | $1.5M | +25% |\n| Profit | $240K | $320K | +33% |\n| Customers | 1,200 | 1,450 | +21% |\n\n## Key Achievements\n\n- **Product Innovation**: Launched new AI-powered analytics suite\n- **Market Expansion**: Successfully entered 3 new geographic markets\n- **Customer Satisfaction**: Achieved 94% satisfaction rating (up from 87%)\n- **Team Growth**: Expanded engineering team by 40%\n\n## Looking Forward\n\nQ4 projections indicate continued strong performance with expected revenue of $1.8M.",
                "page_texts": {
                    "0": "# Quarterly Report Q3 2024\n\n## Executive Summary\n\nThis quarter showed exceptional growth across all business segments...",
                    "1": "## Financial Highlights\n\n| Metric | Q2 2024 | Q3 2024 | Change |\n|--------|---------|---------|--------|\n| Revenue | $1.2M | $1.5M | +25% |",
                    "2": "## Key Achievements\n\n- **Product Innovation**: Launched new AI-powered analytics suite\n- **Market Expansion**: Successfully entered 3 new geographic markets",
                    "3": "## Looking Forward\n\nQ4 projections indicate continued strong performance with expected revenue of $1.8M."
                },
                "fallback_pages": [],
                "processing_time": 23.45,
                "created_at": "2024-01-15T14:30:45.123Z",
                "error_message": None
            }
        },
        "SingleFileWithFallbacks": {
            "summary": "Processing with some page failures",
            "description": "Example where most pages processed successfully but some required fallback methods",
            "value": {
                "success": True,
                "file_name": "scanned_contract.pdf",
                "file_size": 1536000,
                "num_pages": 12,
                "document_text": "# Service Agreement\n\n**Effective Date:** January 1, 2024\n**Parties:** Company A and Company B\n\n## Terms and Conditions\n\n### 1. Scope of Work\nThe contractor agrees to provide consulting services...\n\n### 2. Payment Terms\nPayment shall be made within 30 days of invoice receipt.\n\n[Note: Pages 7 and 11 had reduced quality due to scanning artifacts]",
                "page_texts": {
                    "0": "# Service Agreement\n\n**Effective Date:** January 1, 2024",
                    "1": "## Terms and Conditions\n\n### 1. Scope of Work",
                    "6": "[Partial text due to poor scan quality]",
                    "10": "[Partial text due to poor scan quality]"
                },
                "fallback_pages": [7, 11],
                "processing_time": 45.2,
                "created_at": "2024-01-15T14:35:22.456Z",
                "error_message": None
            }
        },
        "SingleFileError": {
            "summary": "Failed file processing",
            "description": "Example of a file that failed to process due to corruption or encryption",
            "value": {
                "success": False,
                "file_name": "encrypted_document.pdf",
                "file_size": 512000,
                "num_pages": 0,
                "document_text": "",
                "page_texts": {},
                "fallback_pages": [],
                "processing_time": 2.1,
                "created_at": "2024-01-15T14:40:10.789Z",
                "error_message": "File is password-protected and cannot be processed. Please provide an unencrypted version."
            }
        },
        "BatchProcessSuccess": {
            "summary": "Successful batch processing",
            "description": "Example of batch processing multiple files with mixed results showing typical business documents",
            "value": {
                "total_files": 5,
                "successful_files": 4,
                "failed_files": 1,
                "results": [
                    {
                        "success": True,
                        "file_name": "invoice_001.pdf",
                        "file_size": 256000,
                        "num_pages": 1,
                        "document_text": "# Invoice #INV-001\n\n**Date:** January 15, 2024\n**Due Date:** February 14, 2024\n**Amount:** $1,250.00\n\n## Billing Details\n\n**Bill To:**\nAcme Corporation\n123 Business St\nCity, State 12345\n\n## Items\n\n| Description | Quantity | Rate | Amount |\n|-------------|----------|------|--------|\n| Consulting Services | 10 hours | $125.00 | $1,250.00 |\n\n**Total: $1,250.00**",
                        "page_texts": {"0": "# Invoice #INV-001\n\n**Date:** January 15, 2024..."},
                        "fallback_pages": [],
                        "processing_time": 5.2,
                        "created_at": "2024-01-15T14:35:22.456Z",
                        "error_message": None
                    },
                    {
                        "success": True,
                        "file_name": "contract_template.pdf",
                        "file_size": 1024000,
                        "num_pages": 4,
                        "document_text": "# Service Agreement\n\n**Effective Date:** January 1, 2024\n**Term:** 12 months\n\n## Parties\n\n**Client:** Acme Corporation\n**Service Provider:** Professional Services LLC\n\n## Terms and Conditions\n\n### 1. Scope of Work\nThe contractor agrees to provide consulting services including:\n- Strategic planning\n- Process optimization\n- Technology assessment\n\n### 2. Payment Terms\nPayment shall be made within 30 days of invoice receipt.\n\n### 3. Confidentiality\nBoth parties agree to maintain confidentiality...",
                        "page_texts": {
                            "0": "# Service Agreement\n\n**Effective Date:** January 1, 2024",
                            "1": "## Terms and Conditions\n\n### 1. Scope of Work",
                            "2": "### 2. Payment Terms\nPayment shall be made within 30 days",
                            "3": "### 3. Confidentiality\nBoth parties agree to maintain confidentiality"
                        },
                        "fallback_pages": [],
                        "processing_time": 12.8,
                        "created_at": "2024-01-15T14:35:22.456Z",
                        "error_message": None
                    },
                    {
                        "success": True,
                        "file_name": "receipt_scan.jpg",
                        "file_size": 512000,
                        "num_pages": 1,
                        "document_text": "# Receipt\n\n**Store:** Tech Supplies Inc.\n**Date:** January 14, 2024\n**Time:** 2:45 PM\n\n## Items Purchased\n\n- Laptop Stand: $45.99\n- USB Cable: $12.99\n- Mouse Pad: $8.99\n\n**Subtotal:** $67.97\n**Tax:** $5.44\n**Total:** $73.41\n\n**Payment Method:** Credit Card ****1234\n**Transaction ID:** TXN789456123",
                        "page_texts": {"0": "# Receipt\n\n**Store:** Tech Supplies Inc.\n**Date:** January 14, 2024..."},
                        "fallback_pages": [],
                        "processing_time": 3.1,
                        "created_at": "2024-01-15T14:35:22.456Z",
                        "error_message": None
                    },
                    {
                        "success": True,
                        "file_name": "presentation_slides.pdf",
                        "file_size": 2048000,
                        "num_pages": 15,
                        "document_text": "# Q4 Business Review\n\n## Agenda\n\n1. Performance Overview\n2. Key Metrics\n3. Challenges & Opportunities\n4. Q1 Planning\n\n## Performance Overview\n\n- Revenue exceeded targets by 12%\n- Customer acquisition up 25%\n- Product launches successful\n\n## Key Metrics\n\n| Metric | Target | Actual | Variance |\n|--------|--------|--------|----------|\n| Revenue | $2.0M | $2.24M | +12% |\n| New Customers | 400 | 500 | +25% |\n| Retention Rate | 85% | 89% | +4% |",
                        "page_texts": {
                            "0": "# Q4 Business Review\n\n## Agenda",
                            "1": "## Performance Overview",
                            "2": "## Key Metrics"
                        },
                        "fallback_pages": [8, 12],
                        "processing_time": 28.7,
                        "created_at": "2024-01-15T14:35:22.456Z",
                        "error_message": None
                    },
                    {
                        "success": False,
                        "file_name": "corrupted_file.pdf",
                        "file_size": 0,
                        "num_pages": 0,
                        "document_text": "",
                        "page_texts": {},
                        "fallback_pages": [],
                        "processing_time": 1.1,
                        "created_at": "2024-01-15T14:35:22.456Z",
                        "error_message": "File appears to be corrupted or truncated. Unable to read PDF structure."
                    }
                ],
                "total_processing_time": 52.1,
                "created_at": "2024-01-15T14:35:22.456Z"
            }
        },
        "TaskSubmitted": {
            "summary": "Task successfully submitted",
            "description": "Example response when submitting an asynchronous task for a large document",
            "value": {
                "success": True,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "estimated_completion": "2024-01-15T15:00:00.000Z",
                "message": "Single file processing task submitted successfully and is queued for processing"
            }
        },
        "BatchTaskSubmitted": {
            "summary": "Batch task successfully submitted",
            "description": "Example response when submitting multiple files for asynchronous processing",
            "value": {
                "success": True,
                "task_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "status": "pending",
                "estimated_completion": "2024-01-15T15:10:00.000Z",
                "message": "Batch processing task submitted successfully for 7 files"
            }
        },
        "TaskPending": {
            "summary": "Task waiting in queue",
            "description": "Example task status when task is waiting to be processed",
            "value": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "progress": 0.0,
                "created_at": "2024-01-15T14:30:00.000Z",
                "started_at": None,
                "completed_at": None,
                "estimated_completion": "2024-01-15T15:00:00.000Z",
                "processing_time": None,
                "error_message": None,
                "result_available": False
            }
        },
        "TaskRunning": {
            "summary": "Task currently processing",
            "description": "Example task status when processing is in progress",
            "value": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "running",
                "progress": 0.65,
                "created_at": "2024-01-15T14:30:00.000Z",
                "started_at": "2024-01-15T14:30:15.000Z",
                "completed_at": None,
                "estimated_completion": "2024-01-15T14:31:30.000Z",
                "processing_time": None,
                "error_message": None,
                "result_available": False
            }
        },
        "TaskCompleted": {
            "summary": "Task completed successfully",
            "description": "Example task status when processing is complete and results are available",
            "value": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "progress": 1.0,
                "created_at": "2024-01-15T14:30:00.000Z",
                "started_at": "2024-01-15T14:30:15.000Z",
                "completed_at": "2024-01-15T14:30:45.123Z",
                "estimated_completion": "2024-01-15T14:31:30.000Z",
                "processing_time": 30.123,
                "error_message": None,
                "result_available": True
            }
        },
        "TaskFailed": {
            "summary": "Task failed with error",
            "description": "Example task status when processing failed",
            "value": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "failed",
                "progress": 0.3,
                "created_at": "2024-01-15T14:30:00.000Z",
                "started_at": "2024-01-15T14:30:15.000Z",
                "completed_at": "2024-01-15T14:30:25.456Z",
                "estimated_completion": None,
                "processing_time": 10.456,
                "error_message": "Model inference failed due to insufficient GPU memory. Please try again later.",
                "result_available": False
            }
        },
        "HealthySystem": {
            "summary": "System healthy",
            "description": "Example health check response when all systems are operating normally",
            "value": {
                "status": "healthy",
                "model_loaded": True,
                "model_path": "/models/OCRFlux-3B",
                "memory_usage": {
                    "used_gb": 12.5,
                    "total_gb": 32.0,
                    "percentage": 39.1
                },
                "uptime": 86400.5,
                "version": "1.0.0",
                "active_tasks": 2,
                "queue_size": 5,
                "timestamp": "2024-01-15T14:30:45.123Z"
            }
        },
        "DegradedSystem": {
            "summary": "System degraded",
            "description": "Example health check response when system is experiencing issues but still functional",
            "value": {
                "status": "degraded",
                "model_loaded": True,
                "model_path": "/models/OCRFlux-3B",
                "memory_usage": {
                    "used_gb": 28.2,
                    "total_gb": 32.0,
                    "percentage": 88.1
                },
                "uptime": 3600.2,
                "version": "1.0.0",
                "active_tasks": 8,
                "queue_size": 15,
                "timestamp": "2024-01-15T14:30:45.123Z",
                "warnings": ["High memory usage", "Queue backlog detected"]
            }
        },
        "UnhealthySystem": {
            "summary": "System unhealthy",
            "description": "Example health check response when system is not functioning properly",
            "value": {
                "status": "unhealthy",
                "model_loaded": False,
                "model_path": "/models/OCRFlux-3B",
                "memory_usage": {
                    "used_gb": 2.1,
                    "total_gb": 32.0,
                    "percentage": 6.6
                },
                "uptime": 120.5,
                "version": "1.0.0",
                "active_tasks": 0,
                "queue_size": 0,
                "timestamp": "2024-01-15T14:30:45.123Z",
                "errors": ["Model failed to load", "CUDA out of memory during initialization"]
            }
        }
    })


def _add_custom_extensions(schema: Dict[str, Any]) -> None:
    """Add custom OpenAPI extensions."""
    # Add API usage guidelines
    schema["info"]["x-api-guidelines"] = {
        "rate_limiting": "No rate limits currently enforced, but consider implementing for production use",
        "file_size_limits": "Maximum file size is 100MB per file",
        "batch_limits": "Maximum 10 files per batch request",
        "supported_formats": ["PDF", "PNG", "JPG", "JPEG"],
        "async_processing": "Use async endpoints for files larger than 10MB or batches with more than 3 files"
    }
    
    # Add comprehensive code samples
    schema["info"]["x-code-samples"] = {
        "python": {
            "client_library": "requests",
            "single_file": """
import requests
import json

# Single file processing (synchronous)
def process_single_file(file_path, api_url="http://localhost:8000"):
    with open(file_path, 'rb') as f:
        response = requests.post(
            f'{api_url}/api/v1/parse',
            files={'file': f},
            data={
                'skip_cross_page_merge': False,
                'max_page_retries': 1,
                'target_longest_image_dim': 1024
            }
        )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result['success']}")
        print(f"Pages: {result['num_pages']}")
        print(f"Processing time: {result['processing_time']:.2f}s")
        return result['document_text']
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Usage
markdown_text = process_single_file('document.pdf')
""",
            "async_processing": """
import requests
import time
import json

def submit_async_task(file_path, api_url="http://localhost:8000"):
    \"\"\"Submit file for async processing\"\"\"
    with open(file_path, 'rb') as f:
        response = requests.post(
            f'{api_url}/api/v1/parse-async',
            files={'file': f},
            data={'skip_cross_page_merge': False}
        )
    
    if response.status_code == 200:
        return response.json()['task_id']
    else:
        raise Exception(f"Failed to submit task: {response.text}")

def check_task_status(task_id, api_url="http://localhost:8000"):
    \"\"\"Check task status\"\"\"
    response = requests.get(f'{api_url}/api/v1/tasks/{task_id}')
    return response.json()

def get_task_result(task_id, api_url="http://localhost:8000"):
    \"\"\"Get task result when completed\"\"\"
    response = requests.get(f'{api_url}/api/v1/tasks/{task_id}/result')
    return response.json()

def process_file_async(file_path, api_url="http://localhost:8000"):
    \"\"\"Complete async processing workflow\"\"\"
    # Submit task
    task_id = submit_async_task(file_path, api_url)
    print(f"Task submitted: {task_id}")
    
    # Poll for completion
    while True:
        status = check_task_status(task_id, api_url)
        print(f"Status: {status['status']} ({status['progress']*100:.1f}%)")
        
        if status['status'] == 'completed':
            result = get_task_result(task_id, api_url)
            return result
        elif status['status'] == 'failed':
            raise Exception(f"Task failed: {status['error_message']}")
        
        time.sleep(2)  # Wait 2 seconds before next check

# Usage
result = process_file_async('large_document.pdf')
""",
            "batch_processing": """
import requests
from pathlib import Path

def process_batch_files(file_paths, api_url="http://localhost:8000"):
    \"\"\"Process multiple files in batch\"\"\"
    files = []
    try:
        # Prepare files for upload
        for file_path in file_paths:
            files.append(('files', open(file_path, 'rb')))
        
        # Submit batch request
        response = requests.post(
            f'{api_url}/api/v1/batch',
            files=files,
            data={
                'skip_cross_page_merge': False,
                'max_page_retries': 2
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Processed {result['successful_files']}/{result['total_files']} files")
            return result
        else:
            print(f"Batch processing failed: {response.text}")
            return None
    
    finally:
        # Close all file handles
        for _, file_handle in files:
            file_handle.close()

# Usage
file_list = ['doc1.pdf', 'doc2.pdf', 'image1.png']
batch_result = process_batch_files(file_list)
"""
        },
        "javascript": {
            "client_library": "fetch",
            "single_file": """
// Single file processing with error handling
async function processSingleFile(file, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('skip_cross_page_merge', options.skipCrossPageMerge || false);
    formData.append('max_page_retries', options.maxPageRetries || 1);
    formData.append('target_longest_image_dim', options.targetImageDim || 1024);
    
    try {
        const response = await fetch('/api/v1/parse', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(`Processing failed: ${error.message}`);
        }
        
        const result = await response.json();
        console.log(`Processed ${result.num_pages} pages in ${result.processing_time.toFixed(2)}s`);
        return result.document_text;
        
    } catch (error) {
        console.error('Error processing file:', error);
        throw error;
    }
}

// Usage with file input
document.getElementById('fileInput').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        try {
            const markdown = await processSingleFile(file);
            document.getElementById('output').textContent = markdown;
        } catch (error) {
            document.getElementById('error').textContent = error.message;
        }
    }
});
""",
            "async_processing": """
// Async processing with status polling
class OCRClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }
    
    async submitAsyncTask(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        Object.entries(options).forEach(([key, value]) => {
            formData.append(key, value);
        });
        
        const response = await fetch(`${this.baseUrl}/api/v1/parse-async`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Failed to submit task: ${response.statusText}`);
        }
        
        const result = await response.json();
        return result.task_id;
    }
    
    async checkTaskStatus(taskId) {
        const response = await fetch(`${this.baseUrl}/api/v1/tasks/${taskId}`);
        return await response.json();
    }
    
    async getTaskResult(taskId) {
        const response = await fetch(`${this.baseUrl}/api/v1/tasks/${taskId}/result`);
        return await response.json();
    }
    
    async processFileAsync(file, options = {}, onProgress = null) {
        const taskId = await this.submitAsyncTask(file, options);
        console.log(`Task submitted: ${taskId}`);
        
        return new Promise((resolve, reject) => {
            const pollInterval = setInterval(async () => {
                try {
                    const status = await this.checkTaskStatus(taskId);
                    
                    if (onProgress) {
                        onProgress(status);
                    }
                    
                    if (status.status === 'completed') {
                        clearInterval(pollInterval);
                        const result = await this.getTaskResult(taskId);
                        resolve(result);
                    } else if (status.status === 'failed') {
                        clearInterval(pollInterval);
                        reject(new Error(status.error_message));
                    }
                } catch (error) {
                    clearInterval(pollInterval);
                    reject(error);
                }
            }, 2000);
        });
    }
}

// Usage
const client = new OCRClient();
const fileInput = document.getElementById('fileInput');

fileInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        try {
            const result = await client.processFileAsync(
                file,
                { skip_cross_page_merge: false },
                (status) => {
                    console.log(`Progress: ${(status.progress * 100).toFixed(1)}%`);
                }
            );
            console.log('Processing complete:', result);
        } catch (error) {
            console.error('Processing failed:', error);
        }
    }
});
"""
        },
        "curl": {
            "basic_usage": """
# Single file processing
curl -X POST "http://localhost:8000/api/v1/parse" \\
     -F "file=@document.pdf" \\
     -F "skip_cross_page_merge=false" \\
     -F "max_page_retries=1"

# Batch processing
curl -X POST "http://localhost:8000/api/v1/batch" \\
     -F "files=@doc1.pdf" \\
     -F "files=@doc2.pdf" \\
     -F "files=@image1.png" \\
     -F "skip_cross_page_merge=false"

# Health check
curl -X GET "http://localhost:8000/api/v1/health"
""",
            "async_workflow": """
# Submit async task
TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/parse-async" \\
     -F "file=@large_document.pdf" \\
     -F "skip_cross_page_merge=false" | jq -r '.task_id')

echo "Task ID: $TASK_ID"

# Poll task status
while true; do
    STATUS=$(curl -s "http://localhost:8000/api/v1/tasks/$TASK_ID" | jq -r '.status')
    PROGRESS=$(curl -s "http://localhost:8000/api/v1/tasks/$TASK_ID" | jq -r '.progress')
    
    echo "Status: $STATUS, Progress: $(echo "$PROGRESS * 100" | bc -l | cut -d. -f1)%"
    
    if [ "$STATUS" = "completed" ]; then
        echo "Task completed! Getting results..."
        curl -s "http://localhost:8000/api/v1/tasks/$TASK_ID/result" | jq '.document_text'
        break
    elif [ "$STATUS" = "failed" ]; then
        echo "Task failed!"
        curl -s "http://localhost:8000/api/v1/tasks/$TASK_ID" | jq '.error_message'
        break
    fi
    
    sleep 2
done
""",
            "error_handling": """
# Example with error handling and response parsing
process_file() {
    local file="$1"
    local response
    local status_code
    
    # Make request and capture both response and status code
    response=$(curl -s -w "\\n%{http_code}" -X POST "http://localhost:8000/api/v1/parse" \\
        -F "file=@$file" \\
        -F "skip_cross_page_merge=false")
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    case $status_code in
        200)
            echo "Success! Processing completed."
            echo "$body" | jq '.document_text'
            ;;
        400)
            echo "Bad request - check file format and parameters"
            echo "$body" | jq '.message'
            ;;
        413)
            echo "File too large - maximum size is 100MB"
            ;;
        422)
            echo "Unsupported file format - use PDF, PNG, JPG, or JPEG"
            ;;
        503)
            echo "Service unavailable - model not loaded or system overloaded"
            ;;
        *)
            echo "Unexpected error (HTTP $status_code)"
            echo "$body"
            ;;
    esac
}

# Usage
process_file "document.pdf"
"""
        }
    }
    
    # Add comprehensive performance and usage guidelines
    schema["info"]["x-performance-tips"] = {
        "file_size_optimization": [
            "Use async endpoints for files larger than 10MB to avoid request timeouts",
            "Compress large PDF files before upload if possible (without losing quality)",
            "For images, use PNG format for text-heavy content, JPEG for photos with text"
        ],
        "batch_processing": [
            "Batch 3-7 small files together for optimal throughput",
            "Avoid mixing very large and very small files in the same batch",
            "Use async batch processing for batches with total size > 50MB"
        ],
        "quality_vs_speed": [
            "target_longest_image_dim=1024: Balanced speed and quality (recommended)",
            "target_longest_image_dim=768: Faster processing, slightly lower quality",
            "target_longest_image_dim=1536: Slower processing, higher quality for complex documents",
            "target_longest_image_dim=2048: Maximum quality for high-resolution scanned documents"
        ],
        "processing_options": [
            "Enable cross-page merging (default) for better document structure and table handling",
            "Disable cross-page merging for independent page processing or faster results",
            "Set max_page_retries=2-3 for unreliable documents or network conditions",
            "Use image_rotation for scanned documents that may be rotated"
        ],
        "system_monitoring": [
            "Check /api/v1/health before submitting large batches",
            "Monitor task queue size to avoid overloading the system",
            "Use async processing during peak hours to maintain responsiveness"
        ],
        "error_handling": [
            "Always check the 'success' field in responses before processing results",
            "Handle partial failures in batch processing gracefully",
            "Implement exponential backoff for retrying failed requests",
            "Check 'fallback_pages' array for pages that may have reduced quality"
        ]
    }
    
    # Add troubleshooting guide
    schema["info"]["x-troubleshooting"] = {
        "common_errors": {
            "413_payload_too_large": {
                "description": "File size exceeds 100MB limit",
                "solutions": [
                    "Compress the PDF file using a PDF optimizer",
                    "Split large documents into smaller sections",
                    "For images, reduce resolution while maintaining text readability"
                ]
            },
            "422_unprocessable_entity": {
                "description": "File format not supported or file corrupted",
                "solutions": [
                    "Ensure file extension is .pdf, .png, .jpg, or .jpeg",
                    "Try opening the file in another application to verify it's not corrupted",
                    "For password-protected PDFs, remove the password before uploading"
                ]
            },
            "503_service_unavailable": {
                "description": "OCR model not loaded or system overloaded",
                "solutions": [
                    "Wait a few minutes and try again",
                    "Check system health at /api/v1/health",
                    "Use async processing to avoid blocking requests"
                ]
            },
            "504_gateway_timeout": {
                "description": "Processing took too long and timed out",
                "solutions": [
                    "Use async processing for large or complex documents",
                    "Reduce target_longest_image_dim for faster processing",
                    "Split large documents into smaller sections"
                ]
            }
        },
        "quality_issues": {
            "poor_text_extraction": [
                "Increase target_longest_image_dim for higher resolution processing",
                "Ensure document images are high quality and well-lit",
                "Check if document is rotated and use image_rotation parameter",
                "For scanned documents, ensure they are scanned at 300+ DPI"
            ],
            "missing_tables": [
                "Enable cross-page merging (default) for better table detection",
                "Ensure table borders are clear in the source document",
                "Try increasing target_longest_image_dim for complex tables"
            ],
            "incomplete_pages": [
                "Check the fallback_pages array in the response",
                "Increase max_page_retries for unreliable processing",
                "Verify the source document pages are not corrupted"
            ]
        }
    }
    
    # Add integration examples
    schema["info"]["x-integration-examples"] = {
        "web_application": {
            "description": "Integrate OCR processing into a web application",
            "use_cases": [
                "Document management systems",
                "Invoice processing workflows",
                "Content digitization platforms",
                "Automated data extraction pipelines"
            ]
        },
        "microservices": {
            "description": "Use as a microservice in a larger architecture",
            "patterns": [
                "Event-driven processing with message queues",
                "Batch processing workflows",
                "Real-time document analysis APIs",
                "Content search and indexing systems"
            ]
        },
        "automation": {
            "description": "Automate document processing workflows",
            "scenarios": [
                "Scheduled batch processing of document folders",
                "Email attachment processing",
                "Cloud storage integration (S3, Google Drive, etc.)",
                "Webhook-triggered processing"
            ]
        }
    }


def setup_openapi_customization(app: FastAPI) -> None:
    """
    Set up custom OpenAPI schema generation for the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    def custom_openapi():
        return custom_openapi_schema(app)
    
    app.openapi = custom_openapi