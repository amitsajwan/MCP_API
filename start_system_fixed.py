#!/usr/bin/env python3
"""
Fixed System Startup Script
Properly orchestrates the complete MCP system with error handling and diagnostics.
"""

import asyncio
import subprocess
import sys
import time
import os
import requests
import logging
import signal
import psutil
from typing import Optional, List, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("system_startup")

class SystemManager:
    """Manages the complete MCP system startup and shutdown."""
    
    def __init__(self):
        self.processes: List[Tuple[str, subprocess.Popen]] = []
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("\n🛑 Shutting down system...")
        self.running = False
        self.stop_all()
        sys.exit(0)
    
    def check_port(self, port: int, service_name: str) -> bool:
        """Check if a port is available or occupied."""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    logger.info(f"✅ {service_name} is running on port {port}")
                    return True
            logger.warning(f"⚠️  Port {port} for {service_name} is not occupied")
            return False
        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
            return False
    
    def wait_for_service(self, url: str, service_name: str, max_attempts: int = 30) -> bool:
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
    
    def start_mcp_server(self) -> Optional[subprocess.Popen]:
        """Start the MCP server."""
        logger.info("🚀 Starting MCP Server...")
        
        # Check if already running
        if self.check_port(9000, "MCP Server"):
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
            
            self.processes.append(("MCP Server", process))
            
            # Give it time to start
            time.sleep(3)
            
            if self.wait_for_service("http://localhost:9000", "MCP Server"):
                logger.info("✅ MCP Server started successfully")
                return process
            else:
                logger.error("❌ MCP Server failed to start properly")
                if process.poll() is None:
                    process.terminate()
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to start MCP Server: {e}")
            return None
    
    def start_chatbot_app(self) -> Optional[subprocess.Popen]:
        """Start the chatbot application."""
        logger.info("🤖 Starting Chatbot Application...")
        
        # Check if already running
        if self.check_port(9099, "Chatbot App"):
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
            
            self.processes.append(("Chatbot App", process))
            
            # Give it time to start
            time.sleep(5)
            
            if self.wait_for_service("http://localhost:9099", "Chatbot App"):
                logger.info("✅ Chatbot App started successfully")
                return process
            else:
                logger.error("❌ Chatbot App failed to start properly")
                if process.poll() is None:
                    process.terminate()
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to start Chatbot App: {e}")
            return None
    
    def test_system_integration(self) -> bool:
        """Test the complete system integration."""
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
            
            # Test chatbot tools endpoint
            response = requests.get("http://localhost:9099/api/tools", timeout=10)
            if response.status_code == 200:
                tools = response.json().get("tools", [])
                logger.info(f"✅ Chatbot can access {len(tools)} tools")
            else:
                logger.warning("⚠️  Could not retrieve tools from chatbot")
            
            logger.info("✅ System integration test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ System test failed: {e}")
            return False
    
    def print_system_status(self):
        """Print current system status."""
        logger.info("=" * 60)
        logger.info("🎯 MCP System Status")
        logger.info("=" * 60)
        
        # Check service status
        mcp_healthy = self.check_port(9000, "MCP Server")
        chatbot_healthy = self.check_port(9099, "Chatbot App")
        
        logger.info(f"📊 Service Status:")
        logger.info(f"   MCP Server:     {'✅ Healthy' if mcp_healthy else '❌ Not Running'}")
        logger.info(f"   Chatbot App:    {'✅ Healthy' if chatbot_healthy else '❌ Not Running'}")
        
        logger.info(f"\n🌐 Access URLs:")
        logger.info(f"   Web UI:         http://localhost:9099/")
        logger.info(f"   WebSocket:      ws://localhost:9099/ws")
        logger.info(f"   MCP Server:     http://localhost:9000/")
        logger.info(f"   MCP Health:     http://localhost:9000/health")
        logger.info(f"   MCP Tools:      http://localhost:9000/tools")
        logger.info(f"   MCP Docs:       http://localhost:9000/docs")
        
        logger.info(f"\n💡 Usage:")
        logger.info(f"   - Open http://localhost:9099/ in your browser")
        logger.info(f"   - Use the WebSocket interface for real-time chat")
        logger.info(f"   - Check MCP server documentation at /docs")
        logger.info(f"   - Use Ctrl+C to stop all services")
        logger.info("=" * 60)
    
    def stop_all(self):
        """Stop all running processes."""
        logger.info("🛑 Stopping all services...")
        for name, process in self.processes:
            try:
                logger.info(f"   Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.info(f"   Force killing {name}...")
                process.kill()
            except Exception as e:
                logger.error(f"   Error stopping {name}: {e}")
        self.processes.clear()
        logger.info("✅ All services stopped")
    
    def run(self):
        """Run the complete system."""
        logger.info("=" * 60)
        logger.info("🚀 Starting MCP Financial API System")
        logger.info("=" * 60)
        
        try:
            # Start MCP Server
            mcp_process = self.start_mcp_server()
            if not mcp_process and not self.check_port(9000, "MCP Server"):
                logger.error("❌ Failed to start MCP Server")
                return 1
            
            # Start Chatbot App
            chatbot_process = self.start_chatbot_app()
            if not chatbot_process and not self.check_port(9099, "Chatbot App"):
                logger.error("❌ Failed to start Chatbot App")
                return 1
            
            # Test system integration
            if not self.test_system_integration():
                logger.error("❌ System integration test failed")
                return 1
            
            # Print status
            self.print_system_status()
            
            # Keep running
            logger.info("⏳ System is running. Press Ctrl+C to stop...")
            try:
                while self.running:
                    # Check if processes are still running
                    for name, process in self.processes:
                        if process.poll() is not None:
                            logger.warning(f"⚠️  {name} has stopped unexpectedly")
                    time.sleep(5)
            except KeyboardInterrupt:
                pass
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ System startup failed: {e}")
            return 1
        finally:
            self.stop_all()


def main():
    """Main entry point."""
    manager = SystemManager()
    return manager.run()


if __name__ == "__main__":
    exit(main())