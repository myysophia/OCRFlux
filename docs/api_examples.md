# OCRFlux API - Usage Examples

This document provides comprehensive examples of how to use the OCRFlux API service for various OCR processing tasks.

## Table of Contents

- [Authentication](#authentication)
- [Single File Processing](#single-file-processing)
- [Batch Processing](#batch-processing)
- [Asynchronous Processing](#asynchronous-processing)
- [Health Monitoring](#health-monitoring)
- [Error Handling](#error-handling)
- [Client Libraries](#client-libraries)
- [Advanced Usage](#advanced-usage)

## Authentication

Currently, the OCRFlux API does not require authentication for development environments. For production deployments, consider implementing API key authentication or OAuth2.

```bash
# No authentication required for basic usage
curl -X GET "http://localhost:8000/api/v1/health"
```

## Single File Processing

### Process a PDF Document

```bash
# Basic PDF processing
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"

# PDF processing with options
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "skip_cross_page_merge=false" \
  -F "max_page_retries=2"
```

**Response:**
```json
{
  "success": true,
  "file_name": "document.pdf",
  "file_path": "/tmp/ocrflux/document_abc123.pdf",
  "num_pages": 3,
  "document_text": "# Document Title\n\nThis is the extracted text...",
  "page_texts": {
    "0": "# Document Title\n\nFirst page content...",
    "1": "Second page content...",
    "2": "Third page content..."
  },
  "fallback_pages": [],
  "processing_time": 12.34,
  "error_message": null
}
```

### Process an Image

```bash
# Process PNG image
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@screenshot.png"

# Process JPEG image
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@photo.jpg"
```

**Response:**
```json
{
  "success": true,
  "file_name": "screenshot.png",
  "file_path": "/tmp/ocrflux/screenshot_def456.png",
  "num_pages": 1,
  "document_text": "# Screenshot Content\n\nExtracted text from image...",
  "page_texts": {
    "0": "# Screenshot Content\n\nExtracted text from image..."
  },
  "fallback_pages": [],
  "processing_time": 5.67,
  "error_message": null
}
```

## Batch Processing

### Process Multiple Files

```bash
# Batch process multiple files
curl -X POST "http://localhost:8000/api/v1/batch" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf" \
  -F "files=@image.png" \
  -F "skip_cross_page_merge=false"
```

**Response:**
```json
{
  "total_files": 3,
  "successful_files": 3,
  "failed_files": 0,
  "processing_time": 25.89,
  "results": [
    {
      "success": true,
      "file_name": "document1.pdf",
      "num_pages": 2,
      "document_text": "Content from document1...",
      "processing_time": 8.45
    },
    {
      "success": true,
      "file_name": "document2.pdf",
      "num_pages": 1,
      "document_text": "Content from document2...",
      "processing_time": 6.12
    },
    {
      "success": true,
      "file_name": "image.png",
      "num_pages": 1,
      "document_text": "Content from image...",
      "processing_time": 3.21
    }
  ]
}
```

### Handling Partial Failures

```bash
# Some files may fail processing
curl -X POST "http://localhost:8000/api/v1/batch" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@valid_document.pdf" \
  -F "files=@corrupted_file.pdf" \
  -F "files=@valid_image.png"
```

**Response:**
```json
{
  "total_files": 3,
  "successful_files": 2,
  "failed_files": 1,
  "processing_time": 15.67,
  "results": [
    {
      "success": true,
      "file_name": "valid_document.pdf",
      "document_text": "Successfully extracted content..."
    },
    {
      "success": false,
      "file_name": "corrupted_file.pdf",
      "error_message": "Failed to parse PDF: File appears to be corrupted"
    },
    {
      "success": true,
      "file_name": "valid_image.png",
      "document_text": "Successfully extracted image content..."
    }
  ]
}
```

## Asynchronous Processing

### Submit Async Task

```bash
# Submit large file for async processing
curl -X POST "http://localhost:8000/api/v1/parse-async" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@large_document.pdf" \
  -F "skip_cross_page_merge=false"
```

**Response:**
```json
{
  "task_id": "task_abc123def456",
  "status": "pending",
  "message": "Task submitted successfully",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

### Check Task Status

```bash
# Check task progress
curl -X GET "http://localhost:8000/api/v1/tasks/task_abc123def456"
```

**Response (In Progress):**
```json
{
  "task_id": "task_abc123def456",
  "status": "processing",
  "progress": 0.65,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:33:00Z",
  "estimated_completion": "2024-01-15T10:35:00Z",
  "processing_time": 180.5,
  "error_message": null
}
```

**Response (Completed):**
```json
{
  "task_id": "task_abc123def456",
  "status": "completed",
  "progress": 1.0,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:34:30Z",
  "completed_at": "2024-01-15T10:34:30Z",
  "processing_time": 270.8,
  "error_message": null
}
```

### Retrieve Task Results

```bash
# Get completed task results
curl -X GET "http://localhost:8000/api/v1/tasks/task_abc123def456/result"
```

**Response:**
```json
{
  "success": true,
  "file_name": "large_document.pdf",
  "num_pages": 50,
  "document_text": "# Large Document\n\nExtracted content from all 50 pages...",
  "page_texts": {
    "0": "First page content...",
    "1": "Second page content...",
    "...": "...",
    "49": "Last page content..."
  },
  "fallback_pages": [15, 23],
  "processing_time": 270.8
}
```

### Cancel Task

```bash
# Cancel a pending or running task
curl -X DELETE "http://localhost:8000/api/v1/tasks/task_abc123def456"
```

**Response:**
```json
{
  "task_id": "task_abc123def456",
  "status": "cancelled",
  "message": "Task cancelled successfully"
}
```

## Health Monitoring

### Basic Health Check

```bash
# Simple health check
curl -X GET "http://localhost:8000/api/v1/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "uptime": 3600.5
}
```

### Detailed Health Information

```bash
# Comprehensive health check
curl -X GET "http://localhost:8000/api/v1/health/detailed"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "uptime": 3600.5,
  "model": {
    "loaded": true,
    "model_path": "/app/models/OCRFlux-3B",
    "load_time": 45.2,
    "memory_usage_mb": 2048.5
  },
  "system": {
    "cpu_usage": 25.6,
    "memory_usage": {
      "total_mb": 16384,
      "used_mb": 8192,
      "available_mb": 8192
    },
    "disk_usage": {
      "total_gb": 100,
      "used_gb": 45,
      "available_gb": 55
    }
  },
  "tasks": {
    "active_tasks": 2,
    "pending_tasks": 1,
    "completed_tasks": 156,
    "failed_tasks": 3
  }
}
```

### Model-Specific Health

```bash
# Check model health
curl -X GET "http://localhost:8000/api/v1/health/model"
```

**Response:**
```json
{
  "model_loaded": true,
  "model_path": "/app/models/OCRFlux-3B",
  "load_time": 45.2,
  "memory_usage_mb": 2048.5,
  "gpu_memory_usage_mb": 6144.0,
  "last_inference": "2024-01-15T10:29:45Z",
  "total_inferences": 1247,
  "average_inference_time": 8.3
}
```

## Error Handling

### Common Error Responses

#### File Too Large

```bash
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@huge_file.pdf"
```

**Response (413 Payload Too Large):**
```json
{
  "error_type": "file_error",
  "message": "Request size exceeds maximum limit of 100MB",
  "details": [
    {
      "field": "content-length",
      "message": "Request size is 157286400 bytes, maximum allowed is 104857600 bytes",
      "code": "REQUEST_TOO_LARGE",
      "context": {
        "actual_size_mb": 150.0,
        "max_size_mb": 100.0,
        "suggestion": "Reduce file size or use chunked upload for large files"
      }
    }
  ],
  "request_id": "req_abc123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Unsupported File Type

```bash
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.docx"
```

**Response (400 Bad Request):**
```json
{
  "error_type": "validation_error",
  "message": "File extension not allowed",
  "details": [
    {
      "field": "file",
      "message": "File extension '.docx' is not supported",
      "code": "INVALID_FILE_TYPE",
      "context": {
        "provided_extension": ".docx",
        "allowed_extensions": [".pdf", ".png", ".jpg", ".jpeg"]
      }
    }
  ],
  "request_id": "req_def456",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Model Not Ready

```bash
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

**Response (503 Service Unavailable):**
```json
{
  "error_type": "model_error",
  "message": "OCR model is not ready",
  "details": [
    {
      "message": "Model is still loading, please try again in a few moments",
      "code": "MODEL_LOADING",
      "context": {
        "model_status": "loading",
        "estimated_ready_time": "2024-01-15T10:32:00Z"
      }
    }
  ],
  "request_id": "req_ghi789",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Client Libraries

### Python Client Example

```python
import requests
import json
from pathlib import Path

class OCRFluxClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def process_file(self, file_path, **options):
        """Process a single file"""
        url = f"{self.base_url}/api/v1/parse"
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = options
            
            response = self.session.post(url, files=files, data=data)
            response.raise_for_status()
            
            return response.json()
    
    def process_batch(self, file_paths, **options):
        """Process multiple files"""
        url = f"{self.base_url}/api/v1/batch"
        
        files = []
        for file_path in file_paths:
            files.append(('files', open(file_path, 'rb')))
        
        try:
            response = self.session.post(url, files=files, data=options)
            response.raise_for_status()
            return response.json()
        finally:
            # Close all file handles
            for _, file_handle in files:
                file_handle.close()
    
    def submit_async_task(self, file_path, **options):
        """Submit file for async processing"""
        url = f"{self.base_url}/api/v1/parse-async"
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = options
            
            response = self.session.post(url, files=files, data=data)
            response.raise_for_status()
            
            return response.json()['task_id']
    
    def get_task_status(self, task_id):
        """Get task status"""
        url = f"{self.base_url}/api/v1/tasks/{task_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_task_result(self, task_id):
        """Get task result"""
        url = f"{self.base_url}/api/v1/tasks/{task_id}/result"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def health_check(self):
        """Check service health"""
        url = f"{self.base_url}/api/v1/health"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

# Usage example
client = OCRFluxClient()

# Process single file
result = client.process_file("document.pdf", skip_cross_page_merge=False)
print(f"Extracted text: {result['document_text'][:100]}...")

# Process multiple files
results = client.process_batch(["doc1.pdf", "doc2.pdf", "image.png"])
print(f"Processed {results['successful_files']} files successfully")

# Async processing
task_id = client.submit_async_task("large_document.pdf")
print(f"Task submitted: {task_id}")

# Wait for completion
import time
while True:
    status = client.get_task_status(task_id)
    print(f"Task status: {status['status']} ({status['progress']*100:.1f}%)")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(5)

# Get results
if status['status'] == 'completed':
    result = client.get_task_result(task_id)
    print(f"Final result: {result['document_text'][:100]}...")
```

### JavaScript/Node.js Client Example

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class OCRFluxClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.client = axios.create({ baseURL: baseUrl });
    }

    async processFile(filePath, options = {}) {
        const form = new FormData();
        form.append('file', fs.createReadStream(filePath));
        
        Object.entries(options).forEach(([key, value]) => {
            form.append(key, value);
        });

        const response = await this.client.post('/api/v1/parse', form, {
            headers: form.getHeaders()
        });

        return response.data;
    }

    async processBatch(filePaths, options = {}) {
        const form = new FormData();
        
        filePaths.forEach(filePath => {
            form.append('files', fs.createReadStream(filePath));
        });
        
        Object.entries(options).forEach(([key, value]) => {
            form.append(key, value);
        });

        const response = await this.client.post('/api/v1/batch', form, {
            headers: form.getHeaders()
        });

        return response.data;
    }

    async submitAsyncTask(filePath, options = {}) {
        const form = new FormData();
        form.append('file', fs.createReadStream(filePath));
        
        Object.entries(options).forEach(([key, value]) => {
            form.append(key, value);
        });

        const response = await this.client.post('/api/v1/parse-async', form, {
            headers: form.getHeaders()
        });

        return response.data.task_id;
    }

    async getTaskStatus(taskId) {
        const response = await this.client.get(`/api/v1/tasks/${taskId}`);
        return response.data;
    }

    async getTaskResult(taskId) {
        const response = await this.client.get(`/api/v1/tasks/${taskId}/result`);
        return response.data;
    }

    async healthCheck() {
        const response = await this.client.get('/api/v1/health');
        return response.data;
    }
}

// Usage example
async function main() {
    const client = new OCRFluxClient();

    try {
        // Process single file
        const result = await client.processFile('document.pdf', {
            skip_cross_page_merge: false
        });
        console.log(`Extracted text: ${result.document_text.substring(0, 100)}...`);

        // Process multiple files
        const batchResult = await client.processBatch([
            'doc1.pdf', 'doc2.pdf', 'image.png'
        ]);
        console.log(`Processed ${batchResult.successful_files} files successfully`);

        // Async processing
        const taskId = await client.submitAsyncTask('large_document.pdf');
        console.log(`Task submitted: ${taskId}`);

        // Wait for completion
        let status;
        do {
            status = await client.getTaskStatus(taskId);
            console.log(`Task status: ${status.status} (${(status.progress * 100).toFixed(1)}%)`);
            
            if (status.status === 'processing') {
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        } while (status.status === 'pending' || status.status === 'processing');

        // Get results
        if (status.status === 'completed') {
            const result = await client.getTaskResult(taskId);
            console.log(`Final result: ${result.document_text.substring(0, 100)}...`);
        }

    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

main();
```

## Advanced Usage

### Custom Processing Options

```bash
# Advanced PDF processing with all options
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@complex_document.pdf" \
  -F "skip_cross_page_merge=false" \
  -F "max_page_retries=3" \
  -F "target_longest_image_dim=1536" \
  -F "image_rotation=0"
```

### Webhook Notifications (Future Feature)

```bash
# Submit async task with webhook notification
curl -X POST "http://localhost:8000/api/v1/parse-async" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "webhook_url=https://your-app.com/webhook/ocr-complete" \
  -F "webhook_secret=your_secret_key"
```

### Batch Processing with Progress Tracking

```python
# Python example for batch processing with progress
import time
from concurrent.futures import ThreadPoolExecutor

def process_large_batch(client, file_paths, batch_size=5):
    """Process large number of files in batches"""
    results = []
    
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}: {len(batch)} files")
        
        # Submit async tasks for each file in batch
        task_ids = []
        for file_path in batch:
            task_id = client.submit_async_task(file_path)
            task_ids.append((task_id, file_path))
        
        # Wait for all tasks in batch to complete
        batch_results = []
        for task_id, file_path in task_ids:
            while True:
                status = client.get_task_status(task_id)
                if status['status'] in ['completed', 'failed']:
                    if status['status'] == 'completed':
                        result = client.get_task_result(task_id)
                        batch_results.append(result)
                    break
                time.sleep(2)
        
        results.extend(batch_results)
        print(f"Batch {i//batch_size + 1} completed: {len(batch_results)} successful")
    
    return results

# Usage
client = OCRFluxClient()
file_paths = ['doc1.pdf', 'doc2.pdf', 'doc3.pdf', ...]  # Large list
results = process_large_batch(client, file_paths)
```

### Error Recovery and Retry Logic

```python
import time
import random
from requests.exceptions import RequestException

def robust_process_file(client, file_path, max_retries=3, backoff_factor=2):
    """Process file with retry logic and exponential backoff"""
    
    for attempt in range(max_retries):
        try:
            result = client.process_file(file_path)
            return result
            
        except RequestException as e:
            if attempt == max_retries - 1:
                raise e
            
            # Exponential backoff with jitter
            delay = (backoff_factor ** attempt) + random.uniform(0, 1)
            print(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s...")
            time.sleep(delay)
    
    raise Exception(f"Failed to process {file_path} after {max_retries} attempts")

# Usage
try:
    result = robust_process_file(client, "problematic_document.pdf")
    print("Processing successful!")
except Exception as e:
    print(f"Processing failed: {e}")
```

This comprehensive guide covers all major aspects of using the OCRFlux API. For more specific use cases or advanced configurations, refer to the interactive API documentation at `/docs` when the service is running.