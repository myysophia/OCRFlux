#!/usr/bin/env python3
"""
Complete OCRFlux API Server Launcher

This script starts the complete OCRFlux API service with all implemented features.
"""
import os
import sys
import uvicorn
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

def main():
    """Main entry point for the complete API server"""
    
    print("Starting Complete OCRFlux API Service...")
    print("Features included:")
    print("- Single file OCR processing")
    print("- Batch file processing")
    print("- Asynchronous task processing")
    print("- Health monitoring")
    print("- Complete error handling")
    print("- OpenAPI documentation")
    
    try:
        # Import and start the complete app
        from api.main_complete import app
        
        # Get configuration
        from api.core.config import settings
        
        print(f"Model Path: {settings.model_path}")
        print(f"Host: {settings.host}")
        print(f"Port: {settings.port}")
        print(f"Docs URL: http://{settings.host}:{settings.port}{settings.docs_url}")
        
        # Start server
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            reload=False
        )
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Some components may be missing. Using simplified version...")
        
        # Fallback to simple version
        from api.main import app
        from api.core.config import settings
        
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            reload=False
        )
        
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()