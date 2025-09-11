#!/usr/bin/env python3
"""
Stdio-Based MCP System Launcher
This launcher implements the recommended stdio-based MCP architecture:
- MCP Server runs with stdio transport
- MCP Client connects via stdio pipes
- Chatbot App uses proper MCP client
- No HTTP transport layer issues
"""

import asyncio
import subprocess
import sys
import time
import logging
import signal
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stdio_launcher")

class StdioMCPSystemLauncher:
    """Launches and manages the complete stdio-based MCP system."""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.running = False
        self.mcp_server_process: Optional[subprocess.Popen] = None
        self.chatbot_process: Optional[subprocess.Popen] = None
        
    def start_mcp_server_stdio(self) -> subprocess.Popen:
        """Start the MCP server with stdio transport."""
        logger.info("🚀 Starting MCP Server with stdio transport...")
        
        # Start MCP server as a subprocess with stdio transport
        cmd = [sys.executable, "mcp_server.py", "--transport", "stdio"]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            if process.poll() is None:
                logger.info("✅ MCP Server started successfully with stdio transport")
                return process
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ MCP Server failed to start: {stderr}")
                raise Exception(f"MCP Server failed to start: {stderr}")
                
        except Exception as e:
            logger.error(f"❌ Failed to start MCP Server: {e}")
            raise
    
    def start_chatbot_app(self) -> subprocess.Popen:
        """Start the chatbot application."""
        logger.info("🤖 Starting Chatbot Application...")
        
        # Start chatbot app as a subprocess
        cmd = [sys.executable, "chatbot_app.py"]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it a moment to start
            time.sleep(3)
            
            if process.poll() is None:
                logger.info("✅ Chatbot Application started successfully")
                return process
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ Chatbot Application failed to start: {stderr}")
                raise Exception(f"Chatbot Application failed to start: {stderr}")
                
        except Exception as e:
            logger.error(f"❌ Failed to start Chatbot Application: {e}")
            raise
    
    def start_mock_server(self) -> Optional[subprocess.Popen]:
        """Start the mock API server (optional)."""
        logger.info("🔧 Starting Mock API Server...")
        
        try:
            process = subprocess.Popen([
                sys.executable, "mock_server.py",
                "--host", "127.0.0.1",
                "--port", "9001"
            ])
            
            time.sleep(2)
            
            if process.poll() is None:
                logger.info("✅ Mock API Server started successfully")
                return process
            else:
                logger.warning("⚠️ Mock API Server failed to start (optional)")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to start Mock API Server (optional): {e}")
            return None
    
    def start_system(self, with_mock: bool = True):
        """Start the complete stdio-based MCP system."""
        try:
            logger.info("🚀 Starting Complete Stdio-Based MCP System...")
            logger.info("=" * 60)
            
            # Start MCP Server with stdio transport
            self.mcp_server_process = self.start_mcp_server_stdio()
            self.processes.append(("MCP Server (stdio)", self.mcp_server_process))
            
            # Start Mock Server (optional)
            if with_mock:
                mock_process = self.start_mock_server()
                if mock_process:
                    self.processes.append(("Mock API Server", mock_process))
            
            # Start Chatbot App
            self.chatbot_process = self.start_chatbot_app()
            self.processes.append(("Chatbot App", self.chatbot_process))
            
            self.running = True
            
            logger.info("=" * 60)
            logger.info("✅ Complete Stdio-Based MCP System Started Successfully!")
            logger.info("")
            logger.info("🏗️ Architecture:")
            logger.info("   Real Estate Agent Interface")
            logger.info("           ↓ (HTTP)")
            logger.info("    FastAPI Chatbot App")
            logger.info("           ↓ (stdio)")
            logger.info("        MCP Client")
            logger.info("           ↓ (stdio)")
            logger.info("        MCP Server")
            logger.info("           ↓ (HTTP)")
            logger.info("    Complex OpenAPI Services")
            logger.info("")
            logger.info("🌐 Access URLs:")
            logger.info("   - Chatbot UI: http://localhost:8000")
            logger.info("   - Mock API: http://127.0.0.1:9001 (if enabled)")
            logger.info("")
            logger.info("📊 System Status:")
            logger.info(f"   - MCP Server: {'✅ Running' if self.mcp_server_process.poll() is None else '❌ Stopped'}")
            logger.info(f"   - Chatbot App: {'✅ Running' if self.chatbot_process.poll() is None else '❌ Stopped'}")
            logger.info("")
            logger.info("💡 Usage:")
            logger.info("   1. Open http://localhost:8000 in your browser")
            logger.info("   2. Start chatting with the MCP-powered chatbot")
            logger.info("   3. The chatbot uses stdio-based MCP communication")
            logger.info("")
            logger.info("🛑 Press Ctrl+C to stop the system")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start system: {e}")
            self.stop_system()
            return False
    
    def stop_system(self):
        """Stop all processes in the system."""
        logger.info("🛑 Stopping Stdio-Based MCP System...")
        
        for name, process in self.processes:
            try:
                if process.poll() is None:  # Process is still running
                    logger.info(f"Terminating {name} (PID: {process.pid})")
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=5)
                        logger.info(f"✅ {name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Force killing {name} (PID: {process.pid})")
                        process.kill()
                        process.wait()
                        logger.info(f"✅ {name} force stopped")
                        
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        self.processes.clear()
        self.running = False
        self.mcp_server_process = None
        self.chatbot_process = None
        logger.info("✅ Stdio-Based MCP System stopped")
    
    def monitor_system(self):
        """Monitor the system and restart if needed."""
        try:
            while self.running:
                time.sleep(5)  # Check every 5 seconds
                
                # Check if any critical process has died
                critical_processes = [
                    ("MCP Server", self.mcp_server_process),
                    ("Chatbot App", self.chatbot_process)
                ]
                
                for name, process in critical_processes:
                    if process and process.poll() is not None:
                        logger.error(f"❌ Critical process {name} has stopped unexpectedly")
                        self.running = False
                        break
                        
        except KeyboardInterrupt:
            logger.info("🛑 Received shutdown signal")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Error monitoring system: {e}")
            self.running = False
        finally:
            self.stop_system()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("🛑 Received shutdown signal")
    if 'launcher' in globals():
        launcher.running = False

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        ('fastapi', 'fastapi'), 
        ('uvicorn', 'uvicorn'), 
        ('pydantic', 'pydantic'), 
        ('aiohttp', 'aiohttp'), 
        ('requests', 'requests'), 
        ('pyyaml', 'yaml'), 
        ('python-dotenv', 'dotenv'), 
        ('mcp', 'mcp'), 
        ('openai', 'openai')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        logger.error("❌ Missing required packages:")
        for package in missing_packages:
            logger.error(f"   - {package}")
        logger.error("\n💡 Install them with:")
        logger.error("   pip install -r requirements.txt")
        return False
    
    return True

def check_required_files():
    """Check if required files exist."""
    required_files = [
        "mcp_server.py",
        "chatbot_app.py", 
        "mcp_client_proper_working.py",
        "config.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"❌ Missing required files: {missing_files}")
        logger.error("Please ensure all required files are present in the current directory")
        return False
    
    return True

def main():
    """Main entry point."""
    global launcher
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check required files
    if not check_required_files():
        return 1
    
    # Create and start launcher
    launcher = StdioMCPSystemLauncher()
    
    try:
        if launcher.start_system(with_mock=True):
            launcher.monitor_system()
        else:
            logger.error("❌ Failed to start system")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1
    finally:
        launcher.stop_system()
    
    return 0

if __name__ == "__main__":
    exit(main())