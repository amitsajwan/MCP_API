#!/usr/bin/env python3
"""
Launcher - Clean Implementation
Simplified launcher for the MCP API project.
"""

import subprocess
import sys
import time
import threading
import os
import argparse
import signal
from pathlib import Path
from typing import List, Optional

from config import config


class Launcher:
    """Clean launcher implementation."""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n🛑 Shutting down...")
        self.running = False
        self.stop_all()
        sys.exit(0)
    
    def start_mock_server(self) -> Optional[subprocess.Popen]:
        """Start the mock API server."""
        if not self.running:
            return None
        
        print("🚀 Starting Mock API Server...")
        try:
            process = subprocess.Popen([
                sys.executable, "mock_server.py",
                "--host", config.MOCK_API_HOST,
                "--port", str(config.MOCK_API_PORT)
            ])
            self.processes.append(("Mock API Server", process))
            print(f"✅ Mock API Server started on {config.get_mock_url()}")
            return process
        except Exception as e:
            print(f"❌ Failed to start Mock API Server: {e}")
            return None
    
    def start_mcp_server(self) -> Optional[subprocess.Popen]:
        """Start the MCP server with HTTP transport for launcher management."""
        if not self.running:
            return None
        
        print("🚀 Starting MCP Server...")
        try:
            # Use HTTP mode for launcher so we can manage the process
            # The MCP client will connect via stdio when needed
            process = subprocess.Popen([
                sys.executable, "mcp_server.py",
                "--transport", "http",
                "--host", config.MCP_HOST,
                "--port", str(config.MCP_PORT)
            ])
            self.processes.append(("MCP Server", process))
            print(f"✅ MCP Server started on {config.get_mcp_url()}")
            print("💡 MCP Client can connect via stdio when needed")
            return process
        except Exception as e:
            print(f"❌ Failed to start MCP Server: {e}")
            return None
    
    def start_chatbot(self) -> Optional[subprocess.Popen]:
        """Start the chatbot application."""
        if not self.running:
            return None
        
        print("🚀 Starting Chatbot Application...")
        try:
            process = subprocess.Popen([
                sys.executable, "chatbot_app.py"
            ])
            self.processes.append(("Chatbot", process))
            print(f"✅ Chatbot started on {config.get_chatbot_url()}")
            print(f"🌐 Web UI available at: {config.get_chatbot_url()}")
            print(f"📄 Simple UI available at: {config.get_chatbot_url()}/")
            return process
        except Exception as e:
            print(f"❌ Failed to start Chatbot: {e}")
            return None
    
    def start_frontend_dev(self) -> Optional[subprocess.Popen]:
        """Frontend is served by FastAPI - no separate dev server needed."""
        print("ℹ️  Frontend is integrated with FastAPI chatbot app")
        print(f"🌐 Simple UI served at: {config.get_chatbot_url()}/")
        print("⚠️  No separate frontend dev server needed")
        return None
    
    def build_frontend(self) -> bool:
        """Frontend is static HTML - no build process needed."""
        print("ℹ️  Frontend is static HTML (simple_ui.html)")
        print("✅ No build process required - ready for production")
        return True
    
    def wait_for_services(self, timeout: int = 30):
        """Wait for services to be ready."""
        print("⏳ Waiting for services to be ready...")
        time.sleep(5)  # Give services time to start
    
    def print_status(self):
        """Print current status."""
        print("\n" + "="*60)
        print("🎯 MCP API Project Status")
        print("="*60)
        print(f"📊 Configuration:")
        print(f"   MCP Server:     {config.get_mcp_url()}")
        print(f"   Chatbot:        {config.get_chatbot_url()}")
        print(f"   Mock API:       {config.get_mock_url()}")
        print(f"   OpenAPI Dir:    {config.OPENAPI_DIR}")
        print(f"   Mock All:       {config.MOCK_ALL}")
        print(f"   Auto Mock:      {config.AUTO_MOCK_FALLBACK}")
        print(f"   Log Level:      {config.LOG_LEVEL}")
        print("\n🌐 Access URLs:")
        print(f"   Web UI:         {config.get_chatbot_url()}/")
        print(f"   WebSocket:      {config.get_websocket_url()}")
        print(f"   Mock API:       {config.get_mock_url()}")
        print(f"   MCP Server:     {config.get_mcp_url()}")
        print("\n💡 Tips:")
        print("   - Use Ctrl+C to stop all services")
        print("   - Open the Web UI URL in your browser")
        print("   - Check logs for detailed information")
        print("   - Configure settings in .env file")
        print("="*60)
    
    def stop_all(self):
        """Stop all running processes."""
        print("\n🛑 Stopping all services...")
        for name, process in self.processes:
            try:
                print(f"   Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"   Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"   Error stopping {name}: {e}")
        self.processes.clear()
        print("✅ All services stopped")
    
    def run_dev_mode(self, with_mock: bool = True, with_frontend: bool = False):
        """Run in development mode."""
        print("🚀 Starting Development Mode...")
        
        # Start mock server if requested
        if with_mock:
            self.start_mock_server()
        
        # Start MCP server
        self.start_mcp_server()
        
        # Start chatbot (includes frontend)
        self.start_chatbot()
        
        # Note about frontend
        if with_frontend:
            self.start_frontend_dev()
        
        # Wait for services
        self.wait_for_services()
        
        # Print status
        self.print_status()
        
        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_all()
    
    def run_prod_mode(self, with_mock: bool = True):
        """Run in production mode."""
        print("🚀 Starting Production Mode...")
        
        # Build frontend
        self.build_frontend()
        
        # Start mock server if requested
        if with_mock:
            self.start_mock_server()
        
        # Start MCP server
        self.start_mcp_server()
        
        # Start chatbot
        self.start_chatbot()
        
        # Wait for services
        self.wait_for_services()
        
        # Print status
        self.print_status()
        
        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_all()


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
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install them with:")
        print("   pip install -r requirements.txt")
        return False
    
    return True


