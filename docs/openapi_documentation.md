# OCRFlux API OpenAPI Documentation

This document describes the comprehensive OpenAPI 3.0 documentation implementation for the OCRFlux API Service.

## Overview

The OCRFlux API Service provides complete OpenAPI 3.0 documentation with:

- **Interactive Documentation**: Swagger UI and ReDoc interfaces
- **Comprehensive Examples**: Real-world usage examples for all endpoints
- **Client Code Generation**: Support for generating client SDKs in multiple languages
- **Detailed Schema**: Complete request/response models with validation
- **Error Documentation**: Comprehensive error response examples
- **Performance Guidelines**: Best practices and optimization tips

## Documentation Endpoints

### Interactive Documentation

| Endpoint | Description | Use Case |
|----------|-------------|----------|
| `/docs` | Swagger UI | Interactive API testing and exploration |
| `/redoc` | ReDoc | Comprehensive API reference documentation |
| `/openapi.json` | OpenAPI Schema | Machine-readable API specification |
| `/api-info` | API Information | Service capabilities and metadata |
| `/schema-stats` | Schema Statistics | API metrics and component counts |

### Accessing Documentation

1. **Swagger UI** (Recommended for testing):
   ```
   http://localhost:8000/docs
   ```
   - Interactive interface for testing API endpoints
   - Built-in request/response examples
   - Direct API calls from the browser
   - Parameter validation and formatting

2. **ReDoc** (Recommended for reference):
   ```
   http://localhost:8000/redoc
   ```
   - Clean, comprehensive documentation layout
   - Detailed schema information
   - Code samples in multiple languages
   - Downloadable OpenAPI specification

3. **OpenAPI Schema** (For tooling integration):
   ```
   http://localhost:8000/openapi.json
   ```
   - Complete OpenAPI 3.0 JSON specification
   - Use with Postman, Insomnia, or other API tools
   - Generate client SDKs with OpenAPI generators
   - Validate requests/responses programmatically

## Key Features

### 1. Comprehensive Examples

The documentation includes detailed examples for all major use cases:

#### Single File Processing
```json
{
  "success": true,
  "file_name": "quarterly_report.pdf",
  "file_size": 2048576,
  "num_pages": 8,
  "document_text": "# Quarterly Report Q3 2024\n\n## Executive Summary...",
  "page_texts": {
    "0": "# Quarterly Report Q3 2024...",
    "1": "## Financial Highlights..."
  },
  "fallback_pages": [],
  "processing_time": 23.45,
  "created_at": "2024-01-15T14:30:45.123Z"
}
```

#### Batch Processing
```json
{
  "total_files": 5,
  "successful_files": 4,
  "failed_files": 1,
  "results": [
    {
      "success": true,
      "file_name": "invoice_001.pdf",
      "document_text": "# Invoice #INV-001..."
    }
  ],
  "total_processing_time": 52.1
}
```

#### Task Management
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 1.0,
  "result_available": true
}
```

### 2. Multi-Language Code Samples

#### Python Example
```python
import requests

def process_file(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/v1/parse',
            files={'file': f},
            data={'skip_cross_page_merge': False}
        )
    return response.json()

result = process_file('document.pdf')
print(result['document_text'])
```

#### JavaScript Example
```javascript
async function processFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('skip_cross_page_merge', false);
    
    const response = await fetch('/api/v1/parse', {
        method: 'POST',
        body: formData
    });
    
    return await response.json();
}
```

#### cURL Example
```bash
curl -X POST "http://localhost:8000/api/v1/parse" \
     -F "file=@document.pdf" \
     -F "skip_cross_page_merge=false"
```

### 3. Error Documentation

Comprehensive error response examples for all HTTP status codes:

- **400 Bad Request**: Invalid parameters or file format
- **413 Payload Too Large**: File size exceeds limits
- **422 Unprocessable Entity**: Unsupported file format
- **503 Service Unavailable**: Model not loaded or system overloaded

### 4. Performance Guidelines

The documentation includes detailed performance optimization tips:

#### File Size Optimization
- Use async endpoints for files > 10MB
- Compress PDFs without losing quality
- Use PNG for text-heavy images, JPEG for photos

#### Batch Processing
- Batch 3-7 small files for optimal throughput
- Avoid mixing large and small files
- Use async batch processing for total size > 50MB

#### Quality vs Speed
- `target_longest_image_dim=1024`: Balanced (recommended)
- `target_longest_image_dim=768`: Faster, lower quality
- `target_longest_image_dim=1536`: Slower, higher quality

### 5. Troubleshooting Guide

Common issues and solutions:

#### File Upload Issues
- **413 Payload Too Large**: Compress file or split into sections
- **422 Unprocessable Entity**: Check file format and corruption
- **Password-protected PDFs**: Remove password before upload

#### Processing Issues
- **503 Service Unavailable**: Check `/api/v1/health` endpoint
- **504 Gateway Timeout**: Use async processing for large files
- **Poor text quality**: Increase `target_longest_image_dim`

## Integration Examples

### 1. Web Application Integration

```html
<!DOCTYPE html>
<html>
<head>
    <title>OCR Document Processor</title>
</head>
<body>
    <input type="file" id="fileInput" accept=".pdf,.png,.jpg,.jpeg">
    <div id="result"></div>
    
    <script>
        document.getElementById('fileInput').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/api/v1/parse', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    document.getElementById('result').innerHTML = 
                        `<pre>${result.document_text}</pre>`;
                } catch (error) {
                    console.error('Processing failed:', error);
                }
            }
        });
    </script>
