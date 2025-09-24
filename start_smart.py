#!/usr/bin/env python3
"""
Start Smart MCP System
======================
Startup script for the Smart MCP system with API relationship intelligence.
"""

import os
import sys
import subprocess
import time
import signal
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'fastmcp',
        'flask',
        'flask-socketio',
        'httpx',
        'pyyaml'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        logger.info("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_openapi_specs():
    """Check if OpenAPI specifications exist"""
    openapi_dir = Path("./openapi_specs")
    if not openapi_dir.exists():
        logger.error("OpenAPI specifications directory not found: ./openapi_specs")
        return False
    
    yaml_files = list(openapi_dir.glob("*.yaml"))
    if not yaml_files:
        logger.error("No YAML files found in ./openapi_specs")
        return False
    
    logger.info(f"Found {len(yaml_files)} OpenAPI specification files:")
    for spec_file in yaml_files:
        logger.info(f"  - {spec_file.name}")
    return True

def start_server():
    """Start the Smart MCP server"""
    logger.info("🧠 Starting Smart MCP server...")
    
    try:
        # Start the server in stdio mode
        server_process = subprocess.Popen([
            sys.executable, "smart_mcp_server.py", "--transport", "stdio"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        logger.info(f"✅ Smart MCP server started with PID {server_process.pid}")
        return server_process
        
    except Exception as e:
        logger.error(f"❌ Failed to start Smart MCP server: {e}")
        return None

def start_web_ui():
    """Start the web UI"""
    logger.info("🌐 Starting Smart Web UI...")
    
    try:
        # Start the web UI
        web_process = subprocess.Popen([
            sys.executable, "smart_web_ui.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        logger.info(f"✅ Smart Web UI started with PID {web_process.pid}")
        return web_process
        
    except Exception as e:
        logger.error(f"❌ Failed to start web UI: {e}")
        return None

def main():
    """Main startup function"""
    logger.info("🧠 Starting Smart MCP System")
    logger.info("=" * 50)
    logger.info("Features:")
    logger.info("  🔐 JSESSIONID & API Key authentication")
    logger.info("  📊 Intelligent response truncation (100 items max)")
    logger.info("  🔗 API relationship understanding")
    logger.info("  🚀 Smart tool execution ordering")
    logger.info("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check OpenAPI specs
    if not check_openapi_specs():
        sys.exit(1)
    
    # Start components
    server_process = None
    web_process = None
    
    try:
        # Start Smart MCP server
        server_process = start_server()
        if not server_process:
            sys.exit(1)
        
        # Give server time to start
        time.sleep(2)
        
        # Start web UI
        web_process = start_web_ui()
        if not web_process:
            sys.exit(1)
        
        logger.info("🎉 Smart MCP System started successfully!")
        logger.info("🌐 Web UI: http://localhost:5002")
        logger.info("📡 Smart MCP Server: Running in stdio mode")
        logger.info("")
        logger.info("Key Features:")
        logger.info("  • Automatic JSESSIONID extraction and management")
        logger.info("  • API key authentication support")
        logger.info("  • Response truncation to prevent huge outputs")
        logger.info("  • Intelligent API call ordering based on relationships")
        logger.info("  • Real-time relationship visualization")
        logger.info("")
        logger.info("Press Ctrl+C to stop all services")
        
        # Wait for processes
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if server_process.poll() is not None:
                logger.error("❌ Smart MCP server stopped unexpectedly")
                break
            
            if web_process.poll() is not None:
                logger.error("❌ Web UI stopped unexpectedly")
                break
    
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    
    finally:
        # Cleanup processes
        if server_process:
            logger.info("🛑 Stopping Smart MCP server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
        
        if web_process:
            logger.info("🛑 Stopping web UI...")
            web_process.terminate()
            try:
                web_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                web_process.kill()
        
        logger.info("✅ Shutdown complete")

if __name__ == "__main__":
    main()