#!/usr/bin/env python3
"""
FastMCP Chatbot Configuration
Centralized configuration management for the FastMCP chatbot system.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ServerConfig:
    """Configuration for the FastMCP server."""
    host: str = "localhost"
    port: int = 9000
    transport: str = "stdio"
    log_level: str = "INFO"
    max_connections: int = 100
    timeout: int = 30

@dataclass
class ClientConfig:
    """Configuration for the FastMCP client."""
    server_script: str = "fastmcp_chatbot_server.py"
    server_args: list = None
    max_retries: int = 3
    retry_delay: float = 1.0
    connection_timeout: int = 30
    max_response_size: int = 10000
    
    def __post_init__(self):
        if self.server_args is None:
            self.server_args = ["--transport", "stdio"]

@dataclass
class WebConfig:
    """Configuration for the web application."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list = None
    static_files: str = "static"
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]

@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

@dataclass
class DatabaseConfig:
    """Configuration for database (if needed)."""
    url: str = "sqlite:///chatbot.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10

class FastMCPConfig:
    """Main configuration class for the FastMCP chatbot system."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.server = ServerConfig()
        self.client = ClientConfig()
        self.web = WebConfig()
        self.logging = LoggingConfig()
        self.database = DatabaseConfig()
        
        # Load configuration
        self._load_from_env()
        if config_file and Path(config_file).exists():
            self._load_from_file(config_file)
        
        # Validate configuration
        self._validate()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Server configuration
        self.server.host = os.getenv("MCP_SERVER_HOST", self.server.host)
        self.server.port = int(os.getenv("MCP_SERVER_PORT", self.server.port))
        self.server.transport = os.getenv("MCP_SERVER_TRANSPORT", self.server.transport)
        self.server.log_level = os.getenv("MCP_SERVER_LOG_LEVEL", self.server.log_level)
        self.server.max_connections = int(os.getenv("MCP_SERVER_MAX_CONNECTIONS", self.server.max_connections))
        self.server.timeout = int(os.getenv("MCP_SERVER_TIMEOUT", self.server.timeout))
        
        # Client configuration
        self.client.server_script = os.getenv("MCP_CLIENT_SERVER_SCRIPT", self.client.server_script)
        self.client.max_retries = int(os.getenv("MCP_CLIENT_MAX_RETRIES", self.client.max_retries))
        self.client.retry_delay = float(os.getenv("MCP_CLIENT_RETRY_DELAY", self.client.retry_delay))
        self.client.connection_timeout = int(os.getenv("MCP_CLIENT_CONNECTION_TIMEOUT", self.client.connection_timeout))
        self.client.max_response_size = int(os.getenv("MCP_CLIENT_MAX_RESPONSE_SIZE", self.client.max_response_size))
        
        # Web configuration
        self.web.host = os.getenv("WEB_HOST", self.web.host)
        self.web.port = int(os.getenv("WEB_PORT", self.web.port))
        self.web.debug = os.getenv("WEB_DEBUG", "false").lower() == "true"
        self.web.static_files = os.getenv("WEB_STATIC_FILES", self.web.static_files)
        
        # Logging configuration
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level)
        self.logging.format = os.getenv("LOG_FORMAT", self.logging.format)
        self.logging.file = os.getenv("LOG_FILE", self.logging.file)
        self.logging.max_size = int(os.getenv("LOG_MAX_SIZE", self.logging.max_size))
        self.logging.backup_count = int(os.getenv("LOG_BACKUP_COUNT", self.logging.backup_count))
        
        # Database configuration
        self.database.url = os.getenv("DATABASE_URL", self.database.url)
        self.database.echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"
        self.database.pool_size = int(os.getenv("DATABASE_POOL_SIZE", self.database.pool_size))
        self.database.max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", self.database.max_overflow))
    
    def _load_from_file(self, config_file: str):
        """Load configuration from file (JSON format)."""
        try:
            import json
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update configurations
            if "server" in config_data:
                for key, value in config_data["server"].items():
                    if hasattr(self.server, key):
                        setattr(self.server, key, value)
            
            if "client" in config_data:
                for key, value in config_data["client"].items():
                    if hasattr(self.client, key):
                        setattr(self.client, key, value)
            
            if "web" in config_data:
                for key, value in config_data["web"].items():
                    if hasattr(self.web, key):
                        setattr(self.web, key, value)
            
            if "logging" in config_data:
                for key, value in config_data["logging"].items():
                    if hasattr(self.logging, key):
                        setattr(self.logging, key, value)
            
            if "database" in config_data:
                for key, value in config_data["database"].items():
                    if hasattr(self.database, key):
                        setattr(self.database, key, value)
                        
        except Exception as e:
            logging.warning(f"Failed to load configuration from file {config_file}: {e}")
    
    def _validate(self):
        """Validate configuration values."""
        # Validate server configuration
        if self.server.port < 1 or self.server.port > 65535:
            raise ValueError(f"Invalid server port: {self.server.port}")
        
        if self.server.transport not in ["stdio", "http"]:
            raise ValueError(f"Invalid server transport: {self.server.transport}")
        
        if self.server.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self.server.log_level}")
        
        # Validate client configuration
        if self.client.max_retries < 0:
            raise ValueError(f"Invalid max retries: {self.client.max_retries}")
        
        if self.client.retry_delay < 0:
            raise ValueError(f"Invalid retry delay: {self.client.retry_delay}")
        
        if self.client.max_response_size < 0:
            raise ValueError(f"Invalid max response size: {self.client.max_response_size}")
        
        # Validate web configuration
        if self.web.port < 1 or self.web.port > 65535:
            raise ValueError(f"Invalid web port: {self.web.port}")
        
        # Validate logging configuration
        if self.logging.level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self.logging.level}")
    
    def setup_logging(self):
        """Setup logging based on configuration."""
        # Create formatter
        formatter = logging.Formatter(self.logging.format)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.logging.level))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.logging.level))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (if specified)
        if self.logging.file:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.logging.file,
                maxBytes=self.logging.max_size,
                backupCount=self.logging.backup_count
            )
            file_handler.setLevel(getattr(logging, self.logging.level))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "transport": self.server.transport,
                "log_level": self.server.log_level,
                "max_connections": self.server.max_connections,
                "timeout": self.server.timeout
            },
            "client": {
                "server_script": self.client.server_script,
                "server_args": self.client.server_args,
                "max_retries": self.client.max_retries,
                "retry_delay": self.client.retry_delay,
                "connection_timeout": self.client.connection_timeout,
                "max_response_size": self.client.max_response_size
            },
            "web": {
                "host": self.web.host,
                "port": self.web.port,
                "debug": self.web.debug,
                "cors_origins": self.web.cors_origins,
                "static_files": self.web.static_files
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file": self.logging.file,
                "max_size": self.logging.max_size,
                "backup_count": self.logging.backup_count
            },
            "database": {
                "url": self.database.url,
                "echo": self.database.echo,
                "pool_size": self.database.pool_size,
                "max_overflow": self.database.max_overflow
            }
        }
    
    def save_to_file(self, config_file: str):
        """Save configuration to file."""
        import json
        with open(config_file, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

# Global configuration instance
config = FastMCPConfig()

def get_config() -> FastMCPConfig:
    """Get the global configuration instance."""
    return config

def setup_logging():
    """Setup logging using the global configuration."""
    config.setup_logging()