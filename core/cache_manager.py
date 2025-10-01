"""
Cache Manager for Demo MCP System
Handles caching for workflows, user queries, and use cases
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib

from config.settings import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Cache manager for workflow/user query/use case caching"""
    
    def __init__(self):
        self.workflow_cache: Dict[str, Dict[str, Any]] = {}
        self.user_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.use_case_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = settings.cache_ttl
        self.max_size = settings.cache_max_size
    
    def _generate_cache_key(self, prefix: str, identifier: str, params: Optional[Dict] = None) -> str:
        """Generate cache key with parameters hash"""
        if params:
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"{prefix}_{identifier}_{params_hash}"
        return f"{prefix}_{identifier}"
    
    def _is_expired(self, timestamp: datetime, ttl: int) -> bool:
        """Check if cache entry is expired"""
        return (datetime.now() - timestamp).seconds > ttl
    
    def _cleanup_expired(self):
        """Clean up expired cache entries"""
        current_time = datetime.now()
        
        # Clean workflow cache
        expired_workflows = [
            key for key, data in self.workflow_cache.items()
            if self._is_expired(data["timestamp"], data.get("ttl", self.cache_ttl))
        ]
        for key in expired_workflows:
            del self.workflow_cache[key]
        
        # Clean user cache
        for user_id in list(self.user_cache.keys()):
            expired_queries = [
                query for query, data in self.user_cache[user_id].items()
                if self._is_expired(data["timestamp"], self.cache_ttl)
            ]
            for query in expired_queries:
                del self.user_cache[user_id][query]
            
            # Remove empty user cache
            if not self.user_cache[user_id]:
                del self.user_cache[user_id]
        
        # Clean use case cache
        expired_use_cases = [
            key for key, data in self.use_case_cache.items()
            if self._is_expired(data["timestamp"], self.cache_ttl)
        ]
        for key in expired_use_cases:
            del self.use_case_cache[key]
    
    def set_workflow_cache(self, workflow_id: str, data: Any, ttl: Optional[int] = None) -> None:
        """Set cache for workflow"""
        self._cleanup_expired()
        
        if len(self.workflow_cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.workflow_cache.keys(), 
                            key=lambda k: self.workflow_cache[k]["timestamp"])
            del self.workflow_cache[oldest_key]
        
        self.workflow_cache[workflow_id] = {
            "data": data,
            "timestamp": datetime.now(),
            "ttl": ttl or self.cache_ttl
        }
        
        logger.info(f"Workflow cache set for {workflow_id}")
    
    def get_workflow_cache(self, workflow_id: str) -> Optional[Any]:
        """Get cache for workflow"""
        if workflow_id in self.workflow_cache:
            cache_entry = self.workflow_cache[workflow_id]
            if not self._is_expired(cache_entry["timestamp"], cache_entry["ttl"]):
                logger.info(f"Workflow cache hit for {workflow_id}")
                return cache_entry["data"]
            else:
                del self.workflow_cache[workflow_id]
                logger.info(f"Workflow cache expired for {workflow_id}")
        return None
    
    def set_user_cache(self, user_id: str, query: str, data: Any) -> None:
        """Set cache for user query"""
        self._cleanup_expired()
        
        if user_id not in self.user_cache:
            self.user_cache[user_id] = {}
        
        if len(self.user_cache[user_id]) >= 100:  # Limit per user
            # Remove oldest entry for this user
            oldest_query = min(self.user_cache[user_id].keys(),
                             key=lambda k: self.user_cache[user_id][k]["timestamp"])
            del self.user_cache[user_id][oldest_query]
        
        self.user_cache[user_id][query] = {
            "data": data,
            "timestamp": datetime.now()
        }
        
        logger.info(f"User cache set for {user_id}: {query[:50]}...")
    
    def get_user_cache(self, user_id: str, query: str) -> Optional[Any]:
        """Get cache for user query"""
        if user_id in self.user_cache and query in self.user_cache[user_id]:
            cache_entry = self.user_cache[user_id][query]
            if not self._is_expired(cache_entry["timestamp"], self.cache_ttl):
                logger.info(f"User cache hit for {user_id}: {query[:50]}...")
                return cache_entry["data"]
            else:
                del self.user_cache[user_id][query]
                logger.info(f"User cache expired for {user_id}: {query[:50]}...")
        return None
    
    def set_use_case_cache(self, use_case_id: str, parameters: Dict, result: Any) -> None:
        """Set cache for use case execution"""
        self._cleanup_expired()
        
        cache_key = self._generate_cache_key("use_case", use_case_id, parameters)
        
        if len(self.use_case_cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.use_case_cache.keys(),
                            key=lambda k: self.use_case_cache[k]["timestamp"])
            del self.use_case_cache[oldest_key]
        
        self.use_case_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now()
        }
        
        logger.info(f"Use case cache set for {use_case_id}")
    
    def get_use_case_cache(self, use_case_id: str, parameters: Dict) -> Optional[Any]:
        """Get cache for use case execution"""
        cache_key = self._generate_cache_key("use_case", use_case_id, parameters)
        
        if cache_key in self.use_case_cache:
            cache_entry = self.use_case_cache[cache_key]
            if not self._is_expired(cache_entry["timestamp"], self.cache_ttl):
                logger.info(f"Use case cache hit for {use_case_id}")
                return cache_entry["result"]
            else:
                del self.use_case_cache[cache_key]
                logger.info(f"Use case cache expired for {use_case_id}")
        return None
    
    def clear_cache(self, cache_type: str = "all") -> None:
        """Clear cache by type"""
        if cache_type == "all":
            self.workflow_cache.clear()
            self.user_cache.clear()
            self.use_case_cache.clear()
            logger.info("All cache cleared")
        elif cache_type == "workflow":
            self.workflow_cache.clear()
            logger.info("Workflow cache cleared")
        elif cache_type == "user":
            self.user_cache.clear()
            logger.info("User cache cleared")
        elif cache_type == "use_case":
            self.use_case_cache.clear()
            logger.info("Use case cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        self._cleanup_expired()
        
        return {
            "workflow_cache_size": len(self.workflow_cache),
            "user_cache_size": sum(len(queries) for queries in self.user_cache.values()),
            "use_case_cache_size": len(self.use_case_cache),
            "total_cache_size": len(self.workflow_cache) + 
                              sum(len(queries) for queries in self.user_cache.values()) + 
                              len(self.use_case_cache),
            "cache_ttl": self.cache_ttl,
            "max_size": self.max_size
        }
    
    def get_cache_details(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        return {
            "workflow_cache": {
                "keys": list(self.workflow_cache.keys()),
                "entries": len(self.workflow_cache)
            },
            "user_cache": {
                "users": list(self.user_cache.keys()),
                "total_queries": sum(len(queries) for queries in self.user_cache.values())
            },
            "use_case_cache": {
                "keys": list(self.use_case_cache.keys()),
                "entries": len(self.use_case_cache)
            }
        }
