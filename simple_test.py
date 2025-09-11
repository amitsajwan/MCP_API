#!/usr/bin/env python3
"""
Simple test for FastMCP Chatbot components
"""

import asyncio
import sys
import subprocess
import time
import json

def test_server_startup():
    """Test if the server can start up."""
    print("🧪 Testing server startup...")
    try:
        # Start server process
        process = subprocess.Popen(
            [sys.executable, "fastmcp_chatbot_server.py", "--transport", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Server started successfully")
            process.terminate()
            process.wait(timeout=5)
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Server failed to start: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def test_web_app_import():
    """Test if the web app can be imported."""
    print("🧪 Testing web app import...")
    try:
        import fastmcp_web_app
        print("✅ Web app imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing web app: {e}")
        return False

def test_config_system():
    """Test if the config system works."""
    print("🧪 Testing config system...")
    try:
        from fastmcp_config import get_config, setup_logging
        config = get_config()
        setup_logging()
        print(f"✅ Config system working - Web port: {config.web.port}")
        return True
    except Exception as e:
        print(f"❌ Error testing config: {e}")
        return False

def test_client_import():
    """Test if the client can be imported."""
    print("🧪 Testing client import...")
    try:
        from fastmcp_chatbot_client import FastMCPChatbotClient
        client = FastMCPChatbotClient()
        print("✅ Client imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing client: {e}")
        return False

def test_launcher_import():
    """Test if the launcher can be imported."""
    print("🧪 Testing launcher import...")
    try:
        from launch_fastmcp_chatbot import FastMCPChatbotLauncher
        launcher = FastMCPChatbotLauncher()
        print("✅ Launcher imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing launcher: {e}")
        return False

def main():
    """Run all simple tests."""
    print("🚀 FastMCP Chatbot Simple Test Suite")
    print("=" * 40)
    
    tests = [
        test_config_system,
        test_client_import,
        test_launcher_import,
        test_web_app_import,
        test_server_startup,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 40)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)