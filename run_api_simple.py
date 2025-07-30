#!/usr/bin/env python3
"""
Simple OCRFlux API Server Launcher

This script provides a simplified way to start the OCRFlux API service
without complex configuration checks.
"""
import os
import sys
import uvicorn
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

def main():
    """Main entry point for the API server"""
    
    # Set basic environment variables if not set
    os.environ.setdefault("MODEL_PATH", "/var/lib/gpustack/cache/model_scope/ChatDOC/OCRFlux-3B")
    os.environ.setdefault("HOST", "0.0.0.0")
    os.environ.setdefault("PORT", "8000")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("GPU_MEMORY_UTILIZATION", "0.9")
    os.environ.setdefault("MAX_CONCURRENT_TASKS", "8")
    os.environ.setdefault("TEMP_DIR", "/tmp/ocrflux")
    
    # Create temp directory
    temp_dir = os.environ.get("TEMP_DIR", "/tmp/ocrflux")
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"Starting OCRFlux API Server...")
    print(f"Model Path: {os.environ.get('MODEL_PATH')}")
    print(f"Host: {os.environ.get('HOST')}")
    print(f"Port: {os.environ.get('PORT')}")
    print(f"Temp Dir: {temp_dir}")
    
    try:
        # Import and create FastAPI app
        from api.main import app
        
        # Start server
        uvicorn.run(
            app,
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", 8000)),
            log_level=os.environ.get("LOG_LEVEL", "info").lower(),
            reload=False
        )
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure all required modules are installed:")
        print("pip install fastapi uvicorn pydantic pydantic-settings python-multipart")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()