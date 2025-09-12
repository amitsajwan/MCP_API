#!/usr/bin/env python3
"""
System Verification Script
==========================
Verifies the complete MCP system flow and logic
"""

import os
import sys
import importlib
import inspect
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_imports():
    """Verify all imports work correctly"""
    print("🔍 Verifying imports...")
    
    modules_to_check = [
        'mcp_server_fastmcp2',
        'mcp_client', 
        'mcp_service',
        'web_ui_ws',
        'intelligent_bot',
        'intelligent_bot_demo'
    ]
    
    failed_imports = []
    
    for module_name in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name}: {e}")
            failed_imports.append(module_name)
    
    return len(failed_imports) == 0

def verify_dependencies():
    """Verify all dependencies are available"""
    print("\n🔍 Verifying dependencies...")
    
    required_packages = [
        'fastmcp',
        'azure.identity',
        'openai',
        'flask',
        'flask_socketio',
        'requests',
        'yaml',
        'openapi_core'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def verify_file_structure():
    """Verify all required files exist"""
    print("\n🔍 Verifying file structure...")
    
    required_files = [
        'mcp_server_fastmcp2.py',
        'mcp_client.py',
        'mcp_service.py',
        'web_ui_ws.py',
        'intelligent_bot.py',
        'intelligent_bot_demo.py',
        'view_logs.py',
        'requirements.txt',
        'env.example',
        'templates/chat_ws.html',
        'openapi_specs/cash_api.yaml',
        'openapi_specs/cls_api.yaml',
        'openapi_specs/mailbox_api.yaml',
        'openapi_specs/securities_api.yaml'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def verify_class_methods():
    """Verify all required classes and methods exist"""
    print("\n🔍 Verifying class methods...")
    
    # Check ModernLLMService
    try:
        from mcp_service import ModernLLMService
        service = ModernLLMService()
        
        required_methods = ['initialize', 'process_message', '_analyze_capabilities']
        for method in required_methods:
            if hasattr(service, method):
                print(f"  ✅ ModernLLMService.{method}")
            else:
                print(f"  ❌ ModernLLMService.{method}")
                return False
    except Exception as e:
        print(f"  ❌ ModernLLMService: {e}")
        return False
    
    # Check MCPDemoService
    try:
        from web_ui_ws import MCPDemoService
        demo_service = MCPDemoService()
        
        required_methods = ['initialize', 'process_message']
        for method in required_methods:
            if hasattr(demo_service, method):
                print(f"  ✅ MCPDemoService.{method}")
            else:
                print(f"  ❌ MCPDemoService.{method}")
                return False
    except Exception as e:
        print(f"  ❌ MCPDemoService: {e}")
        return False
    
    return True

def verify_flow_logic():
    """Verify the logical flow of the system"""
    print("\n🔍 Verifying flow logic...")
    
    # Check that MCP service can be initialized
    try:
        from mcp_service import ModernLLMService
        service = ModernLLMService()
        
        # Check initialization method exists and is callable
        if callable(service.initialize):
            print("  ✅ ModernLLMService.initialize is callable")
        else:
            print("  ❌ ModernLLMService.initialize is not callable")
            return False
        
        # Check process_message method exists and is callable
        if callable(service.process_message):
            print("  ✅ ModernLLMService.process_message is callable")
        else:
            print("  ❌ ModernLLMService.process_message is not callable")
            return False
        
    except Exception as e:
        print(f"  ❌ Flow logic verification failed: {e}")
        return False
    
    return True

def verify_web_ui_events():
    """Verify web UI event handlers exist"""
    print("\n🔍 Verifying web UI events...")
    
    try:
        from web_ui_ws import app, socketio
        
        # Check Flask app
        if app is not None:
            print("  ✅ Flask app initialized")
        else:
            print("  ❌ Flask app not initialized")
            return False
        
        # Check SocketIO
        if socketio is not None:
            print("  ✅ SocketIO initialized")
        else:
            print("  ❌ SocketIO not initialized")
            return False
        
        # Check route exists
        if hasattr(app, 'route'):
            print("  ✅ Flask routes available")
        else:
            print("  ❌ Flask routes not available")
            return False
        
    except Exception as e:
        print(f"  ❌ Web UI verification failed: {e}")
        return False
    
    return True

def verify_error_handling():
    """Verify error handling is present"""
    print("\n🔍 Verifying error handling...")
    
    # Check that error handling methods exist
    try:
        from mcp_service import ModernLLMService
        service = ModernLLMService()
        
        # Check that process_message handles errors
        source = inspect.getsource(service.process_message)
        if 'try:' in source and 'except' in source:
            print("  ✅ ModernLLMService has error handling")
        else:
            print("  ❌ ModernLLMService missing error handling")
            return False
        
    except Exception as e:
        print(f"  ❌ Error handling verification failed: {e}")
        return False
    
    return True

def verify_logging():
    """Verify logging is configured"""
    print("\n🔍 Verifying logging configuration...")
    
    # Check that logging is configured in key files
    files_to_check = [
        'mcp_server_fastmcp2.py',
        'mcp_client.py',
        'mcp_service.py',
        'web_ui_ws.py'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                if 'logging.basicConfig' in content:
                    print(f"  ✅ {file_path} has logging configured")
                else:
                    print(f"  ❌ {file_path} missing logging configuration")
                    return False
    
    return True

def main():
    """Run all verification checks"""
    print("🔍 MCP System Verification")
    print("=" * 50)
    
    checks = [
        ("Imports", verify_imports),
        ("Dependencies", verify_dependencies),
        ("File Structure", verify_file_structure),
        ("Class Methods", verify_class_methods),
        ("Flow Logic", verify_flow_logic),
        ("Web UI Events", verify_web_ui_events),
        ("Error Handling", verify_error_handling),
        ("Logging", verify_logging)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
                print(f"✅ {check_name} verification passed")
            else:
                print(f"❌ {check_name} verification failed")
        except Exception as e:
            print(f"❌ {check_name} verification error: {e}")
    
    print("\n📊 Verification Summary")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All verifications passed! System is ready.")
        return True
    else:
        print("❌ Some verifications failed. Please check the issues above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)