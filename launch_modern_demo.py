"""
Modern LLM Capabilities Launcher
===============================
Launches the enhanced MCP bot with modern LLM tool capabilities demonstration
"""

import os
import sys
import subprocess
import time
import webbrowser
from threading import Thread

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("💡 Install python-dotenv for .env file support: pip install python-dotenv")
except FileNotFoundError:
    print("💡 No .env file found - using system environment variables")

def check_requirements():
    """Check if required packages are installed"""
    try:
        import fastmcp
        import azure.identity
        import openai
        import flask
        import flask_socketio
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_azure_config():
    """Check if Azure OpenAI is configured"""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not endpoint or endpoint == "https://your-resource.openai.azure.com/":
        print("⚠️  Azure OpenAI not configured!")
        print("Please set the following environment variables:")
        print("  AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
        print("  AZURE_DEPLOYMENT_NAME=gpt-4o")
        print("  AZURE_CLIENT_ID=your-client-id (optional, for Azure AD)")
        print("  AZURE_CLIENT_SECRET=your-client-secret (optional)")
        print("  AZURE_TENANT_ID=your-tenant-id (optional)")
        return False
    
    print("✅ Azure OpenAI configuration found")
    return True

def check_api_credentials():
    """Check if API credentials are configured"""
    has_credentials = False
    
    # Check for basic auth
    if os.getenv('API_USERNAME') and os.getenv('API_PASSWORD'):
        print("✅ Basic authentication credentials found")
        has_credentials = True
    
    # Check for API key auth
    if os.getenv('API_KEY_NAME') and os.getenv('API_KEY_VALUE'):
        print("✅ API key authentication found")
        has_credentials = True
    
    if not has_credentials:
        print("⚠️  No API credentials found in environment!")
        print("Please set at least one of the following:")
        print("  Basic Auth: API_USERNAME, API_PASSWORD")
        print("  API Key: API_KEY_NAME, API_KEY_VALUE")
        print("  Login URL: LOGIN_URL (optional)")
        print("  Base URL: FORCE_BASE_URL (optional)")
        print("\nYou can also configure credentials at runtime using the web interface.")
        return False
    
    return True

def open_browser():
    """Open browser after a short delay"""
    time.sleep(3)
    webbrowser.open('http://localhost:5000')

def run_demo_scenarios():
    """Run the demo scenarios in the background"""
    try:
        from modern_llm_demo import run_demo
        import asyncio
        asyncio.run(run_demo())
    except Exception as e:
        print(f"Demo scenarios error: {e}")

def main():
    """Main launcher function"""
    print("🚀 Modern LLM Capabilities Demo Launcher")
    print("=" * 60)
    print("Demonstrating advanced LLM tool usage:")
    print("• Intelligent tool selection")
    print("• Complex tool chaining")
    print("• Adaptive tool usage")
    print("• Error handling and retry logic")
    print("• Reasoning about tool outputs")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check Azure configuration
    azure_ok = check_azure_config()
    
    # Check API credentials
    api_ok = check_api_credentials()
    
    if not azure_ok or not api_ok:
        print("\n" + "="*60)
        print("📋 SETUP REQUIRED")
        print("="*60)
        print("Please configure the missing credentials:")
        print("1. See ENVIRONMENT_SETUP.md for detailed instructions")
        print("2. Or use the web interface to configure at runtime")
        print("3. Or set environment variables and restart")
        print("="*60)
        
        response = input("Continue anyway? (y/N): ").lower()
        if response != 'y':
            sys.exit(1)
    
    print("\n🔧 Starting Modern LLM Demo...")
    print("📱 The web interface will open at: http://localhost:5000")
    print("🧪 Try these demo queries:")
    print("   • 'Check my account balance and recent transactions'")
    print("   • 'Transfer money and invest in stocks'")
    print("   • 'Analyze my spending and recommend budget changes'")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Open browser in background
    browser_thread = Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run demo scenarios in background
    demo_thread = Thread(target=run_demo_scenarios)
    demo_thread.daemon = True
    demo_thread.start()
    
    # Start the web UI
    try:
        from web_ui_ws import app, socketio
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Shutting down Modern LLM Demo...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
