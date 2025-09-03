#!/usr/bin/env python3
"""
Intelligent Configuration Manager with Azure OpenAI Integration
This module provides smart configuration management that learns from API usage
patterns and automatically optimizes settings using LLM capabilities.
"""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import yaml
from openai import AzureOpenAI
import threading
import hashlib
import re

logger = logging.getLogger(__name__)

@dataclass
class APIEndpointConfig:
    """Configuration for a single API endpoint."""
    name: str
    method: str
    path: str
    base_url: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    rate_limit: Optional[int] = None
    cache_ttl: Optional[int] = None
    
    # Intelligence features
    auto_optimize: bool = True
    learning_enabled: bool = True
    confidence_threshold: float = 0.7
    
    # Performance tracking
    success_rate: float = 1.0
    avg_response_time: float = 0.0
    usage_count: int = 0
    last_optimized: Optional[datetime] = None
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class IntelligentConfig:
    """Main configuration with intelligence features."""
    version: str = "1.0"
    name: str = "intelligent-api-config"
    
    # API endpoints
    endpoints: Dict[str, APIEndpointConfig] = field(default_factory=dict)
    
    # Global settings
    global_timeout: float = 30.0
    global_retry_count: int = 3
    global_headers: Dict[str, str] = field(default_factory=dict)
    
    # Authentication
    authentication: Dict[str, Any] = field(default_factory=dict)
    
    # Azure OpenAI settings
    azure_openai: Dict[str, str] = field(default_factory=dict)
    
    # Intelligence settings
    intelligence: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "learning_enabled": True,
        "auto_optimization": True,
        "optimization_interval": 3600,  # 1 hour
        "confidence_threshold": 0.7,
        "max_optimization_history": 100
    })
    
    # Performance thresholds
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "max_response_time": 5.0,
        "min_success_rate": 0.95,
        "max_error_rate": 0.05
    })
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    optimization_count: int = 0

