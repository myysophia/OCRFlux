"""
OpenAPI Usage Examples for OCRFlux API Service

This file demonstrates how to use the OpenAPI schema for various purposes:
- Client SDK generation
- API testing and validation
- Documentation generation
- Integration with development tools
"""

import json
import requests
from typing import Dict, Any, List
from pathlib import Path


class OpenAPIClient:
    """Example client that uses the OpenAPI schema for validation and documentation"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.schema = None
        self._load_schema()
    
    def _load_schema(self):
        """Load the OpenAPI schema from the API"""
        try:
            response = requests.get(f"{self.base_url}/openapi.json")
            response.raise_for_status()
            self.schema = response.json()
            print(f"✅ Loaded OpenAPI schema v{self.schema['openapi']}")
        except Exception as e:
            print(f"❌ Failed to load OpenAPI schema: {e}")
    
    def get_available_endpoints(self) -> List[Dict[str, Any]]:
        """Extract all available endpoints from the schema"""
        if not self.schema:
            return []
        
        endpoints = []
        for path, methods in self.schema.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    endpoints.append({
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "tags": details.get("tags", [])
                    })
        return endpoints
    
    def get_model_schemas(self) -> Dict[str, Any]:
        """Extract all data model schemas"""
        if not self.schema:
            return {}
        
        return self.schema.get("components", {}).get("schemas", {})
    
    def get_examples(self) -> Dict[str, Any]:
        """Extract all examples from the schema"""
        if not self.schema:
            return {}
        
        return self.schema.get("components", {}).get("examples", {})
    
    def validate_request_data(self, endpoint_path: str, method: str, data: Dict[str, Any]) -> bool:
        """Basic validation of request data against schema (simplified example)"""
        if not self.schema:
            return False
        
        # This is a simplified example - in practice, you'd use a proper JSON schema validator
        path_info = self.schema.get("paths", {}).get(endpoint_path, {})
        method_info = path_info.get(method.lower(), {})
        
        if not method_info:
            print(f"❌ Endpoint {method} {endpoint_path} not found in schema")
            return False
        
        print(f"✅ Endpoint {method} {endpoint_path} exists in schema")
        return True
    
    def generate_curl_examples(self) -> List[str]:
        """Generate curl command examples for all endpoints"""
        examples = []
        
        if not self.schema:
            return examples
        
        for path, methods in self.schema.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() == "POST":
                    # Generate POST example
                    curl_cmd = f'curl -X POST "{self.base_url}{path}"'
                    
                    # Add common headers
                    if "multipart/form-data" in str(details):
                        curl_cmd += ' \\\n  -F "file=@example.pdf"'
                    
                    examples.append({
                        "endpoint": f"{method.upper()} {path}",
                        "summary": details.get("summary", ""),
                        "curl": curl_cmd
                    })
                
                elif method.upper() == "GET":
                    # Generate GET example
                    curl_cmd = f'curl -X GET "{self.base_url}{path}"'
                    examples.append({
                        "endpoint": f"{method.upper()} {path}",
                        "summary": details.get("summary", ""),
                        "curl": curl_cmd
                    })
        
        return examples


def generate_client_code_examples():
    """Generate client code examples in different languages"""
    
    python_example = '''
# Python Client Example using requests
import requests
import json

class OCRFluxClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def process_file(self, file_path, **options):
        """Process a single file synchronously"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'skip_cross_page_merge': options.get('skip_cross_page_merge', False),
                'max_page_retries': options.get('max_page_retries', 1),
                'target_longest_image_dim': options.get('target_longest_image_dim', 1024)
            }
            
            response = requests.post(f"{self.base_url}/api/v1/parse", 
                                   files=files, data=data)
            response.raise_for_status()
            return response.json()
    
    def process_file_async(self, file_path, **options):
        """Submit file for asynchronous processing"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'skip_cross_page_merge': options.get('skip_cross_page_merge', False),
                'max_page_retries': options.get('max_page_retries', 1)
            }
            
            response = requests.post(f"{self.base_url}/api/v1/parse-async", 
                                   files=files, data=data)
            response.raise_for_status()
            return response.json()['task_id']
    
    def get_task_status(self, task_id):
        """Get status of an async task"""
        response = requests.get(f"{self.base_url}/api/v1/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def get_task_result(self, task_id):
        """Get result of completed async task"""
        response = requests.get(f"{self.base_url}/api/v1/tasks/{task_id}/result")
        response.raise_for_status()
        return response.json()
    
    def health_check(self):
        """Check service health"""
        response = requests.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()

# Usage example
client = OCRFluxClient()
result = client.process_file("document.pdf")
print(result['document_text'])
'''
    
    javascript_example = '''
// JavaScript Client Example using fetch
class OCRFluxClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async processFile(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('skip_cross_page_merge', options.skipCrossPageMerge || false);
        formData.append('max_page_retries', options.maxPageRetries || 1);
        formData.append('target_longest_image_dim', options.targetImageDim || 1024);
        
        const response = await fetch(`${this.baseUrl}/api/v1/parse`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async processFileAsync(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('skip_cross_page_merge', options.skipCrossPageMerge || false);
        formData.append('max_page_retries', options.maxPageRetries || 1);
        
        const response = await fetch(`${this.baseUrl}/api/v1/parse-async`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        return result.task_id;
    }
    
    async getTaskStatus(taskId) {
        const response = await fetch(`${this.baseUrl}/api/v1/tasks/${taskId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async getTaskResult(taskId) {
        const response = await fetch(`${this.baseUrl}/api/v1/tasks/${taskId}/result`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async healthCheck() {
        const response = await fetch(`${this.baseUrl}/api/v1/health`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
}

// Usage example
const client = new OCRFluxClient();
const fileInput = document.getElementById('fileInput');

fileInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        try {
            const result = await client.processFile(file);
            console.log('Document text:', result.document_text);
        } catch (error) {
            console.error('Processing failed:', error);
        }
    }
});
'''
    
    return {
        "python": python_example,
        "javascript": javascript_example
    }


def demonstrate_schema_usage():
    """Demonstrate various ways to use the OpenAPI schema"""
    
    print("🚀 OCRFlux API OpenAPI Schema Usage Examples")
    print("=" * 50)
    
    # Initialize client
    client = OpenAPIClient()
    
    if not client.schema:
        print("❌ Could not load schema. Make sure the API server is running.")
        return
    
    # Show available endpoints
    print("\n📋 Available API Endpoints:")
    print("-" * 30)
    endpoints = client.get_available_endpoints()
    for endpoint in endpoints[:10]:  # Show first 10
        print(f"  {endpoint['method']} {endpoint['path']}")
        print(f"    📝 {endpoint['summary']}")
        if endpoint['tags']:
            print(f"    🏷️  Tags: {', '.join(endpoint['tags'])}")
        print()
    
    # Show data models
    print("\n📊 Available Data Models:")
    print("-" * 30)
    models = client.get_model_schemas()
    for model_name in list(models.keys())[:5]:  # Show first 5
        model = models[model_name]
        print(f"  📋 {model_name}")
        if 'description' in model:
            print(f"    📝 {model['description'][:100]}...")
        print()
    
    # Show examples
    print("\n💡 Available Examples:")
    print("-" * 30)
    examples = client.get_examples()
    for example_name, example_data in list(examples.items())[:3]:  # Show first 3
        print(f"  🔍 {example_name}")
        print(f"    📝 {example_data.get('summary', 'No summary')}")
        print()
    
    # Generate curl examples
    print("\n🔧 Generated cURL Examples:")
    print("-" * 30)
    curl_examples = client.generate_curl_examples()
    for example in curl_examples[:3]:  # Show first 3
        print(f"  📡 {example['endpoint']}")
        print(f"    {example['curl']}")
        print()
    
    # Show schema statistics
    print("\n📈 Schema Statistics:")
    print("-" * 30)
    print(f"  📊 Total endpoints: {len(endpoints)}")
    print(f"  📋 Total models: {len(models)}")
    print(f"  💡 Total examples: {len(examples)}")
    print(f"  🏷️  Tags: {len(set(tag for ep in endpoints for tag in ep['tags']))}")


def export_documentation():
    """Export documentation in various formats"""
    
    print("\n📚 Exporting Documentation:")
    print("-" * 30)
    
    client = OpenAPIClient()
    if not client.schema:
        return
    
    # Export OpenAPI schema
    schema_file = Path("openapi_schema.json")
    with open(schema_file, 'w') as f:
        json.dump(client.schema, f, indent=2)
    print(f"  ✅ OpenAPI schema exported to {schema_file}")
    
    # Export endpoint list
    endpoints_file = Path("api_endpoints.json")
    endpoints = client.get_available_endpoints()
    with open(endpoints_file, 'w') as f:
        json.dump(endpoints, f, indent=2)
    print(f"  ✅ Endpoint list exported to {endpoints_file}")
    
    # Export examples
    examples_file = Path("api_examples.json")
    examples = client.get_examples()
    with open(examples_file, 'w') as f:
        json.dump(examples, f, indent=2)
    print(f"  ✅ Examples exported to {examples_file}")
    
    # Export client code examples
    client_examples = generate_client_code_examples()
    
    python_file = Path("client_example.py")
    with open(python_file, 'w') as f:
        f.write(client_examples['python'])
    print(f"  ✅ Python client example exported to {python_file}")
    
    js_file = Path("client_example.js")
    with open(js_file, 'w') as f:
        f.write(client_examples['javascript'])
    print(f"  ✅ JavaScript client example exported to {js_file}")


if __name__ == "__main__":
    # Run the demonstration
    demonstrate_schema_usage()
    
    # Export documentation files
    export_documentation()
    
    print("\n🎉 OpenAPI documentation examples completed!")
    print("\nNext steps:")
    print("  1. Visit http://localhost:8000/docs for interactive documentation")
    print("  2. Visit http://localhost:8000/redoc for comprehensive docs")
    print("  3. Use the exported files for client SDK generation")
    print("  4. Import openapi_schema.json into Postman or Insomnia")