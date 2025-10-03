# Deep Agents Implementation Plan
## Tech Stack Integration: FAISS + Azure + Redis + MCP Server

### Current Infrastructure
- **FAISS Vector DB**: Use cases, dependencies, MCP tool metadata
- **Azure OpenAI GPT-4o**: Primary LLM
- **Azure Embeddings**: For vector search and similarity matching
- **Redis Cache**: Large API response storage with chunking
- **MCP Server**: Exposes all tools via MCP protocol
- **Existing Data**: Use cases, API dependencies, tool schemas

---

## Phase 1: Core Infrastructure Setup

### 1.1 Install Dependencies
```bash
pip install deepagents langgraph langchain-openai
pip install faiss-cpu redis python-dotenv
pip install mcp-client httpx asyncio
```

### 1.2 Environment Configuration
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_DEPLOYMENT_NAME = "gpt-4o"
    
    # Azure Embeddings
    AZURE_EMBEDDING_ENDPOINT = os.getenv("AZURE_EMBEDDING_ENDPOINT")
    AZURE_EMBEDDING_KEY = os.getenv("AZURE_EMBEDDING_KEY")
    
    # Redis Cache
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    
    # MCP Server
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    
    # FAISS
    FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./faiss_index")
```

---

## Phase 2: Component Integration Classes

### 2.1 FAISS Vector Search Integration
```python
# vector_search.py
import faiss
import numpy as np
from langchain_openai import AzureOpenAIEmbeddings
from config import Config

class VectorSearchService:
    def __init__(self):
        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=Config.AZURE_EMBEDDING_ENDPOINT,
            api_key=Config.AZURE_EMBEDDING_KEY,
            model="text-embedding-ada-002"
        )
        self.faiss_index = faiss.read_index(Config.FAISS_INDEX_PATH)
        self.metadata = self._load_metadata()  # JSON file with use cases/dependencies
    
    def search_use_cases(self, query: str, k: int = 5):
        """Search for similar use cases and workflows."""
        query_embedding = self.embeddings.embed_query(query)
        query_vector = np.array([query_embedding], dtype=np.float32)
        
        distances, indices = self.faiss_index.search(query_vector, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # Valid result
                results.append({
                    "similarity": float(distances[0][i]),
                    "use_case": self.metadata[idx]["use_case"],
                    "dependencies": self.metadata[idx]["dependencies"],
                    "workflow": self.metadata[idx]["workflow"]
                })
        return results
    
    def get_api_dependencies(self, api_name: str):
        """Get dependency graph for specific API."""
        # Search for API-specific dependencies
        results = self.search_use_cases(f"API dependencies {api_name}")
        if results:
            return results[0]["dependencies"]
        return []
```

### 2.2 Redis Cache Manager
```python
# cache_manager.py
import redis
import json
import pickle
from typing import Any, Optional
from config import Config

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            decode_responses=False
        )
    
    def cache_large_response(self, response_data: Any, base_key: str, chunk_size: int = 512*1024) -> str:
        """Cache large API response with chunking."""
        serialized_data = pickle.dumps(response_data)
        
        if len(serialized_data) <= chunk_size:
            # Small response, store directly
            self.redis_client.setex(base_key, 3600, serialized_data)  # 1 hour TTL
            return base_key
        
        # Large response, chunk it
        chunks = [serialized_data[i:i+chunk_size] for i in range(0, len(serialized_data), chunk_size)]
        chunk_keys = []
        
        for idx, chunk in enumerate(chunks):
            chunk_key = f"{base_key}:chunk:{idx}"
            self.redis_client.setex(chunk_key, 3600, chunk)
            chunk_keys.append(chunk_key)
        
        # Store metadata
        metadata = {
            "type": "chunked",
            "chunks": chunk_keys,
            "total_parts": len(chunks),
            "original_size": len(serialized_data)
        }
        self.redis_client.setex(f"{base_key}:meta", 3600, json.dumps(metadata))
        return base_key
    
    def retrieve_cached_response(self, base_key: str) -> Optional[Any]:
        """Retrieve cached response, handling chunks if necessary."""
        # Check if metadata exists (chunked response)
        meta_key = f"{base_key}:meta"
        metadata_json = self.redis_client.get(meta_key)
        
        if metadata_json:
            # Chunked response
            metadata = json.loads(metadata_json.decode())
            full_data = b""
            
            for chunk_key in metadata["chunks"]:
                chunk = self.redis_client.get(chunk_key)
                if chunk:
                    full_data += chunk
                else:
                    return None  # Missing chunk
            
            return pickle.loads(full_data)
        else:
            # Direct response
            data = self.redis_client.get(base_key)
            if data:
                return pickle.loads(data)
        
        return None
    
    def get_cache_summary(self, base_key: str) -> Optional[dict]:
        """Get summary of cached data without loading full payload."""
        meta_key = f"{base_key}:meta"
        metadata_json = self.redis_client.get(meta_key)
        
        if metadata_json:
            return json.loads(metadata_json.decode())
        
        # For direct cached items, just return basic info
        if self.redis_client.exists(base_key):
            return {"type": "direct", "exists": True}
        
        return None
