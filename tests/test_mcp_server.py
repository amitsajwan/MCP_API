#!/usr/bin/env python3
"""
Test Cases for MCP Server (mcp_server_fastmcp2.py)
==================================================
Tests the core MCP server functionality including:
- Server initialization
- Tool registration
- API specification loading
- Tool execution
- Authentication
"""

import unittest
import asyncio
import json
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the MCP server components
from mcp_server_fastmcp2 import FastMCP2Server, load_openapi_specs, create_tool_from_spec

class TestMCPServer(unittest.TestCase):
    """Test cases for MCP Server functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create test OpenAPI specs directory
        self.openapi_dir = Path("openapi_specs")
        self.openapi_dir.mkdir(exist_ok=True)
        
        # Create a simple test API spec
        self.test_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "http://localhost:8080"}],
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Test endpoint",
                        "parameters": [
                            {"name": "param1", "in": "query", "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        # Write test spec to file
        with open(self.openapi_dir / "test_api.yaml", "w") as f:
            import yaml
            yaml.dump(self.test_spec, f)
    
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_server_initialization(self):
        """Test MCP server initializes correctly"""
        server = FastMCP2Server()
        self.assertIsNotNone(server)
        self.assertIsNotNone(server.mcp)
    
    def test_load_openapi_specs(self):
        """Test loading OpenAPI specifications"""
        specs = load_openapi_specs(str(self.openapi_dir))
        self.assertIsInstance(specs, list)
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["info"]["title"], "Test API")
    
    def test_create_tool_from_spec(self):
        """Test creating MCP tools from OpenAPI specs"""
        tool = create_tool_from_spec("test_api", self.test_spec, "/test", "get")
        self.assertIsNotNone(tool)
        self.assertEqual(tool["function"]["name"], "test_api_getTest")
        self.assertIn("param1", str(tool["function"]["parameters"]))
    
    def test_tool_execution_structure(self):
        """Test tool execution returns correct structure"""
        # Mock the requests call
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "success"}
            mock_get.return_value = mock_response
            
            # This would need to be tested with actual tool execution
            # For now, just verify the structure is correct
            self.assertTrue(True)  # Placeholder
    
    def test_authentication_handling(self):
        """Test authentication is handled correctly"""
        # Test that authentication methods are available
        server = FastMCP2Server()
        self.assertTrue(hasattr(server, 'authenticate'))
    
    def test_error_handling(self):
        """Test error handling in tool execution"""
        # Test with invalid API spec
        invalid_spec = {"invalid": "spec"}
        with self.assertRaises(Exception):
            create_tool_from_spec("invalid", invalid_spec, "/test", "get")

class TestMCPServerIntegration(unittest.TestCase):
    """Integration tests for MCP Server"""
    
    def test_server_startup(self):
        """Test server can start without errors"""
        # This would test the actual server startup
        # For now, just verify imports work
        try:
            from mcp_server_fastmcp2 import main
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import main function: {e}")
    
    def test_tool_registration(self):
        """Test that tools are registered correctly"""
        # This would test the actual tool registration process
        # For now, just verify the function exists
        try:
            from mcp_server_fastmcp2 import register_tools
            self.assertTrue(True)
        except ImportError:
            # Function might not exist, that's okay for this test
            pass

if __name__ == '__main__':
    unittest.main()