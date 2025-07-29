#!/usr/bin/env python3
"""
OCRFlux API Service - Production Server Runner

This script provides advanced server configuration and startup options
for running the OCRFlux API service in different environments.
"""

import os
import sys
import argparse
import logging
import signal
import asyncio
from pathlib import Path
from typing import Optional

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.core.config import settings
from api.core.logging import setup_logging


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


def validate_environment():
    """Validate environment and dependencies"""
    logger = logging.getLogger(__name__)
    
    # Check Python version
    if sys.version_info < (3, 11):
        logger.error("Python 3.11 or higher is required")
        sys.exit(1)
    
    # Check required directories
    temp_dir = Path(settings.temp_dir)
    if not temp_dir.exists():
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Failed to create temporary directory: {e}")
            sys.exit(1)
    
    # Check model path if specified
    if settings.model_path and settings.model_path != "/path/to/OCRFlux-3B":
        model_path = Path(settings.model_path)
        if not model_path.exists():
            logger.warning(f"Model path does not exist: {model_path}")
            logger.warning("Model will be loaded on first request if available")
    
    logger.info("Environment validation completed")


def create_uvicorn_config(
    host: str = None,
    port: int = None,
    workers: int = None,
    reload: bool = None,
    log_level: str = None,
    access_log: bool = True,
    ssl_keyfile: Optional[str] = None,
    ssl_certfile: Optional[str] = None
) -> dict:
    """Create uvicorn server configuration"""
    
    config = {
        "app": "api.main:app",
        "host": host or settings.host,
        "port": port or settings.port,
        "log_level": (log_level or settings.log_level).lower(),
        "access_log": access_log,
        "server_header": False,  # Don't expose server info
        "date_header": False,    # Don't expose date header
    }
    
    # Development vs Production settings
    if reload is not None:
        config["reload"] = reload
    elif settings.debug:
        config["reload"] = True
        config["reload_dirs"] = [str(project_root / "api")]
    
    # Worker configuration for production
    if workers and workers > 1:
        config["workers"] = workers
        # Remove reload if using multiple workers
        config.pop("reload", None)
        config.pop("reload_dirs", None)
    
    # SSL configuration
    if ssl_keyfile and ssl_certfile:
        config["ssl_keyfile"] = ssl_keyfile
        config["ssl_certfile"] = ssl_certfile
        logging.info("SSL/TLS enabled")
    
    return config


def run_development_server(args):
    """Run development server with hot reload"""
    import uvicorn
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting OCRFlux API Service in DEVELOPMENT mode")
    
    config = create_uvicorn_config(
        host=args.host,
        port=args.port,
        reload=True,
        log_level=args.log_level
    )
    
    logger.info(f"Server configuration: {config}")
    uvicorn.run(**config)


def run_production_server(args):
    """Run production server with multiple workers"""
    import uvicorn
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting OCRFlux API Service in PRODUCTION mode")
    
    # Calculate optimal worker count if not specified
    workers = args.workers
    if not workers:
        import multiprocessing
        workers = min(multiprocessing.cpu_count(), 4)  # Max 4 workers for memory reasons
        logger.info(f"Auto-detected worker count: {workers}")
    
    config = create_uvicorn_config(
        host=args.host,
        port=args.port,
        workers=workers,
        reload=False,
        log_level=args.log_level,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile
    )
    
    logger.info(f"Server configuration: {config}")
    uvicorn.run(**config)


def run_single_worker_server(args):
    """Run single worker server (useful for debugging)"""
    import uvicorn
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting OCRFlux API Service in SINGLE WORKER mode")
    
    config = create_uvicorn_config(
        host=args.host,
        port=args.port,
        workers=1,
        reload=args.reload,
        log_level=args.log_level,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile
    )
    
    logger.info(f"Server configuration: {config}")
    uvicorn.run(**config)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="OCRFlux API Service Server Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Development server with hot reload
  python run_server.py --mode dev
  
  # Production server with auto-detected workers
  python run_server.py --mode prod
  
  # Single worker server for debugging
  python run_server.py --mode single --reload
  
  # Custom host and port
  python run_server.py --host 0.0.0.0 --port 8080
  
  # Enable SSL/TLS
  python run_server.py --ssl-cert cert.pem --ssl-key key.pem
        """
    )
    
    # Server mode
    parser.add_argument(
        "--mode", 
        choices=["dev", "prod", "single"],
        default="dev" if settings.debug else "prod",
        help="Server mode (default: auto-detect based on DEBUG setting)"
    )
    
    # Network configuration
    parser.add_argument("--host", default=settings.host, help="Host to bind to")
    parser.add_argument("--port", type=int, default=settings.port, help="Port to bind to")
    
    # Worker configuration
    parser.add_argument("--workers", type=int, help="Number of worker processes (production mode)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    # Logging configuration
    parser.add_argument("--log-level", default=settings.log_level, help="Log level")
    parser.add_argument("--log-file", help="Log file path")
    
    # SSL configuration
    parser.add_argument("--ssl-cert", dest="ssl_certfile", help="SSL certificate file")
    parser.add_argument("--ssl-key", dest="ssl_keyfile", help="SSL private key file")
    
    # Environment configuration
    parser.add_argument("--env-file", help="Environment file path")
    parser.add_argument("--validate-only", action="store_true", help="Only validate environment and exit")
    
    args = parser.parse_args()
    
    # Load environment file if specified
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
        print(f"Loaded environment from: {args.env_file}")
    
    # Setup logging
    setup_logging(level=args.log_level, log_file=args.log_file)
    logger = logging.getLogger(__name__)
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Validate environment
    validate_environment()
    
    if args.validate_only:
        logger.info("Environment validation completed successfully")
        return
    
    # Print startup information
    logger.info("=" * 60)
    logger.info("OCRFlux API Service")
    logger.info("=" * 60)
    logger.info(f"Version: {settings.app_version}")
    logger.info(f"Mode: {args.mode.upper()}")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Debug: {settings.debug}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info(f"Model Path: {settings.model_path}")
    logger.info(f"Temp Dir: {settings.temp_dir}")
    logger.info("=" * 60)
    
    # Run server based on mode
    try:
        if args.mode == "dev":
            run_development_server(args)
        elif args.mode == "prod":
            run_production_server(args)
        elif args.mode == "single":
            run_single_worker_server(args)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()