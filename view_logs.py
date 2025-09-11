#!/usr/bin/env python3
"""
Log Viewer for MCP System
========================
View logs from all components in real-time
"""

import os
import time
import subprocess
import sys
from pathlib import Path

def view_logs():
    """View logs from all MCP components"""
    log_files = [
        'web_ui.log',
        'mcp_service.log', 
        'mcp_client.log',
        'mcp_server.log'
    ]
    
    print("🔍 MCP System Log Viewer")
    print("=" * 50)
    
    # Check which log files exist
    existing_logs = []
    for log_file in log_files:
        if Path(log_file).exists():
            existing_logs.append(log_file)
            print(f"✅ Found: {log_file}")
        else:
            print(f"❌ Missing: {log_file}")
    
    if not existing_logs:
        print("\n❌ No log files found. Start the system first!")
        return
    
    print(f"\n📊 Found {len(existing_logs)} log files")
    print("\nChoose an option:")
    print("1. View all logs (tail -f)")
    print("2. View specific log file")
    print("3. View recent logs (last 50 lines)")
    print("4. Search logs for specific text")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        # View all logs with tail -f
        cmd = f"tail -f {' '.join(existing_logs)}"
        print(f"\n🔄 Running: {cmd}")
        print("Press Ctrl+C to stop")
        try:
            subprocess.run(cmd, shell=True)
        except KeyboardInterrupt:
            print("\n👋 Stopped viewing logs")
    
    elif choice == "2":
        # View specific log file
        print("\nAvailable log files:")
        for i, log_file in enumerate(existing_logs, 1):
            print(f"{i}. {log_file}")
        
        try:
            file_choice = int(input("Enter file number: ")) - 1
            if 0 <= file_choice < len(existing_logs):
                log_file = existing_logs[file_choice]
                print(f"\n📄 Viewing: {log_file}")
                print("Press Ctrl+C to stop")
                subprocess.run(f"tail -f {log_file}", shell=True)
            else:
                print("❌ Invalid choice")
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Stopped")
    
    elif choice == "3":
        # View recent logs
        print("\n📄 Recent logs (last 50 lines):")
        for log_file in existing_logs:
            print(f"\n--- {log_file} ---")
            try:
                result = subprocess.run(f"tail -50 {log_file}", shell=True, capture_output=True, text=True)
                print(result.stdout)
            except Exception as e:
                print(f"Error reading {log_file}: {e}")
    
    elif choice == "4":
        # Search logs
        search_term = input("Enter search term: ").strip()
        if search_term:
            print(f"\n🔍 Searching for '{search_term}' in all logs:")
            for log_file in existing_logs:
                print(f"\n--- {log_file} ---")
                try:
                    result = subprocess.run(f"grep -i '{search_term}' {log_file}", shell=True, capture_output=True, text=True)
                    if result.stdout:
                        print(result.stdout)
                    else:
                        print("No matches found")
                except Exception as e:
                    print(f"Error searching {log_file}: {e}")
        else:
            print("❌ No search term provided")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    view_logs()