class IntelligentConfigManager:
    """Intelligent configuration manager with LLM-powered optimization."""
    
    def __init__(self, config_path: str = "intelligent_config.yaml"):
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__)
        self.config: IntelligentConfig = IntelligentConfig()
        self._lock = threading.RLock()
        
        # Initialize LLM client
        self._init_llm_client()
        
        # Load existing configuration
        self.load_config()
        
        # Start optimization scheduler if enabled
        if self.config.intelligence.get("auto_optimization", True):
            self._start_optimization_scheduler()
        
        logger.info("🧠 Intelligent Configuration Manager initialized")
    
    def _init_llm_client(self):
        """Initialize LLM client for intelligent features."""
        try:
            self.llm_client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version="2024-02-15-preview"
            )
            self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
            self.llm_available = True
            logger.info("✅ Config manager LLM initialized")
        except Exception as e:
            logger.warning(f"⚠️  Config manager LLM not available: {e}")
            self.llm_client = None
            self.llm_available = False
    
    def load_config(self) -> bool:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    if self.config_path.suffix.lower() == '.yaml':
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
                
                # Convert to IntelligentConfig
                self.config = self._dict_to_config(data)
                logger.info(f"📁 Configuration loaded from {self.config_path}")
                return True
            else:
                logger.info("📁 No existing configuration found, using defaults")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            return False
    
    def save_config(self) -> bool:
        """Save configuration to file."""
        try:
            with self._lock:
                self.config.updated_at = datetime.now()
                
                # Convert to dict
                data = self._config_to_dict(self.config)
                
                # Ensure directory exists
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save to file
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    if self.config_path.suffix.lower() == '.yaml':
                        yaml.dump(data, f, default_flow_style=False, indent=2)
                    else:
                        json.dump(data, f, indent=2, default=str)
                
                logger.info(f"💾 Configuration saved to {self.config_path}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")
            return False
    
    def add_endpoint(self, endpoint_config: APIEndpointConfig) -> bool:
        """Add or update an API endpoint configuration."""
        try:
            with self._lock:
                self.config.endpoints[endpoint_config.name] = endpoint_config
                
                # Intelligent parameter suggestion
                if self.llm_available and endpoint_config.auto_optimize:
                    suggested_params = self._suggest_endpoint_parameters(endpoint_config)
                    if suggested_params:
                        endpoint_config.parameters.update(suggested_params)
                        logger.info(f"🧠 Applied intelligent parameter suggestions for {endpoint_config.name}")
                
                self.save_config()
                logger.info(f"➕ Added endpoint: {endpoint_config.name}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to add endpoint: {e}")
            return False
    
    def get_endpoint_config(self, name: str) -> Optional[APIEndpointConfig]:
        """Get configuration for a specific endpoint."""
        return self.config.endpoints.get(name)
    
    def update_endpoint_performance(self, name: str, success: bool, 
                                  response_time: float) -> bool:
        """Update endpoint performance metrics."""
        try:
            with self._lock:
                endpoint = self.config.endpoints.get(name)
                if not endpoint:
                    return False
                
                # Update metrics
                endpoint.usage_count += 1
                
                # Update success rate
                if endpoint.usage_count == 1:
                    endpoint.success_rate = 1.0 if success else 0.0
                else:
                    endpoint.success_rate = (
                        (endpoint.success_rate * (endpoint.usage_count - 1) + 
                         (1.0 if success else 0.0)) / endpoint.usage_count
                    )
                
                # Update average response time
                if endpoint.usage_count == 1:
                    endpoint.avg_response_time = response_time
                else:
                    endpoint.avg_response_time = (
                        (endpoint.avg_response_time * (endpoint.usage_count - 1) + 
                         response_time) / endpoint.usage_count
                    )
                
                # Check if optimization is needed
                if self._should_optimize_endpoint(endpoint):
                    self._optimize_endpoint(endpoint)
                
                return True
        except Exception as e:
            logger.error(f"❌ Failed to update endpoint performance: {e}")
            return False
    
    def _should_optimize_endpoint(self, endpoint: APIEndpointConfig) -> bool:
        """Determine if an endpoint should be optimized."""
        if not endpoint.auto_optimize or not self.llm_available:
            return False
        
        # Check if enough data is available
        if endpoint.usage_count < 10:
            return False
        
        # Check performance thresholds
        thresholds = self.config.performance_thresholds
        
        if (endpoint.success_rate < thresholds.get("min_success_rate", 0.95) or
            endpoint.avg_response_time > thresholds.get("max_response_time", 5.0)):
            return True
        
        # Check if it's been a while since last optimization
        if endpoint.last_optimized:
            time_since_optimization = datetime.now() - endpoint.last_optimized
            optimization_interval = self.config.intelligence.get("optimization_interval", 3600)
            if time_since_optimization.total_seconds() > optimization_interval:
                return True
        
        return False
    
    def _optimize_endpoint(self, endpoint: APIEndpointConfig) -> bool:
        """Optimize an endpoint using LLM intelligence."""
        try:
            logger.info(f"🧠 Optimizing endpoint: {endpoint.name}")
            
            # Prepare optimization context
            context = {
                "endpoint": {
                    "name": endpoint.name,
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "current_timeout": endpoint.timeout,
                    "current_retry_count": endpoint.retry_count,
                    "current_retry_delay": endpoint.retry_delay
                },
                "performance": {
                    "success_rate": endpoint.success_rate,
                    "avg_response_time": endpoint.avg_response_time,
                    "usage_count": endpoint.usage_count
                },
                "thresholds": self.config.performance_thresholds
            }
            
            prompt = f"""
Analyze this API endpoint and suggest optimizations:

**Endpoint Details:**
- Name: {endpoint.name}
- Method: {endpoint.method}
- Path: {endpoint.path}
- Current timeout: {endpoint.timeout}s
- Current retry count: {endpoint.retry_count}
- Current retry delay: {endpoint.retry_delay}s

**Performance Metrics:**
- Success rate: {endpoint.success_rate:.2%}
- Average response time: {endpoint.avg_response_time:.2f}s
- Usage count: {endpoint.usage_count}

**Performance Thresholds:**
- Min success rate: {self.config.performance_thresholds.get('min_success_rate', 0.95):.2%}
- Max response time: {self.config.performance_thresholds.get('max_response_time', 5.0)}s

Provide a JSON response with optimized settings:
{{
  "timeout": <recommended_timeout_seconds>,
  "retry_count": <recommended_retry_count>,
  "retry_delay": <recommended_retry_delay_seconds>,
  "rate_limit": <recommended_rate_limit_or_null>,
  "cache_ttl": <recommended_cache_ttl_or_null>,
  "reasoning": "<explanation_of_changes>",
  "confidence": <confidence_score_0_to_1>
}}

Focus on improving performance while maintaining reliability.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API performance optimization expert. Analyze metrics and suggest optimal configurations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            # Parse optimization suggestions
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
            if json_match:
                optimization = json.loads(json_match.group(1))
            else:
                optimization = json.loads(response_text)
            
            # Apply optimizations if confidence is high enough
            confidence_threshold = self.config.intelligence.get("confidence_threshold", 0.7)
            if optimization.get("confidence", 0) >= confidence_threshold:
                
                # Record optimization history
                optimization_record = {
                    "timestamp": datetime.now().isoformat(),
                    "old_config": {
                        "timeout": endpoint.timeout,
                        "retry_count": endpoint.retry_count,
                        "retry_delay": endpoint.retry_delay,
                        "rate_limit": endpoint.rate_limit,
                        "cache_ttl": endpoint.cache_ttl
                    },
                    "new_config": optimization,
                    "reasoning": optimization.get("reasoning", ""),
                    "confidence": optimization.get("confidence", 0)
                }
                
                # Apply optimizations
                endpoint.timeout = optimization.get("timeout", endpoint.timeout)
                endpoint.retry_count = optimization.get("retry_count", endpoint.retry_count)
                endpoint.retry_delay = optimization.get("retry_delay", endpoint.retry_delay)
                endpoint.rate_limit = optimization.get("rate_limit", endpoint.rate_limit)
                endpoint.cache_ttl = optimization.get("cache_ttl", endpoint.cache_ttl)
                
                # Update metadata
                endpoint.last_optimized = datetime.now()
                endpoint.optimization_history.append(optimization_record)
                
                # Keep history manageable
                max_history = self.config.intelligence.get("max_optimization_history", 100)
                if len(endpoint.optimization_history) > max_history:
                    endpoint.optimization_history = endpoint.optimization_history[-max_history//2:]
                
                # Update global counter
                self.config.optimization_count += 1
                
                logger.info(f"✅ Optimized {endpoint.name}: {optimization.get('reasoning', 'No reason provided')}")
                
                # Save configuration
                self.save_config()
                return True
            else:
                logger.info(f"⚠️  Optimization confidence too low ({optimization.get('confidence', 0):.2f}) for {endpoint.name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to optimize endpoint {endpoint.name}: {e}")
            return False
    
    def _suggest_endpoint_parameters(self, endpoint: APIEndpointConfig) -> Dict[str, Any]:
        """Suggest intelligent default parameters for an endpoint."""
        try:
            prompt = f"""
