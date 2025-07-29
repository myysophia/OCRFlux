#!/usr/bin/env python3
"""
Configuration validation and health check script for OCRFlux API Service
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.core.config import settings


def check_python_version() -> Dict[str, Any]:
    """Check Python version compatibility"""
    result = {
        "name": "Python Version",
        "status": "pass",
        "details": {},
        "recommendations": []
    }
    
    current_version = sys.version_info
    required_version = (3, 11)
    
    result["details"]["current_version"] = f"{current_version.major}.{current_version.minor}.{current_version.micro}"
    result["details"]["required_version"] = f"{required_version[0]}.{required_version[1]}+"
    
    if current_version < required_version:
        result["status"] = "fail"
        result["recommendations"].append(f"Upgrade Python to {required_version[0]}.{required_version[1]} or higher")
    
    return result


def check_environment_variables() -> Dict[str, Any]:
    """Check environment variables configuration"""
    result = {
        "name": "Environment Variables",
        "status": "pass",
        "details": {},
        "recommendations": []
    }
    
    # Check for .env file
    env_file = project_root / ".env"
    result["details"]["env_file_exists"] = env_file.exists()
    result["details"]["env_file_path"] = str(env_file)
    
    # Check important environment variables
    important_vars = [
        "MODEL_PATH",
        "TEMP_DIR", 
        "MAX_FILE_SIZE",
        "LOG_LEVEL",
        "DEBUG"
    ]
    
    missing_vars = []
    for var in important_vars:
        if var not in os.environ:
            missing_vars.append(var)
    
    result["details"]["missing_variables"] = missing_vars
    
    if missing_vars:
        result["status"] = "warning"
        result["recommendations"].append("Consider setting missing environment variables for better configuration control")
    
    return result


def check_directories() -> Dict[str, Any]:
    """Check required directories"""
    result = {
        "name": "Directory Structure",
        "status": "pass",
        "details": {},
        "recommendations": []
    }
    
    directories_to_check = [
        ("temp_dir", settings.temp_dir, True),  # (name, path, required)
        ("model_path", settings.model_path, False),
        ("log_dir", Path(settings.log_file).parent if settings.log_file else None, False)
    ]
    
    for name, path, required in directories_to_check:
        if path is None:
            result["details"][name] = {"exists": None, "writable": None, "path": None}
            continue
            
        path_obj = Path(path)
        exists = path_obj.exists()
        writable = path_obj.is_dir() and os.access(path_obj, os.W_OK) if exists else None
        
        result["details"][name] = {
            "exists": exists,
            "writable": writable,
            "path": str(path_obj)
        }
        
        if required and not exists:
            result["status"] = "fail"
            result["recommendations"].append(f"Create required directory: {path}")
        elif exists and not writable:
            result["status"] = "warning"
            result["recommendations"].append(f"Directory not writable: {path}")
    
    return result


def check_dependencies() -> Dict[str, Any]:
    """Check Python dependencies"""
    result = {
        "name": "Python Dependencies",
        "status": "pass",
        "details": {},
        "recommendations": []
    }
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic-settings",
        "python-multipart",
        "aiofiles",
        "psutil"
    ]
    
    optional_packages = [
        "python-magic",
        "vllm",
        "torch",
        "transformers"
    ]
    
    missing_required = []
    missing_optional = []
    installed_versions = {}
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            # Try to get version
            try:
                import importlib.metadata
                version = importlib.metadata.version(package)
                installed_versions[package] = version
            except:
                installed_versions[package] = "unknown"
        except ImportError:
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            __import__(package.replace("-", "_"))
            try:
                import importlib.metadata
                version = importlib.metadata.version(package)
                installed_versions[package] = version
            except:
                installed_versions[package] = "unknown"
        except ImportError:
            missing_optional.append(package)
    
    result["details"]["installed_versions"] = installed_versions
    result["details"]["missing_required"] = missing_required
    result["details"]["missing_optional"] = missing_optional
    
    if missing_required:
        result["status"] = "fail"
        result["recommendations"].append(f"Install missing required packages: {', '.join(missing_required)}")
    
    if missing_optional:
        result["status"] = "warning" if result["status"] == "pass" else result["status"]
        result["recommendations"].append(f"Consider installing optional packages: {', '.join(missing_optional)}")
    
    return result


def check_configuration() -> Dict[str, Any]:
    """Check application configuration"""
    result = {
        "name": "Application Configuration",
        "status": "pass",
        "details": {},
        "recommendations": []
    }
    
    # Check configuration values
    config_checks = {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "host": settings.host,
        "port": settings.port,
        "max_file_size_mb": settings.max_file_size // (1024 * 1024),
        "allowed_extensions": settings.allowed_extensions,
        "log_level": settings.log_level,
        "api_prefix": settings.api_prefix
    }
    
    result["details"]["configuration"] = config_checks
    
    # Check for potential issues
    if settings.debug and settings.host == "0.0.0.0":
        result["status"] = "warning"
        result["recommendations"].append("Debug mode with 0.0.0.0 host may expose debug information")
    
    if settings.max_file_size > 500 * 1024 * 1024:  # 500MB
        result["status"] = "warning"
        result["recommendations"].append("Very large max file size may cause memory issues")
    
    if settings.cors_origins == ["*"]:
        result["status"] = "warning"
        result["recommendations"].append("Wildcard CORS origins should be restricted in production")
    
    return result


def check_model_configuration() -> Dict[str, Any]:
    """Check model configuration"""
    result = {
        "name": "Model Configuration",
        "status": "pass",
        "details": {},
        "recommendations": []
    }
    
    model_path = Path(settings.model_path)
    result["details"]["model_path"] = str(model_path)
    result["details"]["model_exists"] = model_path.exists()
    result["details"]["gpu_memory_utilization"] = settings.gpu_memory_utilization
    result["details"]["model_max_context"] = settings.model_max_context
    
    if not model_path.exists() and settings.model_path != "/path/to/OCRFlux-3B":
        result["status"] = "warning"
        result["recommendations"].append("Model path does not exist - model will need to be downloaded/configured")
    
    if settings.gpu_memory_utilization > 0.9:
        result["status"] = "warning"
        result["recommendations"].append("High GPU memory utilization may cause out-of-memory errors")
    
    return result


def check_security_configuration() -> Dict[str, Any]:
    """Check security configuration"""
    result = {
        "name": "Security Configuration",
        "status": "pass",
        "details": {},
        "recommendations": []
    }
    
    security_checks = {
        "cors_origins": settings.cors_origins,
        "cors_methods": settings.cors_methods,
        "cors_headers": settings.cors_headers,
        "debug_mode": settings.debug,
        "max_request_headers": settings.max_request_headers,
        "max_header_size": settings.max_header_size
    }
    
    result["details"]["security_settings"] = security_checks
    
    # Security recommendations
    if settings.debug:
        result["status"] = "warning"
        result["recommendations"].append("Debug mode should be disabled in production")
    
    if "*" in settings.cors_origins:
        result["status"] = "warning"
        result["recommendations"].append("Wildcard CORS origins should be restricted in production")
    
    if settings.max_request_headers > 200:
        result["status"] = "warning"
        result["recommendations"].append("High max request headers limit may allow DoS attacks")
    
    return result


def run_all_checks() -> List[Dict[str, Any]]:
    """Run all configuration checks"""
    checks = [
        check_python_version,
        check_environment_variables,
        check_directories,
        check_dependencies,
        check_configuration,
        check_model_configuration,
        check_security_configuration
    ]
    
    results = []
    for check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            results.append({
                "name": check_func.__name__,
                "status": "error",
                "details": {"error": str(e)},
                "recommendations": ["Fix the error and run check again"]
            })
    
    return results


def print_results(results: List[Dict[str, Any]], format_type: str = "text"):
    """Print check results"""
    if format_type == "json":
        print(json.dumps(results, indent=2))
        return
    
    # Text format
    print("=" * 80)
    print("OCRFlux API Service - Configuration Check Results")
    print("=" * 80)
    
    overall_status = "PASS"
    for result in results:
        status_icon = {
            "pass": "✅",
            "warning": "⚠️",
            "fail": "❌",
            "error": "💥"
        }.get(result["status"], "❓")
        
        print(f"\n{status_icon} {result['name']}: {result['status'].upper()}")
        
        if result["status"] in ["warning", "fail", "error"]:
            overall_status = "FAIL" if result["status"] in ["fail", "error"] else "WARNING"
        
        # Print details if not pass
        if result["status"] != "pass":
            if result.get("details"):
                print("   Details:")
                for key, value in result["details"].items():
                    print(f"     {key}: {value}")
            
            if result.get("recommendations"):
                print("   Recommendations:")
                for rec in result["recommendations"]:
                    print(f"     • {rec}")
    
    print("\n" + "=" * 80)
    status_icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌"}[overall_status]
    print(f"Overall Status: {status_icon} {overall_status}")
    print("=" * 80)
    
    return overall_status


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OCRFlux API Service Configuration Checker")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--check", help="Run specific check only")
    
    args = parser.parse_args()
    
    if args.check:
        # Run specific check
        check_functions = {
            "python": check_python_version,
            "env": check_environment_variables,
            "dirs": check_directories,
            "deps": check_dependencies,
            "config": check_configuration,
            "model": check_model_configuration,
            "security": check_security_configuration
        }
        
        if args.check not in check_functions:
            print(f"Unknown check: {args.check}")
            print(f"Available checks: {', '.join(check_functions.keys())}")
            sys.exit(1)
        
        result = check_functions[args.check]()
        results = [result]
    else:
        # Run all checks
        results = run_all_checks()
    
    overall_status = print_results(results, args.format)
    
    # Exit with appropriate code
    if overall_status == "FAIL":
        sys.exit(1)
    elif overall_status == "WARNING":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()