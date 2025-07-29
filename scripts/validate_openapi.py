#!/usr/bin/env python3
"""
OpenAPI Documentation Validation Script

This script validates that the OpenAPI documentation is properly configured
and accessible. It can be run independently to verify the documentation setup.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def validate_openapi_structure():
    """Validate the OpenAPI schema structure without running the server"""
    
    print("🔍 Validating OpenAPI Documentation Structure")
    print("=" * 50)
    
    # Check if required files exist
    required_files = [
        "api/core/openapi.py",
        "api/routes/docs.py", 
        "api/main.py",
        "docs/openapi_documentation.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"\n❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print(f"\n✅ All required OpenAPI files are present")
    return True


def validate_openapi_functions():
    """Validate that OpenAPI functions are properly defined"""
    
    print("\n🔧 Validating OpenAPI Functions")
    print("-" * 30)
    
    try:
        # Import the OpenAPI module (this will test basic syntax)
        openapi_file = project_root / "api" / "core" / "openapi.py"
        
        # Read and check for required functions
        with open(openapi_file, 'r') as f:
            content = f.read()
        
        required_functions = [
            "custom_openapi_schema",
            "_add_common_responses", 
            "_enhance_examples",
            "_add_custom_extensions",
            "setup_openapi_customization"
        ]
        
        missing_functions = []
        for func_name in required_functions:
            if f"def {func_name}" not in content:
                missing_functions.append(func_name)
            else:
                print(f"✅ Function: {func_name}")
        
        if missing_functions:
            print(f"\n❌ Missing required functions:")
            for func_name in missing_functions:
                print(f"   - {func_name}")
            return False
        
        print(f"\n✅ All required OpenAPI functions are defined")
        return True
        
    except Exception as e:
        print(f"❌ Error validating OpenAPI functions: {e}")
        return False


def validate_documentation_routes():
    """Validate that documentation routes are properly defined"""
    
    print("\n📋 Validating Documentation Routes")
    print("-" * 30)
    
    try:
        docs_file = project_root / "api" / "routes" / "docs.py"
        
        with open(docs_file, 'r') as f:
            content = f.read()
        
        required_routes = [
            "/openapi.json",
            "/docs", 
            "/redoc",
            "/api-info",
            "/schema-stats"
        ]
        
        missing_routes = []
        for route in required_routes:
            if f'"{route}"' not in content:
                missing_routes.append(route)
            else:
                print(f"✅ Route: {route}")
        
        if missing_routes:
            print(f"\n❌ Missing required routes:")
            for route in missing_routes:
                print(f"   - {route}")
            return False
        
        print(f"\n✅ All required documentation routes are defined")
        return True
        
    except Exception as e:
        print(f"❌ Error validating documentation routes: {e}")
        return False


def validate_main_app_integration():
    """Validate that OpenAPI is properly integrated in main app"""
    
    print("\n🚀 Validating Main App Integration")
    print("-" * 30)
    
    try:
        main_file = project_root / "api" / "main.py"
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        required_integrations = [
            "from api.core.openapi import setup_openapi_customization",
            "setup_openapi_customization(app)",
            "app.include_router(docs.router",
            "tags_metadata=["
        ]
        
        missing_integrations = []
        for integration in required_integrations:
            if integration not in content:
                missing_integrations.append(integration)
            else:
                print(f"✅ Integration: {integration[:50]}...")
        
        if missing_integrations:
            print(f"\n❌ Missing required integrations:")
            for integration in missing_integrations:
                print(f"   - {integration}")
            return False
        
        print(f"\n✅ OpenAPI is properly integrated in main app")
        return True
        
    except Exception as e:
        print(f"❌ Error validating main app integration: {e}")
        return False


def validate_examples_and_documentation():
    """Validate that examples and documentation are comprehensive"""
    
    print("\n📚 Validating Examples and Documentation")
    print("-" * 30)
    
    try:
        # Check OpenAPI examples
        openapi_file = project_root / "api" / "core" / "openapi.py"
        with open(openapi_file, 'r') as f:
            openapi_content = f.read()
        
        required_examples = [
            "SingleFileSuccess",
            "BatchProcessSuccess", 
            "TaskSubmitted",
            "TaskCompleted",
            "HealthySystem"
        ]
        
        missing_examples = []
        for example in required_examples:
            if f'"{example}"' not in openapi_content:
                missing_examples.append(example)
            else:
                print(f"✅ Example: {example}")
        
        # Check code samples
        code_samples = ["python", "javascript", "curl"]
        for sample in code_samples:
            if f'"{sample}"' in openapi_content:
                print(f"✅ Code sample: {sample}")
            else:
                missing_examples.append(f"Code sample: {sample}")
        
        # Check documentation file
        docs_file = project_root / "docs" / "openapi_documentation.md"
        if docs_file.exists():
            print(f"✅ Documentation file: openapi_documentation.md")
        else:
            missing_examples.append("Documentation file")
        
        if missing_examples:
            print(f"\n❌ Missing examples/documentation:")
            for item in missing_examples:
                print(f"   - {item}")
            return False
        
        print(f"\n✅ All examples and documentation are present")
        return True
        
    except Exception as e:
        print(f"❌ Error validating examples: {e}")
        return False


def generate_validation_report():
    """Generate a comprehensive validation report"""
    
    print("\n📊 OpenAPI Documentation Validation Report")
    print("=" * 50)
    
    validations = [
        ("File Structure", validate_openapi_structure),
        ("OpenAPI Functions", validate_openapi_functions),
        ("Documentation Routes", validate_documentation_routes),
        ("Main App Integration", validate_main_app_integration),
        ("Examples & Documentation", validate_examples_and_documentation)
    ]
    
    results = {}
    all_passed = True
    
    for name, validation_func in validations:
        try:
            result = validation_func()
            results[name] = result
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
            results[name] = False
            all_passed = False
    
    # Summary
    print(f"\n📋 Validation Summary")
    print("-" * 20)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {name}")
    
    if all_passed:
        print(f"\n🎉 All OpenAPI documentation validations passed!")
        print(f"\nNext steps:")
        print(f"  1. Start the API server: uvicorn api.main:app --reload")
        print(f"  2. Visit http://localhost:8000/docs for Swagger UI")
        print(f"  3. Visit http://localhost:8000/redoc for ReDoc")
        print(f"  4. Access http://localhost:8000/openapi.json for the schema")
        return True
    else:
        print(f"\n❌ Some validations failed. Please fix the issues above.")
        return False


def main():
    """Main validation function"""
    
    print("🚀 OCRFlux API OpenAPI Documentation Validator")
    print("=" * 60)
    print("This script validates the OpenAPI documentation setup")
    print("without requiring the full application to be running.\n")
    
    success = generate_validation_report()
    
    if success:
        print(f"\n✨ OpenAPI documentation is properly configured!")
        sys.exit(0)
    else:
        print(f"\n💥 OpenAPI documentation has configuration issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()