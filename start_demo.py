#!/usr/bin/env python3
"""
Demo Startup Script

This script starts both the MCP server and the FastAPI chatbot for a complete demo experience.
"""

import subprocess
import sys
import time
import threading
import signal
import os
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        ('fastmcp', 'fastmcp'), 
        ('requests', 'requests'), 
        ('yaml', 'pyyaml'), 
        ('fastapi', 'fastapi'), 
        ('uvicorn', 'uvicorn'), 
        ('pydantic', 'pydantic'), 
        ('aiohttp', 'aiohttp'), 
        ('openapi_spec_validator', 'openapi_spec_validator')
    ]
    
    missing_packages = []
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install them with:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_api_specs():
    """Check if API specification files exist"""
    api_specs_dir = Path("api_specs")
    required_specs = [
        "cash_api.yaml",
        "securities_api.yaml", 
        "cls_api.yaml",
        "mailbox_api.yaml"
    ]
    
    if not api_specs_dir.exists():
        print("❌ api_specs directory not found!")
        return False
    
    missing_specs = []
    for spec in required_specs:
        if not (api_specs_dir / spec).exists():
            missing_specs.append(spec)
    
    if missing_specs:
        print("❌ Missing API specification files:")
        for spec in missing_specs:
            print(f"   - api_specs/{spec}")
        return False
    
    return True

def start_mcp_server():
    """Start the MCP server in a separate process"""
    print("🚀 Starting MCP server...")
    try:
        process = subprocess.Popen(
            [sys.executable, "openapi_mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for server to start
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ MCP server started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ MCP server failed to start:")
            print(f"   STDOUT: {stdout}")
            print(f"   STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start MCP server: {e}")
        return None

def start_chatbot():
    """Start the FastAPI chatbot in a separate process"""
    print("🤖 Starting FastAPI chatbot...")
    try:
        process = subprocess.Popen(
            [sys.executable, "chatbot_app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for server to start
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ FastAPI chatbot started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ FastAPI chatbot failed to start:")
            print(f"   STDOUT: {stdout}")
            print(f"   STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start FastAPI chatbot: {e}")
        return None

def monitor_processes(mcp_process, chatbot_process):
    """Monitor the running processes and handle cleanup"""
    try:
        while True:
            # Check if processes are still running
            if mcp_process and mcp_process.poll() is not None:
                print("⚠️  MCP server stopped unexpectedly")
                break
                
            if chatbot_process and chatbot_process.poll() is not None:
                print("⚠️  FastAPI chatbot stopped unexpectedly")
                break
                
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        
        # Terminate processes
        if mcp_process:
            mcp_process.terminate()
            try:
                mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mcp_process.kill()
        
        if chatbot_process:
            chatbot_process.terminate()
            try:
                chatbot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chatbot_process.kill()
        
        print("✅ Servers stopped")

def main():
    """Main function to start the demo"""
    print("🎯 OpenAPI MCP Server Demo")
    print("=" * 50)
    
    # Check dependencies
    print("\n1️⃣ Checking dependencies...")
    if not check_dependencies():
        return
    
    # Check API specs
    print("\n2️⃣ Checking API specifications...")
    if not check_api_specs():
        return
    
    print("✅ All checks passed!")
    
    # Start MCP server
    print("\n3️⃣ Starting servers...")
    mcp_process = start_mcp_server()
    if not mcp_process:
        print("❌ Cannot continue without MCP server")
        return
    
    # Start FastAPI chatbot
    chatbot_process = start_chatbot()
    if not chatbot_process:
        print("❌ Cannot continue without FastAPI chatbot")
        mcp_process.terminate()
        return
    
    # Show success message
    print("\n🎉 Demo is ready!")
    print("=" * 50)
    print("📱 FastAPI Chatbot: http://localhost:8080")
    print("🔧 MCP Server: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8080/docs")
    print("\n💡 Try these example queries:")
    print("   - 'Show me all pending payments that need approval'")
    print("   - 'What's my current portfolio value?'")
    print("   - 'Are there any CLS settlements pending?'")
    print("   - 'Do I have any unread messages?'")
    print("   - 'Give me a summary of all financial activities'")
    print("\n🛑 Press Ctrl+C to stop the servers")
    
    # Monitor processes
    try:
        monitor_processes(mcp_process, chatbot_process)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