```

### 2.3 MCP Client Integration
```python
# mcp_client.py
import httpx
import asyncio
from typing import Dict, Any, List
from config import Config

class MCPClientService:
    def __init__(self):
        self.base_url = Config.MCP_SERVER_URL
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_available_tools(self) -> List[Dict]:
        """Get all available MCP tools from server."""
        response = await self.client.get(f"{self.base_url}/tools")
        return response.json()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Call specific MCP tool."""
        payload = {
            "tool_name": tool_name,
            "arguments": arguments
        }
        response = await self.client.post(f"{self.base_url}/call_tool", json=payload)
        return response.json()
    
    async def batch_call_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """Call multiple tools in parallel when possible."""
        tasks = []
        for call in tool_calls:
            task = self.call_tool(call["tool_name"], call["arguments"])
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
```

---

## Phase 3: Deep Agents Implementation

### 3.1 Custom MCP Tools for Deep Agents
```python
# deep_agent_tools.py
from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import asyncio
from mcp_client import MCPClientService
from cache_manager import CacheManager
from vector_search import VectorSearchService

class MCPTool(BaseTool):
    name: str
    description: str
    mcp_client: MCPClientService
    cache_manager: CacheManager
    
    def __init__(self, tool_name: str, tool_description: str, **kwargs):
        super().__init__(**kwargs)
        self.name = tool_name
        self.description = tool_description
        self.mcp_client = MCPClientService()
        self.cache_manager = CacheManager()
    
    def _run(self, query: str) -> str:
        """Execute MCP tool call with caching."""
        # Check cache first
        cache_key = f"mcp_tool:{self.name}:{hash(query)}"
        cached_result = self.cache_manager.retrieve_cached_response(cache_key)
        
        if cached_result:
            return f"[CACHED] {cached_result}"
        
        # Make MCP call
        result = asyncio.run(self.mcp_client.call_tool(self.name, {"query": query}))
        
        # Cache large responses
        if len(str(result)) > 10000:  # Cache responses > 10KB
            self.cache_manager.cache_large_response(result, cache_key)
            return f"[LARGE_RESPONSE_CACHED:{cache_key}] Response cached due to size"
        
        return str(result)

class VectorSearchTool(BaseTool):
    name = "vector_search"
    description = "Search for similar use cases and API dependencies"
    vector_service: VectorSearchService
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vector_service = VectorSearchService()
    
    def _run(self, query: str) -> str:
        results = self.vector_service.search_use_cases(query)
        return str(results)

class CacheRetrievalTool(BaseTool):
    name = "cache_retrieval"
    description = "Retrieve cached large API responses"
    cache_manager: CacheManager
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache_manager = CacheManager()
    
    def _run(self, cache_key: str) -> str:
        result = self.cache_manager.retrieve_cached_response(cache_key)
        if result:
            return str(result)
        return "Cache miss - no data found"
```

### 3.2 Main Deep Agent Setup
```python
# main_agent.py
from deepagents import DeepAgent
from langchain_openai import AzureChatOpenAI
from deep_agent_tools import MCPTool, VectorSearchTool, CacheRetrievalTool
from config import Config
import asyncio

class IntelligentMCPAgent:
    def __init__(self):
        # Initialize Azure GPT-4o
        self.llm = AzureChatOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            api_key=Config.AZURE_OPENAI_KEY,
            azure_deployment=Config.AZURE_DEPLOYMENT_NAME,
            api_version="2024-02-01",
            temperature=0.1
        )
        
        # Initialize tools
        self.tools = self._setup_tools()
        
        # Create Deep Agent
        self.agent = DeepAgent(
            llm=self.llm,
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
            max_iterations=10,
            verbose=True
        )
    
    def _setup_tools(self):
        """Setup all available tools including MCP tools."""
        tools = [
            VectorSearchTool(),
            CacheRetrievalTool()
        ]
        
        # Dynamically create MCP tools from server
        mcp_client = MCPClientService()
        available_tools = asyncio.run(mcp_client.get_available_tools())
        
        for tool_info in available_tools:
            mcp_tool = MCPTool(
                tool_name=tool_info["name"],
                tool_description=tool_info["description"]
            )
            tools.append(mcp_tool)
        
        return tools
    
    def _get_system_prompt(self):
        return """
        You are an intelligent AI agent that can handle both simple and complex queries using MCP tools.
        
        WORKFLOW:
        1. For any query, first use vector_search to find similar use cases and dependencies
        2. Plan your approach based on the retrieved context
        3. Use appropriate MCP tools in the right sequence (check dependencies)
        4. For large responses, data will be cached - use cache_retrieval when needed
        5. Synthesize results and provide comprehensive answers
        
        IMPORTANT:
        - Always check for use cases and dependencies before making tool calls
        - Be aware that some API responses are cached due to size
        - Break complex queries into subtasks
        - Provide clear, well-structured responses
        """
    
    def run_query(self, user_query: str):
        """Process user query through the deep agent."""
        return self.agent.run(user_query)

# Usage example
if __name__ == "__main__":
    agent = IntelligentMCPAgent()
    
    # Simple query
    response1 = agent.run_query("Give me a summary of all accounts")
    print("Simple Query Response:", response1)
    
    # Complex query
    response2 = agent.run_query(
        "Analyze quarterly performance by account, show top 10 transactions "
        "over ₹50,000, and provide vendor breakdown with market trends"
    )
    print("Complex Query Response:", response2)
```

---

## Phase 4: Implementation Timeline

### Week 1: Foundation
- [ ] Set up environment and dependencies
- [ ] Integrate FAISS vector search service
- [ ] Implement Redis cache manager
- [ ] Test MCP client connectivity

### Week 2: Tool Integration
- [ ] Create MCP tool wrappers for Deep Agents
- [ ] Implement vector search and cache retrieval tools
- [ ] Test individual tool functionality
- [ ] Set up Azure GPT-4o integration

### Week 3: Deep Agent Configuration
- [ ] Configure Deep Agent with all tools
- [ ] Design and test system prompts
- [ ] Implement query processing workflow
- [ ] Test simple queries

### Week 4: Complex Workflow Testing
- [ ] Test multi-step, complex queries
- [ ] Optimize cache handling for large payloads
- [ ] Fine-tune dependency handling
- [ ] Performance testing and optimization

### Week 5: Production Readiness
- [ ] Error handling and logging
- [ ] Monitoring and observability
- [ ] Load testing
- [ ] Documentation and deployment

---

## Phase 5: Advanced Features

### 5.1 Subagent Specialization
```python
# specialized_agents.py
from deepagents import SubAgent

class FinancialAnalysisAgent(SubAgent):
    def plan(self, task: str):
        return f"Financial analysis for: {task}"

class DataAggregationAgent(SubAgent):
    def plan(self, task: str):
        return f"Data aggregation for: {task}"
```

### 5.2 Monitoring and Observability
```python
# monitoring.py
import logging
from langchain.callbacks import BaseCallbackHandler

class MCPAgentMonitor(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        logging.info(f"Tool started: {serialized['name']} with input: {input_str}")
    
    def on_tool_end(self, output, **kwargs):
        logging.info(f"Tool completed with output length: {len(str(output))}")
```

This implementation plan provides a complete roadmap for integrating your existing infrastructure (FAISS, Azure, Redis, MCP Server) with Deep Agents to create an intelligent, scalable agent system capable of handling both simple and complex multi-API workflows.
