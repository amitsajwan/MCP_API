#!/usr/bin/env python3
"""
FastMCP Chatbot Launcher
A comprehensive launcher script for the FastMCP chatbot system.
"""

import asyncio
import argparse
import logging
import os
import sys
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

from fastmcp_config import FastMCPConfig, setup_logging

class FastMCPChatbotLauncher:
    """Launcher for the FastMCP chatbot system."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = FastMCPConfig(config_file)
        self.server_process: Optional[subprocess.Popen] = None
        self.web_process: Optional[subprocess.Popen] = None
        self.running = False
        
        # Setup logging
        setup_logging()
        self.logger = logging.getLogger("launcher")
    
    def start_server(self) -> bool:
        """Start the FastMCP server."""
        try:
            self.logger.info("🚀 Starting FastMCP server...")
            
            cmd = [
                sys.executable,
                self.config.client.server_script,
                "--transport", self.config.server.transport,
                "--host", self.config.server.host,
                "--port", str(self.config.server.port)
            ]
            
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment to check if server started successfully
            time.sleep(2)
            
            if self.server_process.poll() is None:
                self.logger.info("✅ FastMCP server started successfully")
                return True
            else:
                stdout, stderr = self.server_process.communicate()
                self.logger.error(f"❌ FastMCP server failed to start: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error starting FastMCP server: {e}")
            return False
    
    def start_web_app(self) -> bool:
        """Start the web application."""
        try:
            self.logger.info("🌐 Starting web application...")
            
            cmd = [
                sys.executable,
                "fastmcp_web_app.py"
            ]
            
            self.web_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment to check if web app started successfully
            time.sleep(3)
            
            if self.web_process.poll() is None:
                self.logger.info("✅ Web application started successfully")
                return True
            else:
                stdout, stderr = self.web_process.communicate()
                self.logger.error(f"❌ Web application failed to start: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error starting web application: {e}")
            return False
    
    def stop_server(self):
        """Stop the FastMCP server."""
        if self.server_process and self.server_process.poll() is None:
            self.logger.info("🛑 Stopping FastMCP server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.logger.info("✅ FastMCP server stopped")
    
    def stop_web_app(self):
        """Stop the web application."""
        if self.web_process and self.web_process.poll() is None:
            self.logger.info("🛑 Stopping web application...")
            self.web_process.terminate()
            try:
                self.web_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.web_process.kill()
            self.logger.info("✅ Web application stopped")
    
    def stop_all(self):
        """Stop all processes."""
        self.running = False
        self.stop_web_app()
        self.stop_server()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.stop_all()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self, mode: str = "full"):
        """Run the chatbot system."""
        self.logger.info("🚀 Starting FastMCP Chatbot System")
        self.logger.info(f"Configuration: {self.config.to_dict()}")
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        try:
            if mode in ["full", "server"]:
                if not self.start_server():
                    self.logger.error("Failed to start server, exiting...")
                    return False
            
            if mode in ["full", "web"]:
                if not self.start_web_app():
                    self.logger.error("Failed to start web app, exiting...")
                    return False
            
            self.running = True
            
            if mode == "full":
                self.logger.info("🎉 FastMCP Chatbot System is running!")
                self.logger.info(f"🌐 Web UI: http://{self.config.web.host}:{self.config.web.port}")
                self.logger.info("Press Ctrl+C to stop")
                
                # Keep running until interrupted
                try:
                    while self.running:
                        time.sleep(1)
                        
                        # Check if processes are still running
                        if self.server_process and self.server_process.poll() is not None:
                            self.logger.error("Server process died, restarting...")
                            if not self.start_server():
                                break
                        
                        if self.web_process and self.web_process.poll() is not None:
                            self.logger.error("Web process died, restarting...")
                            if not self.start_web_app():
                                break
                                
                except KeyboardInterrupt:
                    self.logger.info("Received interrupt signal")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error running chatbot system: {e}")
            return False
        finally:
            self.stop_all()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="FastMCP Chatbot Launcher")
    parser.add_argument("--mode", choices=["full", "server", "web"], default="full",
                       help="Mode to run: full (server + web), server only, or web only")
    parser.add_argument("--config", type=str, help="Configuration file path")
    parser.add_argument("--port", type=int, help="Web application port")
    parser.add_argument("--host", type=str, help="Web application host")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Create launcher
    launcher = FastMCPChatbotLauncher(args.config)
    
    # Override config with command line arguments
    if args.port:
        launcher.config.web.port = args.port
    if args.host:
        launcher.config.web.host = args.host
    if args.debug:
        launcher.config.web.debug = True
        launcher.config.logging.level = "DEBUG"
        setup_logging()
    
    # Run the system
    success = launcher.run(args.mode)
    
    if success:
        print("✅ FastMCP Chatbot System completed successfully")
        sys.exit(0)
    else:
        print("❌ FastMCP Chatbot System failed")
        sys.exit(1)

if __name__ == "__main__":
    main()