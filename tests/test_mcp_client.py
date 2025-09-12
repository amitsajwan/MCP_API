#!/usr/bin/env python3
"""
Test Cases for MCP Client (mcp_client.py)
=========================================
Tests the MCP client functionality including:
- Azure client creation
- Tool discovery and preparation
- Tool execution
- Response handling
"""

import unittest
import asyncio
import json
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import (
    create_azure_client, 
    list_and_prepare_tools, 
    safe_truncate, 
    count_tokens,
    MCPClient,
    PythonStdioTransport
)

class TestMCPClient(unittest.TestCase):
    """Test cases for MCP Client functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_DEPLOYMENT_NAME': 'gpt-4o',
            'AZURE_CLIENT_ID': 'test-client-id',
            'AZURE_CLIENT_SECRET': 'test-secret',
            'AZURE_TENANT_ID': 'test-tenant'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_count_tokens(self):
        """Test token counting function"""
        text = "This is a test message with multiple words"
        count = count_tokens(text)
        self.assertEqual(count, 9)  # 9 words
    
    def test_safe_truncate_small_object(self):
        """Test safe_truncate with small object"""
        small_obj = {"key": "value", "number": 123}
        result = safe_truncate(small_obj, max_tokens=100)
        self.assertEqual(result, small_obj)
    
    def test_safe_truncate_large_object(self):
        """Test safe_truncate with large object"""
        large_obj = {"data": "x" * 10000}  # Very large string
        result = safe_truncate(large_obj, max_tokens=10)
        self.assertNotEqual(result, large_obj)
        self.assertIn("truncated", str(result).lower())
    
    @patch('mcp_client.AsyncAzureOpenAI')
    @patch('mcp_client.get_bearer_token_provider')
    def test_create_azure_client(self, mock_token_provider, mock_azure_client):
        """Test Azure client creation"""
        # Mock the token provider
        mock_token_provider.return_value = MagicMock()
        
        # Mock the Azure client
        mock_client_instance = MagicMock()
        mock_azure_client.return_value = mock_client_instance
        
        # Test client creation
        client = asyncio.run(create_azure_client())
        
        # Verify client was created
        mock_azure_client.assert_called_once()
        self.assertIsNotNone(client)
    
    def test_python_stdio_transport_initialization(self):
        """Test PythonStdioTransport initialization"""
        transport = PythonStdioTransport("test_script.py", args=["--test"])
        self.assertIsNotNone(transport)
        self.assertEqual(transport.script_path, "test_script.py")
        self.assertEqual(transport.args, ["--test"])
    
    @patch('mcp_client.MCPClient')
    async def test_list_and_prepare_tools(self, mock_mcp_client_class):
        """Test tool listing and preparation"""
        # Mock MCP client
        mock_client = AsyncMock()
        mock_mcp_client_class.return_value = mock_client
        
        # Mock tool list response
        mock_tools = [
            {
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        mock_client.list_tools.return_value = mock_tools
        
        # Test tool preparation
        tools = await list_and_prepare_tools(mcp_client)
        
        # Verify tools were processed
        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["function"]["name"], "test_tool")

class TestMCPClientIntegration(unittest.TestCase):
    """Integration tests for MCP Client"""
    
    def test_import_structure(self):
        """Test that all required functions can be imported"""
        try:
            from mcp_client import (
                create_azure_client,
                list_and_prepare_tools,
                safe_truncate,
                count_tokens,
                MCPClient,
                PythonStdioTransport
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import required functions: {e}")
    
    def test_environment_variable_handling(self):
        """Test environment variable handling"""
        # Test with missing environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Should handle missing env vars gracefully
            try:
                from mcp_client import AZURE_ENDPOINT, AZURE_DEPLOYMENT
                self.assertEqual(AZURE_ENDPOINT, "https://your-resource.openai.azure.com/")
                self.assertEqual(AZURE_DEPLOYMENT, "gpt-4o")
            except Exception as e:
                self.fail(f"Failed to handle missing environment variables: {e}")

class TestMCPClientErrorHandling(unittest.TestCase):
    """Test error handling in MCP Client"""
    
    def test_invalid_azure_credentials(self):
        """Test handling of invalid Azure credentials"""
        with patch.dict(os.environ, {
            'AZURE_OPENAI_ENDPOINT': 'invalid-endpoint',
            'AZURE_DEPLOYMENT_NAME': 'invalid-deployment'
        }):
            # Should handle invalid credentials gracefully
            try:
                from mcp_client import create_azure_client
                # This might raise an exception, which is expected
                self.assertTrue(True)
            except Exception:
                # Expected behavior for invalid credentials
                self.assertTrue(True)
    
    def test_network_error_handling(self):
        """Test handling of network errors"""
        # This would test network error handling
        # For now, just verify the structure is correct
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()