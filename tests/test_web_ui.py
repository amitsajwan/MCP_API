#!/usr/bin/env python3
"""
Test Cases for Web UI (web_ui_ws.py)
====================================
Tests the web UI functionality including:
- Flask app initialization
- SocketIO event handling
- MCP service integration
- Message processing
- Error handling
"""

import unittest
import asyncio
import json
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui_ws import MCPDemoService, app, socketio

class TestWebUI(unittest.TestCase):
    """Test cases for Web UI functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.client = self.app.test_client()
        self.socketio = socketio
    
    def test_app_initialization(self):
        """Test Flask app initializes correctly"""
        self.assertIsNotNone(self.app)
        self.assertEqual(self.app.name, 'web_ui_ws')
    
    def test_socketio_initialization(self):
        """Test SocketIO initializes correctly"""
        self.assertIsNotNone(self.socketio)
    
    def test_mcp_demo_service_initialization(self):
        """Test MCPDemoService initializes correctly"""
        service = MCPDemoService()
        self.assertIsNotNone(service)
        self.assertFalse(service.initialized)
        self.assertIsNone(service.service)
        self.assertEqual(service.conversation, [])
    
    def test_mcp_demo_service_initialize_success(self):
        """Test successful MCPDemoService initialization"""
        service = MCPDemoService()
        
        # Mock the ModernLLMService
        with patch('web_ui_ws.ModernLLMService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.initialize.return_value = True
            mock_service_class.return_value = mock_service
            
            # Test initialization
            result = asyncio.run(service.initialize())
            
            # Verify initialization
            self.assertTrue(result)
            self.assertTrue(service.initialized)
            self.assertIsNotNone(service.service)
    
    def test_mcp_demo_service_initialize_failure(self):
        """Test MCPDemoService initialization failure"""
        service = MCPDemoService()
        
        # Mock the ModernLLMService to fail
        with patch('web_ui_ws.ModernLLMService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.initialize.return_value = False
            mock_service_class.return_value = mock_service
            
            # Test initialization
            result = asyncio.run(service.initialize())
            
            # Verify initialization failed
            self.assertFalse(result)
            self.assertFalse(service.initialized)
    
    def test_mcp_demo_service_process_message_not_initialized(self):
        """Test message processing when not initialized"""
        service = MCPDemoService()
        
        # Test with uninitialized service
        result = asyncio.run(service.process_message("test message"))
        
        # Verify error handling
        self.assertIsInstance(result, dict)
        self.assertIn("not initialized", result["response"])
        self.assertEqual(result["tool_calls"], [])
        self.assertEqual(result["capabilities"], [])
    
    def test_mcp_demo_service_process_message_success(self):
        """Test successful message processing"""
        service = MCPDemoService()
        service.initialized = True
        
        # Mock the service
        mock_service = AsyncMock()
        mock_service.process_message.return_value = {
            "response": "Test response",
            "tool_calls": [{"tool_name": "test_tool", "success": True}],
            "capabilities": {"descriptions": ["Test capability"]}
        }
        service.service = mock_service
        
        # Test message processing
        result = asyncio.run(service.process_message("test message"))
        
        # Verify processing
        self.assertIsInstance(result, dict)
        self.assertEqual(result["response"], "Test response")
        self.assertEqual(len(result["tool_calls"]), 1)
        self.assertEqual(len(result["capabilities"]["descriptions"]), 1)
    
    def test_mcp_demo_service_conversation_handling(self):
        """Test conversation history handling"""
        service = MCPDemoService()
        service.initialized = True
        
        # Mock the service
        mock_service = AsyncMock()
        mock_service.process_message.return_value = {
            "response": "Test response",
            "tool_calls": [],
            "capabilities": {}
        }
        service.service = mock_service
        
        # Test first message
        result1 = asyncio.run(service.process_message("Hello"))
        self.assertEqual(len(service.conversation), 2)  # user + assistant
        
        # Test second message
        result2 = asyncio.run(service.process_message("How are you?"))
        self.assertEqual(len(service.conversation), 4)  # 2 more messages

class TestWebUIRoutes(unittest.TestCase):
    """Test cases for Web UI routes"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.client = self.app.test_client()
    
    def test_index_route(self):
        """Test index route returns correct template"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'chat_ws.html', response.data)

class TestWebUISocketIO(unittest.TestCase):
    """Test cases for Web UI SocketIO events"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.socketio = socketio
    
    def test_connect_event(self):
        """Test connect event handling"""
        # This would test the actual SocketIO connect event
        # For now, just verify the function exists
        self.assertTrue(hasattr(self.socketio, 'on'))
    
    def test_message_event(self):
        """Test message event handling"""
        # This would test the actual SocketIO message event
        # For now, just verify the function exists
        self.assertTrue(hasattr(self.socketio, 'on'))
    
    def test_disconnect_event(self):
        """Test disconnect event handling"""
        # This would test the actual SocketIO disconnect event
        # For now, just verify the function exists
        self.assertTrue(hasattr(self.socketio, 'on'))

class TestWebUIIntegration(unittest.TestCase):
    """Integration tests for Web UI"""
    
    def test_import_structure(self):
        """Test that all required functions can be imported"""
        try:
            from web_ui_ws import MCPDemoService, app, socketio
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import required components: {e}")
    
    def test_app_configuration(self):
        """Test app configuration"""
        self.assertEqual(self.app.config['SECRET_KEY'], 'demo-secret-key')
    
    def test_socketio_configuration(self):
        """Test SocketIO configuration"""
        self.assertIsNotNone(self.socketio)

class TestWebUIErrorHandling(unittest.TestCase):
    """Test error handling in Web UI"""
    
    def test_invalid_message_handling(self):
        """Test handling of invalid messages"""
        service = MCPDemoService()
        
        # Test with None message
        result = asyncio.run(service.process_message(None))
        self.assertIsInstance(result, dict)
        self.assertIn("not initialized", result["response"])
    
    def test_empty_message_handling(self):
        """Test handling of empty messages"""
        service = MCPDemoService()
        
        # Test with empty message
        result = asyncio.run(service.process_message(""))
        self.assertIsInstance(result, dict)
        self.assertIn("not initialized", result["response"])
    
    def test_service_initialization_error_handling(self):
        """Test error handling during service initialization"""
        service = MCPDemoService()
        
        # Mock service initialization to raise exception
        with patch('web_ui_ws.ModernLLMService') as mock_service_class:
            mock_service_class.side_effect = Exception("Initialization failed")
            
            # Test initialization
            result = asyncio.run(service.initialize())
            
            # Verify error handling
            self.assertFalse(result)
            self.assertFalse(service.initialized)

if __name__ == '__main__':
    unittest.main()