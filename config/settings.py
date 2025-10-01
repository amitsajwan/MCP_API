"""
Configuration settings for Demo MCP System
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Demo MCP System"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Azure OpenAI Configuration
    azure_openai_api_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment_name: str = Field(default="gpt-4o", env="AZURE_OPENAI_DEPLOYMENT_NAME")
    azure_openai_embedding_model: str = Field(default="embed-ada-v0", env="AZURE_OPENAI_EMBEDDING_MODEL")
    
    # Vector Store Configuration
    vector_db_url: str = Field(default="http://localhost:6333", env="VECTOR_DB_URL")
    vector_db_collection_name: str = Field(default="semantic_state", env="VECTOR_DB_COLLECTION_NAME")
    vector_db_dimension: int = Field(default=1536, env="VECTOR_DB_DIMENSION")
    
    # Cache Configuration
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    # Session Configuration
    session_timeout: int = Field(default=1800, env="SESSION_TIMEOUT")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
