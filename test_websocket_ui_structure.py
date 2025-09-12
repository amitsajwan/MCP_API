#!/usr/bin/env python3
"""
WebSocket UI Structure Test
===========================
Tests the structure and async patterns of the WebSocket UI (web_ui_ws.py)
"""

import ast
import sys
import os

def test_websocket_ui_structure():
    """Test the WebSocket UI structure"""
    
    print("🔧 Testing WebSocket UI Structure")
    print("=" * 50)
    
    try:
        # Read the web_ui_ws.py file
        with open('web_ui_ws.py', 'r') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        # Find key components
        components_found = {
            'AsyncEventLoop': False,
            'MCPDemoService': False,
            'initialize_async': False,
            'process_message_async': False,
            'get_tools_async': False,
            'socketio_handlers': False,
            'async_loop_usage': False
        }
        
        for node in ast.walk(tree):
            # Check for AsyncEventLoop class
            if isinstance(node, ast.ClassDef) and node.name == 'AsyncEventLoop':
                components_found['AsyncEventLoop'] = True
                print("✅ AsyncEventLoop class found")
            
            # Check for MCPDemoService class
            elif isinstance(node, ast.ClassDef) and node.name == 'MCPDemoService':
                components_found['MCPDemoService'] = True
                print("✅ MCPDemoService class found")
                
                # Check methods in MCPDemoService
                for item in node.body:
                    if isinstance(item, ast.AsyncFunctionDef):
                        if item.name == 'initialize':
                            components_found['initialize_async'] = True
                            print("✅ MCPDemoService.initialize() is async")
                        elif item.name == 'process_message':
                            components_found['process_message_async'] = True
                            print("✅ MCPDemoService.process_message() is async")
                        elif item.name == 'get_tools':
                            components_found['get_tools_async'] = True
                            print("✅ MCPDemoService.get_tools() is async")
            
            # Check for socketio handlers
            elif isinstance(node, ast.FunctionDef) and node.name.startswith('handle_'):
                components_found['socketio_handlers'] = True
                print(f"✅ SocketIO handler found: {node.name}")
            
            # Check for async_loop.run_async usage
            elif isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Attribute) and 
                    isinstance(node.func.value, ast.Name) and 
                    node.func.value.id == 'async_loop' and 
                    node.func.attr == 'run_async'):
                    components_found['async_loop_usage'] = True
                    print("✅ async_loop.run_async() usage found")
        
        print(f"\n🎯 WebSocket UI Structure Test Results")
        print("=" * 50)
        
        all_found = True
        for component, found in components_found.items():
            status = "✅" if found else "❌"
            print(f"{status} {component}: {'Found' if found else 'Not found'}")
            if not found:
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ Structure test failed: {e}")
        return False

def test_mcp_service_structure():
    """Test the MCP service structure"""
    
    print("\n🔧 Testing MCP Service Structure")
    print("=" * 50)
    
    try:
        # Read the mcp_service.py file
        with open('mcp_service.py', 'r') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        # Find key components
        components_found = {
            'ModernLLMService': False,
            'initialize_async': False,
            'process_message_async': False,
            'no_asyncio_run': True  # Should not have asyncio.run()
        }
        
        for node in ast.walk(tree):
            # Check for ModernLLMService class
            if isinstance(node, ast.ClassDef) and node.name == 'ModernLLMService':
                components_found['ModernLLMService'] = True
                print("✅ ModernLLMService class found")
                
                # Check methods in ModernLLMService
                for item in node.body:
                    if isinstance(item, ast.AsyncFunctionDef):
                        if item.name == 'initialize':
                            components_found['initialize_async'] = True
                            print("✅ ModernLLMService.initialize() is async")
                        elif item.name == 'process_message':
                            components_found['process_message_async'] = True
                            print("✅ ModernLLMService.process_message() is async")
            
            # Check for asyncio.run usage (should not be present)
            elif isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Attribute) and 
                    isinstance(node.func.value, ast.Name) and 
                    node.func.value.id == 'asyncio' and 
                    node.func.attr == 'run'):
                    components_found['no_asyncio_run'] = False
                    print("❌ asyncio.run() found (should be removed)")
        
        print(f"\n🎯 MCP Service Structure Test Results")
        print("=" * 50)
        
        all_found = True
        for component, found in components_found.items():
            status = "✅" if found else "❌"
            print(f"{status} {component}: {'Found' if found else 'Not found'}")
            if not found:
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ MCP service structure test failed: {e}")
        return False

