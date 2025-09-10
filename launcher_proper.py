#!/usr/bin/env python3
"""
Proper MCP System Launcher
This script starts the complete MCP system:
1. MCP Server (stdio transport)
2. Chatbot App (WebSocket UI)
"""

import asyncio
import subprocess
import sys
import time
import logging
import signal
import os
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_launcher")

class MCPSystemLauncher:
    """Launches and manages the complete MCP system."""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.running = False
        
    def start_mcp_server(self) -> subprocess.Popen:
        """Start the MCP server with stdio transport."""
        logger.info("🚀 Starting MCP Server...")
        
        # Start MCP server as a subprocess
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
                logger.info("✅ MCP Server started successfully")
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
    
    def start_system(self):
        """Start the complete MCP system."""
        try:
            logger.info("🚀 Starting Complete MCP System...")
            logger.info("=" * 50)
            
            # Start MCP Server
            mcp_server = self.start_mcp_server()
            self.processes.append(mcp_server)
            
            # Start Chatbot App
            chatbot_app = self.start_chatbot_app()
            self.processes.append(chatbot_app)
            
            self.running = True
            
            logger.info("=" * 50)
            logger.info("✅ Complete MCP System Started Successfully!")
            logger.info("")
            logger.info("🌐 Chatbot UI: http://localhost:8000")
            logger.info("📊 System Status:")
            logger.info(f"   - MCP Server: {'✅ Running' if mcp_server.poll() is None else '❌ Stopped'}")
            logger.info(f"   - Chatbot App: {'✅ Running' if chatbot_app.poll() is None else '❌ Stopped'}")
            logger.info("")
            logger.info("💡 Usage:")
            logger.info("   1. Open http://localhost:8000 in your browser")
            logger.info("   2. Start chatting with the MCP-powered chatbot")
            logger.info("   3. The chatbot will use MCP tools to process your requests")
            logger.info("")
            logger.info("🛑 Press Ctrl+C to stop the system")
            logger.info("=" * 50)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start system: {e}")
            self.stop_system()
            return False
    
    def stop_system(self):
        """Stop all processes in the system."""
        logger.info("🛑 Stopping MCP System...")
        
        for process in self.processes:
            try:
                if process.poll() is None:  # Process is still running
                    logger.info(f"Terminating process {process.pid}")
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Force killing process {process.pid}")
                        process.kill()
                        process.wait()
                        
            except Exception as e:
                logger.error(f"Error stopping process {process.pid}: {e}")
        
        self.processes.clear()
        self.running = False
        logger.info("✅ MCP System stopped")
    
    def monitor_system(self):
        """Monitor the system and restart if needed."""
        try:
            while self.running:
                time.sleep(5)  # Check every 5 seconds
                
                # Check if any process has died
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        logger.error(f"❌ Process {process.pid} has stopped unexpectedly")
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

def main():
    """Main entry point."""
    global launcher
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check if required files exist
    required_files = ["mcp_server.py", "chatbot_app.py", "mcp_client_proper_working.py"]
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"❌ Missing required files: {missing_files}")
        logger.error("Please ensure all required files are present in the current directory")
        return 1
    
    # Create and start launcher
    launcher = MCPSystemLauncher()
    
    try:
        if launcher.start_system():
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