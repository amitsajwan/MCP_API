#!/usr/bin/env python3
"""
Enhanced MCP System Startup Script
Starts the complete system with proper error checking and diagnostics
"""

import asyncio
import subprocess
import sys
import time
import os
import requests
import logging
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("system_startup")

def check_port(port: int, service_name: str) -> bool:
    """Check if a port is available or occupied."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(('localhost', port))
        if result == 0:
            logger.info(f"✅ {service_name} is running on port {port}")
            return True
        else:
            logger.warning(f"⚠️  Port {port} for {service_name} is not occupied")
            return False

def wait_for_service(url: str, service_name: str, max_attempts: int = 30) -> bool:
    """Wait for a service to become available."""
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ {service_name} is healthy at {url}")
                return True
        except requests.RequestException:
            pass
        
        if attempt < max_attempts - 1:
            logger.info(f"⏳ Waiting for {service_name} (attempt {attempt + 1}/{max_attempts})...")
            time.sleep(2)
    
    logger.error(f"❌ {service_name} failed to start after {max_attempts} attempts")
    return False

def start_mcp_server() -> Optional[subprocess.Popen]:
    """Start the MCP server."""
    logger.info("🚀 Starting MCP Server...")
    
    # Check if already running
    if check_port(9000, "MCP Server"):
        logger.info("MCP Server already running")
        return None
    
    try:
        process = subprocess.Popen([
            sys.executable, "mcp_server.py", 
            "--transport", "http", 
            "--host", "localhost", 
            "--port", "9000"
        ], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True
        )
        
        # Give it time to start
        time.sleep(3)
        
        if wait_for_service("http://localhost:9000", "MCP Server"):
            return process
        else:
            logger.error("MCP Server failed to start properly")
            if process.poll() is None:
                process.terminate()
            return None
            
    except Exception as e:
        logger.error(f"Failed to start MCP Server: {e}")
        return None

def start_chatbot_app() -> Optional[subprocess.Popen]:
    """Start the chatbot application."""
    logger.info("🤖 Starting Chatbot Application...")
    
    # Check if already running
    if check_port(9099, "Chatbot App"):
        logger.info("Chatbot App already running")
        return None
    
    try:
        process = subprocess.Popen([
            sys.executable, "chatbot_app.py"
        ], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True
        )
        
        # Give it time to start
        time.sleep(3)
        
        if wait_for_service("http://localhost:9099", "Chatbot App"):
            return process
        else:
            logger.error("Chatbot App failed to start properly")
            if process.poll() is None:
                process.terminate()
            return None
            
    except Exception as e:
        logger.error(f"Failed to start Chatbot App: {e}")
        return None

def check_configuration():
    """Check system configuration."""
    logger.info("🔧 Checking configuration...")
    
    # Import config
    try:
        from config import config
        config.validate()
        config.print_config()
    except Exception as e:
        logger.warning(f"Configuration issue: {e}")
        return False
    
    # Check OpenAPI specs
    if not os.path.exists("./openapi_specs"):
        logger.warning("⚠️  OpenAPI specs directory not found")
        return False
    
    # Check Azure OpenAI configuration
    if not config.AZURE_OPENAI_ENDPOINT:
        logger.warning("⚠️  Azure OpenAI endpoint not configured")
        logger.info("💡 Set AZURE_OPENAI_ENDPOINT in .env file")
        return False
    
    return True

def test_system():
    """Test the complete system."""
    logger.info("🧪 Testing system integration...")
    
    try:
        # Test MCP Server
        response = requests.get("http://localhost:9000/health", timeout=10)
        if response.status_code != 200:
            logger.error("❌ MCP Server health check failed")
            return False
        
        # Test Chatbot App
        response = requests.get("http://localhost:9099/health", timeout=10)
        if response.status_code != 200:
            logger.error("❌ Chatbot App health check failed")
            return False
        
        # Test MCP tools
        response = requests.get("http://localhost:9000/tools", timeout=10)
        if response.status_code == 200:
            tools = response.json().get("tools", [])
            logger.info(f"✅ Found {len(tools)} available tools")
        else:
            logger.warning("⚠️  Could not retrieve tools list")
        
        logger.info("✅ System integration test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ System test failed: {e}")
        return False

def main():
    """Main startup routine."""
    logger.info("=" * 60)
    logger.info("🚀 Enhanced MCP Financial API System Startup")
    logger.info("=" * 60)
    
    # Check configuration
    if not check_configuration():
        logger.error("❌ Configuration check failed")
        logger.info("💡 Please check your .env file and Azure OpenAI configuration")
        return 1
    
    processes = []
    
    try:
        # Start MCP Server
        mcp_process = start_mcp_server()
        if mcp_process:
            processes.append(("MCP Server", mcp_process))
        
        # Start Chatbot App
        chatbot_process = start_chatbot_app()
        if chatbot_process:
            processes.append(("Chatbot App", chatbot_process))
        
        # Test system
        if not test_system():
            logger.error("❌ System startup validation failed")
            return 1
        
        # Print access information
        logger.info("=" * 60)
        logger.info("🎉 System Started Successfully!")
        logger.info("=" * 60)
        logger.info("📱 Web Chat Interface: http://localhost:9099")
        logger.info("📚 API Documentation:  http://localhost:9000/docs")
        logger.info("🔍 Health Check:       http://localhost:9000/health")
        logger.info("🛠️  MCP Tools:          http://localhost:9000/tools")
        logger.info("=" * 60)
        logger.info("💡 Next Steps:")
        logger.info("   1. Open http://localhost:9099 in your browser")
        logger.info("   2. Set credentials if needed")
        logger.info("   3. Start chatting with your financial APIs!")
        logger.info("=" * 60)
        
        # Keep running
        if processes:
            logger.info("⏳ Press Ctrl+C to stop all services...")
            try:
                while True:
                    # Check if processes are still running
                    for name, process in processes:
                        if process.poll() is not None:
                            logger.warning(f"⚠️  {name} has stopped unexpectedly")
                    time.sleep(5)
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down services...")
                for name, process in processes:
                    logger.info(f"⏹️  Stopping {name}...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                logger.info("✅ All services stopped")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        # Cleanup any started processes
        for name, process in processes:
            try:
                process.terminate()
            except:
                pass
        return 1

if __name__ == "__main__":
    exit(main())
