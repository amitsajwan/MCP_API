#!/usr/bin/env python3
"""
Quick Start Script for FastMCP 2.0
This script helps diagnose and start your MCP setup properly.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("startup")


def check_environment():
    """Check if environment is properly set up"""
    logger.info("🔍 Checking environment...")
    
    issues = []
    
    # Check Python version
    if sys.version_info < (3.8,):
        issues.append(f"Python 3.8+ required, got {sys.version_info}")
    
    # Check required files
    required_files = [
        "mcp_server.py",
        "mcp_client.py", 
        "chatbot_app.py",
        "config.py"
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            issues.append(f"Missing required file: {file}")
    
    # Check OpenAPI directory
    openapi_dir = Path("./openapi_specs")
    if not openapi_dir.exists():
        logger.warning("⚠️ OpenAPI specs directory missing - creating it")
        openapi_dir.mkdir(exist_ok=True)
        
        # Create sample spec
        sample_spec = """
openapi: 3.0.0
info:
  title: Sample API
  version: 1.0.0
servers:
  - url: http://localhost:8080
paths:
  /health:
    get:
      summary: Health check
      responses:
        '200':
          description: OK
"""
        with open(openapi_dir / "sample.yaml", "w") as f:
            f.write(sample_spec.strip())
        logger.info("✅ Created sample OpenAPI spec")
    
    # Check for .env file
    if not os.path.exists(".env"):
        logger.warning("⚠️ No .env file found - creating template")
        env_template = """
# MCP Configuration
MCP_HOST=127.0.0.1
MCP_PORT=9000

# Chatbot Configuration  
CHATBOT_HOST=0.0.0.0
CHATBOT_PORT=8080

# Azure OpenAI Configuration (optional)
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=gpt-4
USE_AZURE_AD_TOKEN_PROVIDER=true

# Authentication (optional)
DEFAULT_LOGIN_URL=http://localhost:8080/auth/login
DEFAULT_USERNAME=
DEFAULT_PASSWORD=

# Logging
LOG_LEVEL=INFO
"""
        with open(".env", "w") as f:
            f.write(env_template.strip())
        logger.info("✅ Created .env template")
    
    if issues:
        logger.error("❌ Environment issues found:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    
    logger.info("✅ Environment check passed")
    return True


def install_dependencies():
    """Check and install required dependencies"""
    logger.info("📦 Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "websockets", 
        "mcp",
        "openai",
        "azure-identity",
        "pydantic",
        "python-dotenv",
        "pyyaml",
        "requests"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        logger.warning(f"⚠️ Missing packages: {missing}")
        logger.info("Installing missing packages...")
        
        import subprocess
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install"
            ] + missing)
            logger.info("✅ Dependencies installed")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install dependencies: {e}")
            return False
    else:
        logger.info("✅ All dependencies available")
    
    return True


async def test_mcp_connection():
    """Test MCP server connection"""
    logger.info("🔌 Testing MCP connection...")
    
    try:
        from mcp_client import MCPClient
        
        client = MCPClient()
        success = await client.connect_with_retry(max_retries=2)
        
        if success:
            tools = await client.list_tools()
            logger.info(f"✅ MCP connection successful - {len(tools)} tools available")
            
            # List tools for debugging
            if tools:
                logger.info("Available tools:")
                for tool in tools[:5]:  # Show first 5 tools
                    logger.info(f"  - {tool.name}: {tool.description}")
                if len(tools) > 5:
                    logger.info(f"  ... and {len(tools) - 5} more")
            
            await client.disconnect()
            return True
        else:
            logger.error("❌ Failed to connect to MCP server")
            return False
            
    except Exception as e:
        logger.error(f"❌ MCP connection test failed: {e}")
        return False


def start_chatbot():
    """Start the chatbot application"""
    logger.info("🚀 Starting chatbot application...")
    
    try:
        import uvicorn
        from chatbot_app import app, config
        
        logger.info(f"Starting server on {config.CHATBOT_HOST}:{config.CHATBOT_PORT}")
        uvicorn.run(
            app,
            host=config.CHATBOT_HOST,
            port=config.CHATBOT_PORT,
            log_level=config.LOG_LEVEL.lower()
        )
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
    except Exception as e:
        logger.error(f"❌ Failed to start chatbot: {e}")


async def main():
    """Main startup sequence"""
    logger.info("🚀 FastMCP 2.0 Quick Start")
    logger.info("=" * 50)
    
    # Step 1: Environment check
    if not check_environment():
        logger.error("❌ Environment check failed - please fix issues above")
        return False
    
    # Step 2: Dependencies
    if not install_dependencies():
        logger.error("❌ Dependency installation failed")
        return False
    
    # Step 3: Test MCP connection
    mcp_ok = await test_mcp_connection()
    if not mcp_ok:
        logger.warning("⚠️ MCP connection test failed - chatbot may have limited functionality")
        
        # Provide troubleshooting help
        logger.info("\n🛠️ MCP Troubleshooting:")
        logger.info("1. Check that mcp_server.py is in the current directory")
        logger.info("2. Verify OpenAPI specs are in ./openapi_specs/")
        logger.info("3. Check Python dependencies are installed")
        logger.info("4. Review logs above for specific errors")
        
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            return False
    
    # Step 4: Start chatbot
    logger.info("\n✅ All checks passed - starting chatbot...")
    logger.info("=" * 50)
    start_chatbot()
    
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if not result:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("👋 Startup cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        sys.exit(1)