</body>
</html>
```

### 2. Microservice Integration

```python
# FastAPI microservice integration
from fastapi import FastAPI, UploadFile, File
import httpx

app = FastAPI()

@app.post("/process-document")
async def process_document(file: UploadFile = File(...)):
    async with httpx.AsyncClient() as client:
        files = {'file': (file.filename, file.file, file.content_type)}
        response = await client.post(
            'http://ocrflux-service:8000/api/v1/parse',
            files=files
        )
        return response.json()
```

### 3. Batch Processing Workflow

```python
import asyncio
import aiohttp
from pathlib import Path

async def process_document_folder(folder_path):
    """Process all documents in a folder asynchronously"""
    files = list(Path(folder_path).glob('*.pdf'))
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for file_path in files:
            task = process_single_file(session, file_path)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

async def process_single_file(session, file_path):
    """Process a single file asynchronously"""
    with open(file_path, 'rb') as f:
        data = aiohttp.FormData()
        data.add_field('file', f, filename=file_path.name)
        
        async with session.post(
            'http://localhost:8000/api/v1/parse-async',
            data=data
        ) as response:
            result = await response.json()
            task_id = result['task_id']
            
            # Poll for completion
            while True:
                async with session.get(
                    f'http://localhost:8000/api/v1/tasks/{task_id}'
                ) as status_response:
                    status = await status_response.json()
                    
                    if status['status'] == 'completed':
                        async with session.get(
                            f'http://localhost:8000/api/v1/tasks/{task_id}/result'
                        ) as result_response:
                            return await result_response.json()
                    elif status['status'] == 'failed':
                        raise Exception(f"Processing failed: {status['error_message']}")
                    
                    await asyncio.sleep(2)
```

## Client SDK Generation

The OpenAPI schema supports generating client SDKs in multiple languages:

### Using OpenAPI Generator

```bash
# Install OpenAPI Generator
npm install @openapitools/openapi-generator-cli -g

# Generate Python client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g python \
  -o ./python-client \
  --package-name ocrflux_client

# Generate JavaScript client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g javascript \
  -o ./js-client

# Generate Java client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g java \
  -o ./java-client \
  --package-name com.example.ocrflux
```

### Using Swagger Codegen

```bash
# Generate TypeScript client
swagger-codegen generate \
  -i http://localhost:8000/openapi.json \
  -l typescript-fetch \
  -o ./typescript-client

# Generate C# client
swagger-codegen generate \
  -i http://localhost:8000/openapi.json \
  -l csharp \
  -o ./csharp-client
```

## Testing with API Tools

### Postman Integration

1. Import the OpenAPI schema:
   - Open Postman
   - Click "Import" → "Link"
   - Enter: `http://localhost:8000/openapi.json`
   - Postman will create a collection with all endpoints

2. Environment setup:
   - Create a new environment
   - Add variable: `base_url` = `http://localhost:8000`
   - Use `{{base_url}}` in requests

### Insomnia Integration

1. Import specification:
   - Open Insomnia
   - Click "Create" → "Import From" → "URL"
   - Enter: `http://localhost:8000/openapi.json`

2. Test endpoints:
   - All endpoints will be available with proper schemas
   - Request/response examples included
   - Automatic validation

## Monitoring and Analytics

### Schema Statistics

Access detailed schema statistics at `/schema-stats`:

```json
{
  "schema_version": "3.0.0",
  "api_version": "1.0.0",
  "endpoints": {
    "total": 15,
    "methods": ["GET", "POST", "DELETE"],
    "tags": ["Documentation", "Health Check", "OCR Processing", "Task Management"]
  },
  "models": {
    "total": 25,
    "names": ["ProcessResult", "BatchProcessResult", "TaskStatus", "ErrorResponse"]
  },
  "examples": {
    "total": 12,
    "names": ["SingleFileSuccess", "BatchProcessSuccess", "TaskCompleted"]
  }
}
```

### API Information

Get comprehensive API metadata at `/api-info`:

```json
{
  "name": "OCRFlux API Service",
  "version": "1.0.0",
  "capabilities": {
    "file_formats": ["PDF", "PNG", "JPG", "JPEG"],
    "processing_modes": ["synchronous", "asynchronous", "batch"],
    "max_file_size": "100MB",
    "max_batch_size": 10
  },
  "endpoints": {
    "documentation": {
      "swagger_ui": "/docs",
      "redoc": "/redoc",
      "openapi_schema": "/openapi.json"
    }
  }
}
```

## Best Practices

### 1. Documentation Maintenance

- Keep examples up-to-date with API changes
- Test all code samples regularly
- Update performance guidelines based on real usage
- Maintain backward compatibility in schema versions

### 2. Client Development

- Use the OpenAPI schema for request validation
- Implement proper error handling for all status codes
- Follow the async processing patterns for large files
- Monitor API health before making requests

### 3. Integration Testing

- Test against the OpenAPI schema for validation
- Use the provided examples as test cases
- Implement retry logic with exponential backoff
- Monitor processing times and adjust parameters

## Conclusion

The OCRFlux API Service provides comprehensive OpenAPI 3.0 documentation that enables:

- **Easy Integration**: Clear examples and client SDK generation
- **Robust Error Handling**: Detailed error responses and troubleshooting
- **Performance Optimization**: Guidelines for optimal usage patterns
- **Developer Experience**: Interactive testing and comprehensive reference

The documentation is designed to support both quick prototyping and production deployment, with examples and guidelines for common integration patterns and use cases.