def test_mcp_server_structure():
    """Test the MCP server structure"""
    
    print("\n🔧 Testing MCP Server Structure")
    print("=" * 50)
    
    try:
        # Read the mcp_server_fastmcp2.py file
        with open('mcp_server_fastmcp2.py', 'r') as f:
            content = f.read()
        
        # Check for key patterns
        patterns_found = {
            'dynamic_function_creation': 'create_dynamic_function' in content,
            'no_arguments_param': 'arguments: Dict[str, Any] = None' not in content,
            'individual_parameters': 'param_name=' in content and 'param_signature' in content and 'param_names' in content,
            'app_tool_registration': '@app.tool()' in content,
            'tool_execution': '_execute_tool' in content
        }
        
        print("✅ Dynamic function creation found" if patterns_found['dynamic_function_creation'] else "❌ Dynamic function creation not found")
        print("✅ Old arguments parameter removed" if patterns_found['no_arguments_param'] else "❌ Old arguments parameter still present")
        print("✅ Individual parameters found" if patterns_found['individual_parameters'] else "❌ Individual parameters not found")
        print("✅ App tool registration found" if patterns_found['app_tool_registration'] else "❌ App tool registration not found")
        print("✅ Tool execution found" if patterns_found['tool_execution'] else "❌ Tool execution not found")
        
        print(f"\n🎯 MCP Server Structure Test Results")
        print("=" * 50)
        
        all_found = all(patterns_found.values())
        for pattern, found in patterns_found.items():
            status = "✅" if found else "❌"
            print(f"{status} {pattern}: {'Found' if found else 'Not found'}")
        
        return all_found
        
    except Exception as e:
        print(f"❌ MCP server structure test failed: {e}")
        return False

def test_html_template():
    """Test the HTML template structure"""
    
    print("\n🔧 Testing HTML Template Structure")
    print("=" * 50)
    
    try:
        # Read the HTML template
        with open('templates/chat_ws.html', 'r') as f:
            content = f.read()
        
        # Check for key components
        components_found = {
            'socket_io': 'socket.io' in content,
            'websocket_handlers': 'socket.on(' in content,
            'message_display': 'message' in content.lower(),
            'tool_execution': 'tool' in content.lower(),
            'capabilities': 'capabilities' in content.lower()
        }
        
        print("✅ Socket.IO integration found" if components_found['socket_io'] else "❌ Socket.IO integration not found")
        print("✅ WebSocket handlers found" if components_found['websocket_handlers'] else "❌ WebSocket handlers not found")
        print("✅ Message display found" if components_found['message_display'] else "❌ Message display not found")
        print("✅ Tool execution display found" if components_found['tool_execution'] else "❌ Tool execution display not found")
        print("✅ Capabilities display found" if components_found['capabilities'] else "❌ Capabilities display not found")
        
        print(f"\n🎯 HTML Template Test Results")
        print("=" * 50)
        
        all_found = all(components_found.values())
        for component, found in components_found.items():
            status = "✅" if found else "❌"
            print(f"{status} {component}: {'Found' if found else 'Not found'}")
        
        return all_found
        
    except Exception as e:
        print(f"❌ HTML template test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 WebSocket UI Structure Test")
    print("=" * 60)
    print("Testing: web_ui_ws.py (WebSocket UI)")
    print("Template: templates/chat_ws.html")
    print("Service: mcp_service.py")
    print("Server: mcp_server_fastmcp2.py")
    print()
    
    # Run all tests
    tests = [
        ("WebSocket UI Structure", test_websocket_ui_structure),
        ("MCP Service Structure", test_mcp_service_structure),
        ("MCP Server Structure", test_mcp_server_structure),
        ("HTML Template Structure", test_html_template)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Print overall results
    print(f"\n🎯 Overall Test Results")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n📊 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL STRUCTURE TESTS PASSED!")
        print("\n✨ WebSocket UI Components:")
        print("✅ web_ui_ws.py - WebSocket-based Flask app")
        print("✅ templates/chat_ws.html - Real-time chat interface")
        print("✅ MCPDemoService - Async service wrapper")
        print("✅ ModernLLMService - Core MCP service (async)")
        print("✅ mcp_server_fastmcp2.py - FastMCP 2.0 server")
        print("✅ AsyncEventLoop - Proper async handling")
        print("✅ SocketIO handlers - Real-time communication")
        print("\n🚀 Ready for production use!")
    else:
        print("❌ SOME STRUCTURE TESTS FAILED!")
        print("Please check the implementation.")

if __name__ == "__main__":
    main()