def check_api_specs():
    """Check if API specification files exist."""
    api_specs_dir = Path(config.OPENAPI_DIR)
    if not api_specs_dir.exists():
        print(f"❌ OpenAPI directory not found: {api_specs_dir}")
        return False
    
    spec_files = list(api_specs_dir.glob("*.yaml"))
    if not spec_files:
        print(f"⚠️  No YAML files found in {api_specs_dir}")
        return False
    
    print(f"✅ Found {len(spec_files)} API specification(s):")
    for spec_file in spec_files:
        print(f"   - {spec_file.name}")
    
    # Check for UI file
    ui_file = Path("simple_ui.html")
    if ui_file.exists():
        print(f"✅ Found UI file: {ui_file.name}")
    else:
        print(f"⚠️  UI file not found: {ui_file.name}")
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MCP API Project Launcher")
    parser.add_argument("--mode", choices=["dev", "prod"], default="dev",
                       help="Run mode (default: dev)")
    parser.add_argument("--no-mock", action="store_true",
                       help="Don't start mock API server")
    parser.add_argument("--no-frontend", action="store_true",
                       help="Don't show frontend information (frontend is integrated)")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check dependencies and configuration")
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check API specs
    if not check_api_specs():
        print("⚠️  Continuing without API specifications...")
    
    # Validate configuration
    if not config.validate():
        print("❌ Configuration validation failed")
        print("💡 Copy config.env.example to .env and configure the required values")
        return 1
    
    # Print configuration
    config.print_config()
    
    if args.check_only:
        print("✅ All checks passed!")
        return 0
    
    # Create launcher
    launcher = Launcher()
    
    try:
        if args.mode == "dev":
            launcher.run_dev_mode(
                with_mock=not args.no_mock,
                with_frontend=not args.no_frontend
            )
        else:  # prod
            launcher.run_prod_mode(with_mock=not args.no_mock)
    except Exception as e:
        print(f"❌ Launcher error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
