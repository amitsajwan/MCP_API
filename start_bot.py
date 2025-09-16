#!/usr/bin/env python3
"""
Start MCP Bot
=============
Quick way to start my personal API assistant
"""

import sys
import os

def main():
    print("🤖 MCP Bot - Personal API Assistant")
    print("=" * 40)
    print()
    print("Choose how you want to run me:")
    print()
    print("1. Web Interface (Recommended)")
    print("   - Nice UI in your browser")
    print("   - Easy to use")
    print("   - http://localhost:5000")
    print()
    print("2. Command Line (Full Version)")
    print("   - Needs Azure setup")
    print("   - More powerful")
    print()
    print("3. MCP OpenAPI Server")
    print("   - Direct MCP server")
    print("   - For development/testing")
    print()
    
    while True:
        choice = input("Pick 1, 2, or 3: ").strip()
        
        if choice == "1":
            print("\n🚀 Starting web interface...")
            print("Open http://localhost:5000 in your browser")
            print("Press Ctrl+C to stop")
            print()
            os.system("python web_ui_ws.py")
            break
            
        elif choice == "2":
            print("\n🚀 Starting full command line version...")
            print("Make sure you have Azure credentials set up!")
            print("Press Ctrl+C to stop")
            print()
            os.system("python intelligent_bot.py")
            break
            
        elif choice == "3":
            print("\n🚀 Starting MCP OpenAPI server...")
            print("This runs the MCP server directly")
            print("Press Ctrl+C to stop")
            print()
            os.system("python mcp_openapi_server.py openapi_specs/cash_api.yaml")
            break
            
        else:
            print("Please pick 1, 2, or 3")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Oops, something went wrong: {e}")