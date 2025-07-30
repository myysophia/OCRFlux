#!/usr/bin/env python3
"""
Enhanced OCRFlux API Server Launcher

This script starts the enhanced OCRFlux API service with more endpoints.
"""
import os
import sys
import uvicorn
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

def main():
    """Main entry point for the enhanced API server"""
    
    print("Starting Enhanced OCRFlux API Service...")
    print("Features included:")
    print("- Single file OCR processing")
    print("- Batch file processing") 
    print("- Asynchronous task processing")
    print("- Task status and result endpoints")
    print("- Detailed health monitoring")
    print("- Complete API documentation")
    
    try:
        # Import the enhanced app
        from api.main_enhanced import app, config
        
        print(f"Model Path: {config.model_path}")
        print(f"Host: {config.host}")
        print(f"Port: {config.port}")
        print(f"Docs URL: http://{config.host}:{config.port}/docs")
        print(f"API Info: http://{config.host}:{config.port}/api-info")
        
        # Start server
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level=config.log_level.lower(),
            reload=False
        )
        
    except Exception as e:
        print(f"Error starting enhanced server: {e}")
        print("Falling back to simple version...")
        
        # Fallback to simple version
        try:
            from api.main import app
            uvicorn.run(app, host="0.0.0.0", port=8000)
        except Exception as e2:
            print(f"Error starting fallback server: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    main()