Analyze this API endpoint and suggest intelligent default parameters:

**Endpoint:**
- Method: {endpoint.method}
- Path: {endpoint.path}
- Base URL: {endpoint.base_url}

**Current Parameters:**
{json.dumps(endpoint.parameters, indent=2) if endpoint.parameters else "None"}

Based on the endpoint path and method, suggest common parameters that might be useful.
For example:
- For GET /api/users: limit, offset, sort, filter parameters
- For POST /api/payments: validation parameters, format options
- For GET /api/search: query, page, per_page parameters

Provide a JSON response with suggested parameters:
{{
  "suggested_parameters": {{
    "parameter_name": {{
      "type": "string|number|boolean",
      "default_value": "suggested_default",
      "description": "what this parameter does",
      "required": true|false
    }}
  }},
  "reasoning": "why these parameters are suggested"
}}

Only suggest parameters that are commonly used for this type of endpoint.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API design expert. Suggest intelligent default parameters for API endpoints."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            # Parse suggestions
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group(1))
            else:
                suggestions = json.loads(response_text)
            
            # Convert to simple parameter dict
            suggested_params = {}
            for param_name, param_info in suggestions.get("suggested_parameters", {}).items():
                suggested_params[param_name] = param_info.get("default_value")
            
            logger.info(f"🧠 Generated parameter suggestions for {endpoint.name}: {suggestions.get('reasoning', '')}")
            return suggested_params
            
        except Exception as e:
            logger.error(f"❌ Failed to suggest parameters for {endpoint.name}: {e}")
            return {}
    
    def _start_optimization_scheduler(self):
        """Start background optimization scheduler."""
        def optimization_worker():
            while True:
                try:
                    interval = self.config.intelligence.get("optimization_interval", 3600)
                    time.sleep(interval)
                    
                    if self.config.intelligence.get("auto_optimization", True):
                        self._run_scheduled_optimization()
                        
                except Exception as e:
                    logger.error(f"❌ Optimization scheduler error: {e}")
                    time.sleep(60)  # Wait a minute before retrying
        
        # Start in background thread
        optimization_thread = threading.Thread(target=optimization_worker, daemon=True)
        optimization_thread.start()
        logger.info("🔄 Optimization scheduler started")
    
    def _run_scheduled_optimization(self):
        """Run scheduled optimization for all endpoints."""
        logger.info("🔄 Running scheduled optimization")
        
        optimized_count = 0
        for endpoint in self.config.endpoints.values():
            if self._should_optimize_endpoint(endpoint):
                if self._optimize_endpoint(endpoint):
                    optimized_count += 1
        
        if optimized_count > 0:
            logger.info(f"✅ Scheduled optimization completed: {optimized_count} endpoints optimized")
        else:
            logger.info("ℹ️  Scheduled optimization completed: no optimizations needed")
    
    def generate_config_report(self) -> Dict[str, Any]:
        """Generate intelligent configuration report."""
        report = {
            "config_summary": {
                "name": self.config.name,
                "version": self.config.version,
                "endpoint_count": len(self.config.endpoints),
                "optimization_count": self.config.optimization_count,
                "created_at": self.config.created_at.isoformat(),
                "updated_at": self.config.updated_at.isoformat()
            },
            "endpoint_performance": {},
            "optimization_history": [],
            "recommendations": [],
            "generated_at": datetime.now().isoformat()
        }
        
        # Add endpoint performance
        for name, endpoint in self.config.endpoints.items():
            report["endpoint_performance"][name] = {
                "success_rate": endpoint.success_rate,
                "avg_response_time": endpoint.avg_response_time,
                "usage_count": endpoint.usage_count,
                "optimization_count": len(endpoint.optimization_history),
                "last_optimized": endpoint.last_optimized.isoformat() if endpoint.last_optimized else None
            }
        
        # Add recent optimization history
        all_optimizations = []
        for endpoint in self.config.endpoints.values():
            for opt in endpoint.optimization_history[-5:]:  # Last 5 optimizations per endpoint
                opt_copy = opt.copy()
                opt_copy["endpoint_name"] = endpoint.name
                all_optimizations.append(opt_copy)
        
        # Sort by timestamp
        all_optimizations.sort(key=lambda x: x["timestamp"], reverse=True)
        report["optimization_history"] = all_optimizations[:20]  # Last 20 optimizations
        
        # Generate intelligent recommendations
        if self.llm_available:
            try:
                recommendations = self._generate_config_recommendations()
                report["recommendations"] = recommendations
            except Exception as e:
                logger.error(f"Failed to generate config recommendations: {e}")
        
        return report
    
    def _generate_config_recommendations(self) -> List[str]:
        """Generate intelligent configuration recommendations."""
        try:
            # Prepare summary for LLM
            summary = {
                "total_endpoints": len(self.config.endpoints),
                "total_optimizations": self.config.optimization_count,
                "performance_issues": [],
                "underused_endpoints": [],
                "high_performance_endpoints": []
            }
            
            # Analyze endpoints
            for name, endpoint in self.config.endpoints.items():
                if endpoint.usage_count > 0:
                    if endpoint.success_rate < 0.9:
                        summary["performance_issues"].append({
                            "name": name,
                            "success_rate": endpoint.success_rate,
                            "avg_response_time": endpoint.avg_response_time
                        })
                    elif endpoint.success_rate > 0.98 and endpoint.avg_response_time < 1.0:
                        summary["high_performance_endpoints"].append(name)
                else:
                    summary["underused_endpoints"].append(name)
            
            prompt = f"""
Analyze this API configuration and provide optimization recommendations:

**Configuration Summary:**
- Total endpoints: {summary['total_endpoints']}
- Total optimizations performed: {summary['total_optimizations']}
- Endpoints with performance issues: {len(summary['performance_issues'])}
- Underused endpoints: {len(summary['underused_endpoints'])}
- High-performance endpoints: {len(summary['high_performance_endpoints'])}

**Performance Issues:**
{json.dumps(summary['performance_issues'], indent=2) if summary['performance_issues'] else 'None'}

**Underused Endpoints:**
{', '.join(summary['underused_endpoints']) if summary['underused_endpoints'] else 'None'}

Provide 3-5 specific recommendations for:
1. Configuration optimization
2. Performance improvement
3. Endpoint management
4. Monitoring and alerting

Make recommendations actionable and prioritized.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API configuration expert. Provide actionable optimization recommendations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse recommendations
            recommendations_text = response.choices[0].message.content
            recommendations = []
            
            lines = recommendations_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(('-', '•', '*')) or re.match(r'^\d+\.', line):
                    recommendation = re.sub(r'^[-•*\d\.\s]+', '', line).strip()
                    if recommendation:
                        recommendations.append(recommendation)
            
            return recommendations[:5]  # Limit to 5 recommendations
            
        except Exception as e:
            logger.error(f"Config recommendation generation failed: {e}")
            return []
    
    def _dict_to_config(self, data: Dict[str, Any]) -> IntelligentConfig:
        """Convert dictionary to IntelligentConfig object."""
        config = IntelligentConfig()
        
        # Basic fields
        config.version = data.get("version", "1.0")
        config.name = data.get("name", "intelligent-api-config")
        config.global_timeout = data.get("global_timeout", 30.0)
        config.global_retry_count = data.get("global_retry_count", 3)
        config.global_headers = data.get("global_headers", {})
        config.authentication = data.get("authentication", {})
        config.azure_openai = data.get("azure_openai", {})
        config.intelligence = data.get("intelligence", config.intelligence)
        config.performance_thresholds = data.get("performance_thresholds", config.performance_thresholds)
        config.optimization_count = data.get("optimization_count", 0)
        
        # Parse timestamps
        if "created_at" in data:
            config.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            config.updated_at = datetime.fromisoformat(data["updated_at"])
        
        # Parse endpoints
        for name, endpoint_data in data.get("endpoints", {}).items():
            endpoint = APIEndpointConfig(
                name=name,
                method=endpoint_data.get("method", "GET"),
                path=endpoint_data.get("path", "/"),
                base_url=endpoint_data.get("base_url", "http://localhost:8000"),
                parameters=endpoint_data.get("parameters", {}),
                headers=endpoint_data.get("headers", {}),
                timeout=endpoint_data.get("timeout", 30.0),
                retry_count=endpoint_data.get("retry_count", 3),
                retry_delay=endpoint_data.get("retry_delay", 1.0),
                rate_limit=endpoint_data.get("rate_limit"),
                cache_ttl=endpoint_data.get("cache_ttl"),
                auto_optimize=endpoint_data.get("auto_optimize", True),
                learning_enabled=endpoint_data.get("learning_enabled", True),
                confidence_threshold=endpoint_data.get("confidence_threshold", 0.7),
                success_rate=endpoint_data.get("success_rate", 1.0),
                avg_response_time=endpoint_data.get("avg_response_time", 0.0),
                usage_count=endpoint_data.get("usage_count", 0),
                optimization_history=endpoint_data.get("optimization_history", [])
            )
            
            # Parse last_optimized timestamp
            if "last_optimized" in endpoint_data and endpoint_data["last_optimized"]:
                endpoint.last_optimized = datetime.fromisoformat(endpoint_data["last_optimized"])
            
            config.endpoints[name] = endpoint
        
        return config
    
    def _config_to_dict(self, config: IntelligentConfig) -> Dict[str, Any]:
        """Convert IntelligentConfig object to dictionary."""
        data = {
            "version": config.version,
            "name": config.name,
            "global_timeout": config.global_timeout,
            "global_retry_count": config.global_retry_count,
            "global_headers": config.global_headers,
            "authentication": config.authentication,
            "azure_openai": config.azure_openai,
            "intelligence": config.intelligence,
            "performance_thresholds": config.performance_thresholds,
            "optimization_count": config.optimization_count,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat(),
            "endpoints": {}
        }
        
        # Convert endpoints
        for name, endpoint in config.endpoints.items():
            endpoint_data = {
                "method": endpoint.method,
                "path": endpoint.path,
                "base_url": endpoint.base_url,
                "parameters": endpoint.parameters,
                "headers": endpoint.headers,
                "timeout": endpoint.timeout,
                "retry_count": endpoint.retry_count,
                "retry_delay": endpoint.retry_delay,
                "rate_limit": endpoint.rate_limit,
                "cache_ttl": endpoint.cache_ttl,
                "auto_optimize": endpoint.auto_optimize,
                "learning_enabled": endpoint.learning_enabled,
                "confidence_threshold": endpoint.confidence_threshold,
                "success_rate": endpoint.success_rate,
                "avg_response_time": endpoint.avg_response_time,
                "usage_count": endpoint.usage_count,
                "last_optimized": endpoint.last_optimized.isoformat() if endpoint.last_optimized else None,
                "optimization_history": endpoint.optimization_history
            }
            data["endpoints"][name] = endpoint_data
        
        return data
    
    def export_config(self, export_path: str, format: str = "yaml") -> bool:
        """Export configuration to a different file."""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = self._config_to_dict(self.config)
            
            with open(export_file, 'w', encoding='utf-8') as f:
                if format.lower() == 'yaml':
                    yaml.dump(data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(data, f, indent=2, default=str)
            
            logger.info(f"📤 Configuration exported to {export_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to export configuration: {e}")
            return False
    
    def get_config(self) -> IntelligentConfig:
        """Get the current configuration."""
        return self.config
    
    def close(self):
        """Clean up resources."""
        logger.info("🔒 Intelligent Configuration Manager closed")

# Example usage
if __name__ == "__main__":
    # Create configuration manager
    config_manager = IntelligentConfigManager("example_config.yaml")
    
    # Add an endpoint
    endpoint = APIEndpointConfig(
        name="get_payments",
        method="GET",
        path="/api/payments",
        base_url="http://localhost:8000"
    )
    config_manager.add_endpoint(endpoint)
    
    # Simulate some usage
    config_manager.update_endpoint_performance("get_payments", True, 0.5)
    config_manager.update_endpoint_performance("get_payments", True, 0.7)
    config_manager.update_endpoint_performance("get_payments", False, 2.0)
    
    # Generate report
    report = config_manager.generate_config_report()
    print(json.dumps(report, indent=2))
    
    # Clean up
    config_manager.close()