#!/usr/bin/env python3
"""
Configuration Management
Centralized configuration for the MCP API project.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Centralized configuration management."""
    
    # MCP Server Configuration
    MCP_HOST: str = os.getenv('MCP_HOST', 'localhost')
    MCP_PORT: int = int(os.getenv('MCP_PORT', '9000'))
    MCP_SERVER_ENDPOINT: str = os.getenv('MCP_SERVER_ENDPOINT', 'http://localhost:9000')
    MCP_SERVER_SCRIPT: str = os.getenv('MCP_SERVER_SCRIPT', 'mcp_server.py')
    MCP_SERVER_ARGS: list = os.getenv('MCP_SERVER_ARGS', '--transport stdio').split()
    
    # Chatbot Application Configuration
    CHATBOT_HOST: str = os.getenv('CHATBOT_HOST', '0.0.0.0')
    CHATBOT_PORT: int = int(os.getenv('CHATBOT_PORT', '9099'))
    
    # WebSocket Configuration
    WEBSOCKET_ENABLED: bool = os.getenv('WEBSOCKET_ENABLED', 'true').lower() == 'true'
    WEBSOCKET_PATH: str = os.getenv('WEBSOCKET_PATH', '/ws')
    WEBSOCKET_PING_INTERVAL: int = int(os.getenv('WEBSOCKET_PING_INTERVAL', '30'))
    WEBSOCKET_PING_TIMEOUT: int = int(os.getenv('WEBSOCKET_PING_TIMEOUT', '10'))
    
    # Mock API Server Configuration
    MOCK_API_HOST: str = os.getenv('MOCK_API_HOST', '127.0.0.1')
    MOCK_API_PORT: int = int(os.getenv('MOCK_API_PORT', '9001'))
    MOCK_API_BASE_URL: str = os.getenv('MOCK_API_BASE_URL', 'http://127.0.0.1:9001')
    
    # Frontend Development Configuration
    VITE_PORT: int = int(os.getenv('VITE_PORT', '9517'))
    FRONTEND_DEV_URL: str = os.getenv('FRONTEND_DEV_URL', 'http://localhost:9517')
    
    # OpenAPI Configuration
    OPENAPI_DIR: str = os.getenv('OPENAPI_DIR', './openapi_specs')
    MOCK_ALL: bool = os.getenv('MOCK_ALL', 'false').lower() == 'true'
    AUTO_MOCK_FALLBACK: bool = os.getenv('AUTO_MOCK_FALLBACK', 'false').lower() == 'true'
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')
    AZURE_OPENAI_API_VERSION: str = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
    
    # Azure AD Token Provider Configuration
    USE_AZURE_AD_TOKEN_PROVIDER: bool = os.getenv('USE_AZURE_AD_TOKEN_PROVIDER', 'true').lower() == 'true'
    AZURE_AD_TOKEN_SCOPE: str = os.getenv('AZURE_AD_TOKEN_SCOPE', 'https://cognitiveservices.azure.com/.default')
    
    # Legacy API Key Configuration (only used if USE_AZURE_AD_TOKEN_PROVIDER=false)
    AZURE_OPENAI_API_KEY: Optional[str] = os.getenv('AZURE_OPENAI_API_KEY')
    
    # Authentication Configuration
    DEFAULT_LOGIN_URL: str = os.getenv('DEFAULT_LOGIN_URL', 'http://api.company.com/login')
    DEFAULT_USERNAME: Optional[str] = os.getenv('DEFAULT_USERNAME')
    DEFAULT_PASSWORD: Optional[str] = os.getenv('DEFAULT_PASSWORD')
    DEFAULT_API_KEY_NAME: Optional[str] = os.getenv('DEFAULT_API_KEY_NAME')
    DEFAULT_API_KEY_VALUE: Optional[str] = os.getenv('DEFAULT_API_KEY_VALUE')
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    ENABLE_DEBUG_LOGGING: bool = os.getenv('ENABLE_DEBUG_LOGGING', 'false').lower() == 'true'
    
    # Development Configuration
    ENABLE_CORS: bool = os.getenv('ENABLE_CORS', 'true').lower() == 'true'
    ENABLE_ACCESS_LOGGING: bool = os.getenv('ENABLE_ACCESS_LOGGING', 'true').lower() == 'true'
    MAX_TOOL_EXECUTIONS: int = int(os.getenv('MAX_TOOL_EXECUTIONS', '5'))
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration and warn if required Azure settings are missing.

        This validation is non-fatal by default to keep local/dev workflows running
        even when Azure settings are not configured. Set STRICT_CONFIG=true in .env
        to enforce hard failures.
        """
        strict = os.getenv('STRICT_CONFIG', 'false').lower() == 'true'

        if cls.USE_AZURE_AD_TOKEN_PROVIDER:
            required_fields = ['AZURE_OPENAI_ENDPOINT']
        else:
            required_fields = ['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY']

        missing_fields = [f for f in required_fields if not getattr(cls, f)]

        if missing_fields:
            prefix = "❌" if strict else "⚠️"
            print(f"{prefix} Missing Azure OpenAI configuration: {', '.join(missing_fields)}")
            if cls.USE_AZURE_AD_TOKEN_PROVIDER:
                print("   Azure AD Token Provider mode expected. Tips:")
                print("   - Set AZURE_OPENAI_ENDPOINT in .env")
                print("   - Ensure Azure CLI is logged in or credentials are available")
            else:
                print("   API Key mode expected. Tips:")
                print("   - Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env")
            if strict:
                return False
        return True
    
    @classmethod
    def get_mcp_url(cls) -> str:
        """Get MCP server URL."""
        return f"http://{cls.MCP_HOST}:{cls.MCP_PORT}"
    
    @classmethod
    def get_chatbot_url(cls) -> str:
        """Get chatbot URL."""
        return f"http://{cls.CHATBOT_HOST}:{cls.CHATBOT_PORT}"
    
    @classmethod
    def get_mock_url(cls) -> str:
        """Get mock API URL."""
        return f"http://{cls.MOCK_API_HOST}:{cls.MOCK_API_PORT}"
    
    @classmethod
    def get_websocket_url(cls) -> str:
        """Get WebSocket URL."""
        protocol = "wss" if cls.CHATBOT_HOST != "127.0.0.1" else "ws"
        return f"{protocol}://{cls.CHATBOT_HOST}:{cls.CHATBOT_PORT}{cls.WEBSOCKET_PATH}"
    
    @classmethod
    def print_config(cls):
        """Print current configuration."""
        print("🔧 Current Configuration:")
        print(f"  MCP Server:     {cls.get_mcp_url()}")
        print(f"  Chatbot:        {cls.get_chatbot_url()}")
        print(f"  Mock API:       {cls.get_mock_url()}")
        print(f"  Frontend Dev:   {cls.FRONTEND_DEV_URL}")
        print(f"  WebSocket:      {cls.get_websocket_url()}")
        print(f"  OpenAPI Dir:    {cls.OPENAPI_DIR}")
        print(f"  Mock All:       {cls.MOCK_ALL}")
        print(f"  Auto Mock:      {cls.AUTO_MOCK_FALLBACK}")
        print(f"  Log Level:      {cls.LOG_LEVEL}")
        print(f"  Azure OpenAI:   {cls.AZURE_OPENAI_ENDPOINT}")
        print(f"  Deployment:     {cls.AZURE_OPENAI_DEPLOYMENT}")
        print(f"  Auth Mode:      {'Azure AD Token Provider' if cls.USE_AZURE_AD_TOKEN_PROVIDER else 'API Key'}")
        if cls.USE_AZURE_AD_TOKEN_PROVIDER:
            print(f"  Token Scope:    {cls.AZURE_AD_TOKEN_SCOPE}")


# Global config instance
config = Config()
