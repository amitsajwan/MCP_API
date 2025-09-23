#!/usr/bin/env python3
"""
Test Dependency Flow
===================
Simple test to demonstrate the dependency-aware MCP server flow.
"""

import asyncio
import json
import subprocess
import sys
from mcp.client import Client
from mcp.client.stdio import stdio_client

async def test_dependency_flow():
    """Test the dependency flow with the MCP server"""
    
    print("🧪 Testing Dependency-Aware MCP Server Flow")
    print("=" * 50)
    
    try:
        # Connect to the MCP server
        async with stdio_client("python", ["simple_dependency_mcp_server.py"]) as (read, write):
            client = Client("test-client")
            await client.initialize(read, write)
            
            print("✅ Connected to MCP server")
            
            # Test 1: Get users
            print("\n📞 Test 1: Getting users...")
            result = await client.call_tool("get_users", {})
            print("Result:", result.content[0].text)
            
            # Test 2: Get accounts
            print("\n📞 Test 2: Getting accounts...")
            result = await client.call_tool("get_accounts", {})
            print("Result:", result.content[0].text)
            
            # Test 3: Try to get mails without account_id (should show dependency)
            print("\n📞 Test 3: Trying to get mails without account_id...")
            result = await client.call_tool("get_mails", {})
            print("Result:", result.content[0].text)
            
            # Test 4: Get mails with account_id
            print("\n📞 Test 4: Getting mails with account_id...")
            result = await client.call_tool("get_mails", {"account_id": "acc_1"})
            print("Result:", result.content[0].text)
            
            # Test 5: Get mails with user_id (should show accounts first)
            print("\n📞 Test 5: Getting mails with user_id...")
            result = await client.call_tool("get_mails", {"user_id": "user_1"})
            print("Result:", result.content[0].text)
            
            # Test 6: Smart tool without parameters
            print("\n📞 Test 6: Smart tool without parameters...")
            result = await client.call_tool("get_mails_smart", {})
            print("Result:", result.content[0].text)
            
            # Test 7: Smart tool with account identifier
            print("\n📞 Test 7: Smart tool with account identifier...")
            result = await client.call_tool("get_mails_smart", {"account_identifier": "acc_1"})
            print("Result:", result.content[0].text)
            
            # Test 8: Smart tool with user identifier
            print("\n📞 Test 8: Smart tool with user identifier...")
            result = await client.call_tool("get_mails_smart", {"user_identifier": "user_1"})
            print("Result:", result.content[0].text)
            
            # Test 9: Smart tool with account name
            print("\n📞 Test 9: Smart tool with account name...")
            result = await client.call_tool("get_mails_smart", {"account_identifier": "Personal Account"})
            print("Result:", result.content[0].text)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_manual_flow():
    """Test the flow manually to show the concept"""
    
    print("\n🎯 Manual Flow Demonstration")
    print("=" * 30)
    
    print("User Query: 'Get my emails'")
    print()
    
    print("Step 1: MCP Client calls get_mails() without parameters")
    print("Result: Prerequisite required - need account_id")
    print()
    
    print("Step 2: MCP Client calls get_accounts() to get available accounts")
    print("Result: Returns list of accounts with IDs")
    print()
    
    print("Step 3: MCP Client calls get_mails(account_id='acc_1')")
    print("Result: Returns emails for the specified account")
    print()
    
    print("Alternative: MCP Client calls get_mails_smart(user_identifier='user_1')")
    print("Result: Smart tool resolves dependency and returns emails")

if __name__ == "__main__":
    print("🚀 Dependency-Aware MCP Server Test")
    print("=" * 40)
    
    # Show manual flow first
    test_manual_flow()
    
    # Run actual tests
    print("\n" + "=" * 50)
    asyncio.run(test_dependency_flow())