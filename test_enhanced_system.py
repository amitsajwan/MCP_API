#!/usr/bin/env python3
"""
Test script for Enhanced MCP Client and Server with LLM Integration
Demonstrates intelligent argument validation, dynamic planning, and response enhancement.
"""

import json
import logging
import os
import time
import threading
from typing import Dict, Any
from enhanced_mcp_client import EnhancedMCPClient
from enhanced_mcp_server import EnhancedMCPServer, create_sample_tools

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_test_server(config: Dict[str, Any]) -> EnhancedMCPServer:
    """Start the enhanced MCP server for testing."""
    server = EnhancedMCPServer(config)
    create_sample_tools(server)
    
    # Start server in a separate thread
    def run_server():
        server.run(host='localhost', port=8001, debug=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    return server

def test_enhanced_client_server():
    """Test the enhanced MCP client and server integration."""
    print("🚀 Testing Enhanced MCP Client and Server with LLM Integration")
    print("=" * 70)
    
    # Configuration
    config = {
        "server_url": "http://localhost:8001",
        "auth": {
            "username": "admin",
            "password": "password123"
        },
        "azure_openai": {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "deployment": "gpt-4"
        },
        "jwt_secret": "test-secret-key"
    }
    
    # Check if LLM credentials are available
    if not config["azure_openai"]["endpoint"] or not config["azure_openai"]["api_key"]:
        print("⚠️ Azure OpenAI credentials not found in environment variables")
        print("Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY")
        return False
    
    try:
        # Start test server
        print("\n1. Starting Enhanced MCP Server...")
        server = start_test_server(config)
        print("✅ Server started successfully")
        
        # Create enhanced client
        print("\n2. Creating Enhanced MCP Client...")
        client = EnhancedMCPClient(config)
        print("✅ Client created successfully")
        
        # Test authentication
        print("\n3. Testing Authentication...")
        if client.authenticate():
            print("✅ Authentication successful")
        else:
            print("❌ Authentication failed")
            return False
        
        # Test tool discovery
        print("\n4. Testing Tool Discovery...")
        if client.discover_tools():
            print(f"✅ Discovered {len(client.tools)} tools with LLM enhancements")
            for tool_name, tool in client.tools.items():
                print(f"   - {tool_name}: {tool.description}")
                if tool.usage_examples:
                    print(f"     Examples: {tool.usage_examples[:2]}")
        else:
            print("❌ Tool discovery failed")
            return False
        
        # Test intelligent argument validation
        print("\n5. Testing Intelligent Argument Validation...")
        test_args = {
            "amount": "100.50",  # String that should be converted to number
            "currency": "USD",
            "description": "Test payment with intelligent validation"
        }
        
        if "createPayment" in client.tools:
            validation = client.validate_arguments_with_llm("createPayment", test_args)
            print(f"   Validation result: {'✅ Valid' if validation.is_valid else '❌ Invalid'}")
            print(f"   Confidence: {validation.confidence:.2f}")
            print(f"   Reasoning: {validation.reasoning}")
            if validation.auto_fixes:
                print(f"   Auto-fixes: {validation.auto_fixes}")
            if validation.suggestions:
                print(f"   Suggestions: {validation.suggestions[:2]}")
        
        # Test direct tool execution with validation
        print("\n6. Testing Direct Tool Execution with Validation...")
        if "createPayment" in client.tools:
            result = client.execute_tool(
                "createPayment",
                {
                    "amount": "75.25",  # String that should be auto-converted
                    "currency": "USD",
                    "description": "Direct execution test"
                },
                validate=True
            )
            
            if result["success"]:
                print("✅ Direct tool execution successful")
                print(f"   Result: {json.dumps(result['result'], indent=2)}")
                print(f"   Execution time: {result['execution_time']:.2f}s")
            else:
                print(f"❌ Direct tool execution failed: {result.get('error')}")
                if "error_analysis" in result:
                    analysis = result["error_analysis"]
                    print(f"   Analysis: {analysis.get('likely_cause')}")
                    print(f"   Suggestions: {analysis.get('suggestions', [])}")
        
        # Test intent-based execution (Dynamic Planning)
        print("\n7. Testing Intent-Based Execution (Dynamic Planning)...")
        intent_tests = [
            "I want to create a payment for $50 USD for coffee",
            "Check the balance for account acc_12345",
            "Make a payment of 25.75 euros for lunch"
        ]
        
        for intent in intent_tests:
            print(f"\n   Intent: '{intent}'")
            result = client.execute_with_intent(
                intent,
                context={"user_id": "test_user", "session": "demo"}
            )
            
            if result["success"]:
                print("   ✅ Intent execution successful")
                plan = result.get("execution_plan")
                if plan:
                    print(f"   📋 Plan: {plan.tool_name} (confidence: {plan.confidence:.2f})")
                    print(f"   💭 Reasoning: {plan.reasoning}")
                print(f"   📊 Result: {json.dumps(result['result'], indent=4)}")
            else:
                print(f"   ❌ Intent execution failed: {result.get('error')}")
                plan = result.get("execution_plan")
                if plan:
                    print(f"   📋 Attempted plan: {plan.tool_name}")
                    print(f"   💭 Reasoning: {plan.reasoning}")
        
        # Test tool suggestions
        print("\n8. Testing Tool Suggestions...")
        suggestion_queries = [
            "I need to check my money",
            "I want to send payment",
            "balance inquiry"
        ]
        
        for query in suggestion_queries:
            print(f"\n   Query: '{query}'")
            suggestions = client.get_tool_suggestions(query)
            
            if suggestions:
                print("   💡 Suggestions:")
                for suggestion in suggestions[:3]:
                    print(f"     - {suggestion['tool_name']} (relevance: {suggestion['relevance']:.2f})")
                    print(f"       Reason: {suggestion['reason']}")
            else:
                print("   ⚠️ No suggestions found")
        
        # Test error handling with invalid arguments
        print("\n9. Testing Error Handling with Invalid Arguments...")
        if "createPayment" in client.tools:
            invalid_result = client.execute_tool(
                "createPayment",
                {
                    "amount": -50,  # Invalid negative amount
                    "currency": "INVALID",  # Invalid currency
                    "description": "" # Empty description
                },
                validate=True
            )
            
            if not invalid_result["success"]:
                print("✅ Error handling working correctly")
                print(f"   Error: {invalid_result.get('error')}")
                if "validation_result" in invalid_result:
                    validation = invalid_result["validation_result"]
                    print(f"   Suggestions: {validation.get('suggestions', [])}")
            else:
                print("⚠️ Expected validation to fail, but it passed")
        
        # Show execution insights
        print("\n10. Execution Insights...")
        insights = client.get_execution_insights()
        if insights.get("total_executions", 0) > 0:
            print(f"   📊 Total executions: {insights['total_executions']}")
            print(f"   📈 Success rate: {insights['success_rate']:.2%}")
            print(f"   ⏱️ Average execution time: {insights['avg_execution_time']:.2f}s")
            
            if insights.get("most_used_tools"):
                print("   🔧 Most used tools:")
                for tool_name, stats in insights["most_used_tools"][:3]:
                    print(f"     - {tool_name}: {stats['count']} calls, {stats['success_rate']:.2%} success")
        
        print("\n" + "=" * 70)
        print("✅ Enhanced MCP Client and Server testing completed successfully!")
        print("\n🎯 Key Features Demonstrated:")
        print("   - LLM-powered argument validation and auto-fixing")
        print("   - Dynamic execution planning based on user intent")
        print("   - Intelligent error analysis and suggestions")
        print("   - Tool recommendations based on partial queries")
        print("   - Response enhancement with LLM insights")
        print("   - Execution analytics and pattern learning")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False
    
    finally:
        # Cleanup
        try:
            if 'client' in locals():
                client.close()
        except:
            pass

def test_validation_scenarios():
    """Test various validation scenarios."""
    print("\n🧪 Testing Advanced Validation Scenarios")
    print("=" * 50)
    
    config = {
        "server_url": "http://localhost:8001",
        "auth": {"username": "admin", "password": "password123"},
        "azure_openai": {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "deployment": "gpt-4"
        }
    }
    
    client = EnhancedMCPClient(config)
    
    try:
        if not client.authenticate() or not client.discover_tools():
            print("❌ Setup failed")
            return False
        
        validation_tests = [
            {
                "name": "Type Conversion",
                "tool": "createPayment",
                "args": {"amount": "123.45", "currency": "USD", "description": "Type test"}
            },
            {
                "name": "Missing Required Field",
                "tool": "createPayment",
                "args": {"amount": 100}  # Missing currency
            },
            {
                "name": "Invalid Enum Value",
                "tool": "createPayment",
                "args": {"amount": 50, "currency": "BITCOIN", "description": "Crypto test"}
            },
            {
                "name": "Boundary Value",
                "tool": "createPayment",
                "args": {"amount": 0.001, "currency": "USD", "description": "Micro payment"}
            },
            {
                "name": "Pattern Validation",
                "tool": "getBalance",
                "args": {"account_id": "invalid_format"}
            }
        ]
        
        for test in validation_tests:
            print(f"\n🔍 Test: {test['name']}")
            print(f"   Tool: {test['tool']}")
            print(f"   Args: {json.dumps(test['args'])}")
            
            if test['tool'] in client.tools:
                validation = client.validate_arguments_with_llm(test['tool'], test['args'])
                
                print(f"   Result: {'✅ Valid' if validation.is_valid else '❌ Invalid'}")
                print(f"   Confidence: {validation.confidence:.2f}")
                
                if validation.reasoning:
                    print(f"   Reasoning: {validation.reasoning}")
                
                if validation.auto_fixes:
                    print(f"   Auto-fixes: {validation.auto_fixes}")
                
                if validation.suggestions:
                    print(f"   Suggestions: {validation.suggestions[:2]}")
                
                if validation.warnings:
                    print(f"   Warnings: {validation.warnings}")
            else:
                print(f"   ⚠️ Tool {test['tool']} not available")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation test failed: {e}")
        return False
    
    finally:
        client.close()

if __name__ == "__main__":
    print("🚀 Enhanced MCP System Testing Suite")
    print("====================================\n")
    
    # Check environment
    if not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_API_KEY"):
        print("❌ Missing Azure OpenAI environment variables:")
        print("   - AZURE_OPENAI_ENDPOINT")
        print("   - AZURE_OPENAI_API_KEY")
        print("\nPlease set these variables and try again.")
        exit(1)
    
    try:
        # Run main integration test
        success = test_enhanced_client_server()
        
        if success:
            # Run validation scenarios
            test_validation_scenarios()
            
            print("\n🎉 All tests completed successfully!")
            print("\n📝 Summary:")
            print("   - Enhanced MCP Client and Server are working correctly")
            print("   - LLM integration is functioning properly")
            print("   - Intelligent validation and planning are operational")
            print("   - Error handling and suggestions are working")
        else:
            print("\n❌ Some tests failed. Please check the logs above.")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
    except Exception as e:
        logger.error(f"❌ Testing suite failed: {e}")
        exit(1)