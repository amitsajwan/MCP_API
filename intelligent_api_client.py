#!/usr/bin/env python3
"""
Intelligent API Client with Azure OpenAI Integration
This version uses LLM capabilities to provide smart API interaction,
dynamic parameter suggestion, and intelligent error recovery.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import httpx
from openai import AzureOpenAI
import os
import asyncio
from urllib.parse import urljoin, urlparse
import re

logger = logging.getLogger(__name__)

@dataclass
class APICallResult:
    """Enhanced API call result with intelligence."""
    success: bool
    status_code: int
    data: Any
    response_time: float
    error_message: str = ""
    suggestions: List[str] = field(default_factory=list)
    retry_recommended: bool = False
    alternative_endpoints: List[str] = field(default_factory=list)
    confidence_score: float = 1.0

@dataclass
class APIPattern:
    """Learned API usage pattern."""
    endpoint: str
    method: str
    common_params: Dict[str, Any]
    success_rate: float
    avg_response_time: float
    usage_count: int
    last_used: datetime
    error_patterns: List[str] = field(default_factory=list)
    optimization_tips: List[str] = field(default_factory=list)

class IntelligentAPIClient:
    """Intelligent API client with LLM-powered features."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize HTTP client
        self.http_client = httpx.Client(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True
        )
        
        # Initialize Azure OpenAI
        self._init_llm_client()
        
        # Learning and analytics
        self.api_patterns: Dict[str, APIPattern] = {}
        self.call_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'avg_response_time': 0.0,
            'error_rate': 0.0
        }
        
        # Intelligence settings
        self.learning_enabled = config.get('intelligence', {}).get('learning_enabled', True)
        self.auto_retry_enabled = config.get('intelligence', {}).get('auto_retry_enabled', True)
        self.suggestion_enabled = config.get('intelligence', {}).get('suggestion_enabled', True)
        
        logger.info("🧠 Intelligent API Client initialized")
    
    def _init_llm_client(self):
        """Initialize LLM client for intelligent features."""
        try:
            azure_config = self.config.get('azure_openai', {})
            self.llm_client = AzureOpenAI(
                azure_endpoint=azure_config.get('endpoint') or os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=azure_config.get('api_key') or os.getenv("AZURE_OPENAI_API_KEY"),
                api_version="2024-02-15-preview"
            )
            self.deployment_name = azure_config.get('deployment', 'gpt-4')
            self.llm_available = True
            logger.info("✅ Intelligent client LLM initialized")
        except Exception as e:
            logger.warning(f"⚠️  Client LLM not available: {e}")
            self.llm_client = None
            self.llm_available = False
    
    def make_request(self, method: str, path: str, arguments: Dict[str, Any],
                    base_url: str = None, headers: Dict[str, str] = None) -> APICallResult:
        """Make intelligent API request with learning and optimization."""
        start_time = time.time()
        
        # Determine base URL
        if not base_url:
            base_url = self._determine_base_url(path, arguments)
        
        # Build full URL
        full_url = urljoin(base_url, path.lstrip('/'))
        
        # Prepare request
        request_data = self._prepare_request_data(method, arguments)
        request_headers = self._prepare_headers(headers, arguments)
        
        # Check for learned optimizations
        if self.learning_enabled:
            optimizations = self._get_learned_optimizations(method, path, arguments)
            if optimizations:
                logger.info(f"🧠 Applying learned optimizations: {optimizations}")
        
        try:
            # Make the request
            response = self._execute_request(
                method, full_url, request_data, request_headers
            )
            
            response_time = time.time() - start_time
            
            # Create result
            result = APICallResult(
                success=response.status_code < 400,
                status_code=response.status_code,
                data=self._parse_response(response),
                response_time=response_time
            )
            
            # Learn from successful call
            if result.success and self.learning_enabled:
                self._learn_from_success(method, path, arguments, result)
            
            # Add intelligent suggestions
            if self.suggestion_enabled and self.llm_available:
                result.suggestions = self._generate_suggestions(method, path, arguments, result)
            
            # Update metrics
            self._update_metrics(result)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Create error result
            result = APICallResult(
                success=False,
                status_code=0,
                data=None,
                response_time=response_time,
                error_message=str(e)
            )
            
            # Intelligent error handling
            if self.llm_available:
                result = self._handle_error_intelligently(method, path, arguments, result, e)
            
            # Learn from error
            if self.learning_enabled:
                self._learn_from_error(method, path, arguments, result)
            
            # Update metrics
            self._update_metrics(result)
            
            return result
    
    def _determine_base_url(self, path: str, arguments: Dict[str, Any]) -> str:
        """Intelligently determine the base URL."""
        # Check if path is already a full URL
        if path.startswith(('http://', 'https://')):
            parsed = urlparse(path)
            return f"{parsed.scheme}://{parsed.netloc}"
        
        # Look for base URL in config
        for api_config in self.config.get('apis', []):
            if 'base_url' in api_config:
                return api_config['base_url']
        
        # Default fallback
        return "http://localhost:8000"
    
    def _prepare_request_data(self, method: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request data based on method and arguments."""
        if method.upper() in ['GET', 'DELETE']:
            # For GET/DELETE, use query parameters
            return {'params': arguments}
        else:
            # For POST/PUT/PATCH, check for body
            if 'body' in arguments:
                return {'json': arguments['body']}
            else:
                return {'json': arguments}
    
    def _prepare_headers(self, custom_headers: Dict[str, str] = None,
                        arguments: Dict[str, Any] = None) -> Dict[str, str]:
        """Prepare request headers with intelligent defaults."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'IntelligentAPIClient/1.0'
        }
        
        # Add authentication if available
        auth_config = self.config.get('authentication', {})
        if auth_config.get('type') == 'bearer' and auth_config.get('token'):
            headers['Authorization'] = f"Bearer {auth_config['token']}"
        elif auth_config.get('type') == 'api_key':
            key_name = auth_config.get('key_name', 'X-API-Key')
            headers[key_name] = auth_config.get('key_value', '')
        
        # Add custom headers
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    def _execute_request(self, method: str, url: str, data: Dict[str, Any],
                        headers: Dict[str, str]) -> httpx.Response:
        """Execute the HTTP request."""
        logger.info(f"🌐 {method.upper()} {url}")
        
        if method.upper() == 'GET':
            return self.http_client.get(url, headers=headers, **data)
        elif method.upper() == 'POST':
            return self.http_client.post(url, headers=headers, **data)
        elif method.upper() == 'PUT':
            return self.http_client.put(url, headers=headers, **data)
        elif method.upper() == 'PATCH':
            return self.http_client.patch(url, headers=headers, **data)
        elif method.upper() == 'DELETE':
            return self.http_client.delete(url, headers=headers, **data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    def _parse_response(self, response: httpx.Response) -> Any:
        """Parse response data intelligently."""
        try:
            # Try JSON first
            return response.json()
        except json.JSONDecodeError:
            # Fallback to text
            return response.text
    
    def _generate_suggestions(self, method: str, path: str, arguments: Dict[str, Any],
                            result: APICallResult) -> List[str]:
        """Generate intelligent suggestions based on the API call."""
        if not self.llm_available:
            return []
        
        try:
            # Get historical context
            pattern_key = f"{method.upper()}:{path}"
            pattern = self.api_patterns.get(pattern_key)
            
            context = {
                'method': method,
                'path': path,
                'arguments': arguments,
                'result': {
                    'success': result.success,
                    'status_code': result.status_code,
                    'response_time': result.response_time
                },
                'historical_pattern': {
                    'success_rate': pattern.success_rate if pattern else 1.0,
                    'avg_response_time': pattern.avg_response_time if pattern else result.response_time,
                    'usage_count': pattern.usage_count if pattern else 1
                } if pattern else None
            }
            
            prompt = f"""
Analyze this API call and provide intelligent suggestions:

**API Call:**
- Method: {method.upper()}
- Path: {path}
- Arguments: {json.dumps(arguments, indent=2)}

**Result:**
- Success: {result.success}
- Status Code: {result.status_code}
- Response Time: {result.response_time:.2f}s

**Historical Context:**
{json.dumps(context.get('historical_pattern'), indent=2) if context.get('historical_pattern') else 'No historical data'}

Provide 2-3 actionable suggestions for:
1. Performance optimization
2. Better parameter usage
3. Error prevention
4. Alternative approaches

Keep suggestions practical and specific.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API optimization expert. Provide practical suggestions for API usage."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            # Parse suggestions from response
            suggestions_text = response.choices[0].message.content
            suggestions = []
            
            # Extract bullet points or numbered items
            lines = suggestions_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(('-', '•', '*')) or re.match(r'^\d+\.', line):
                    # Clean up the suggestion
                    suggestion = re.sub(r'^[-•*\d\.\s]+', '', line).strip()
                    if suggestion:
                        suggestions.append(suggestion)
            
            return suggestions[:3]  # Limit to 3 suggestions
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
            return []
    
    def _handle_error_intelligently(self, method: str, path: str, arguments: Dict[str, Any],
                                  result: APICallResult, error: Exception) -> APICallResult:
        """Handle errors with intelligent analysis and suggestions."""
        try:
            prompt = f"""
Analyze this API error and provide intelligent guidance:

**API Call:**
- Method: {method.upper()}
- Path: {path}
- Arguments: {json.dumps(arguments, indent=2)}

**Error:**
- Type: {type(error).__name__}
- Message: {str(error)}
- Response Time: {result.response_time:.2f}s

Provide a JSON response with:
1. `error_analysis`: What likely caused this error
2. `suggestions`: How to fix it (2-3 specific suggestions)
3. `retry_recommended`: Whether retrying makes sense (boolean)
4. `alternative_endpoints`: Alternative endpoints to try (if any)
5. `confidence_score`: Your confidence in the analysis (0.0-1.0)

Focus on actionable guidance.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API troubleshooting expert. Analyze errors and provide solutions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )
            
            # Parse LLM response
            response_text = response.choices[0].message.content
            
            # Try to extract JSON
            json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(1))
            else:
                analysis = json.loads(response_text)
            
            # Update result with intelligence
            result.suggestions = analysis.get('suggestions', [])
            result.retry_recommended = analysis.get('retry_recommended', False)
            result.alternative_endpoints = analysis.get('alternative_endpoints', [])
            result.confidence_score = analysis.get('confidence_score', 0.5)
            
            # Enhance error message
            error_analysis = analysis.get('error_analysis', '')
            if error_analysis:
                result.error_message = f"{result.error_message}\n\n🧠 Analysis: {error_analysis}"
            
        except Exception as e:
            logger.error(f"Intelligent error handling failed: {e}")
        
        return result
    
    def _learn_from_success(self, method: str, path: str, arguments: Dict[str, Any],
                          result: APICallResult):
        """Learn from successful API calls."""
        pattern_key = f"{method.upper()}:{path}"
        
        if pattern_key not in self.api_patterns:
            self.api_patterns[pattern_key] = APIPattern(
                endpoint=path,
                method=method.upper(),
                common_params={},
                success_rate=1.0,
                avg_response_time=result.response_time,
                usage_count=1,
                last_used=datetime.now()
            )
        else:
            pattern = self.api_patterns[pattern_key]
            
            # Update metrics
            pattern.usage_count += 1
            pattern.last_used = datetime.now()
            
            # Update average response time
            pattern.avg_response_time = (
                (pattern.avg_response_time * (pattern.usage_count - 1) + result.response_time) /
                pattern.usage_count
            )
            
            # Update success rate (assuming this was successful)
            pattern.success_rate = (
                (pattern.success_rate * (pattern.usage_count - 1) + 1.0) /
                pattern.usage_count
            )
        
        # Learn common parameter patterns
        pattern = self.api_patterns[pattern_key]
        for key, value in arguments.items():
            if key not in pattern.common_params:
                pattern.common_params[key] = {}
            
            value_str = str(value)[:50]  # Truncate long values
            if value_str not in pattern.common_params[key]:
                pattern.common_params[key][value_str] = 0
            pattern.common_params[key][value_str] += 1
        
        # Record in history
        self.call_history.append({
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'path': path,
            'arguments': arguments,
            'success': True,
            'response_time': result.response_time,
            'status_code': result.status_code
        })
        
        # Keep history manageable
        if len(self.call_history) > 1000:
            self.call_history = self.call_history[-500:]
    
    def _learn_from_error(self, method: str, path: str, arguments: Dict[str, Any],
                         result: APICallResult):
        """Learn from API call errors."""
        pattern_key = f"{method.upper()}:{path}"
        
        if pattern_key in self.api_patterns:
            pattern = self.api_patterns[pattern_key]
            
            # Update success rate
            pattern.usage_count += 1
            pattern.success_rate = (
                (pattern.success_rate * (pattern.usage_count - 1) + 0.0) /
                pattern.usage_count
            )
            
            # Record error pattern
            error_pattern = f"{result.status_code}: {result.error_message[:100]}"
            if error_pattern not in pattern.error_patterns:
                pattern.error_patterns.append(error_pattern)
                # Keep only recent error patterns
                pattern.error_patterns = pattern.error_patterns[-10:]
        
        # Record in history
        self.call_history.append({
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'path': path,
            'arguments': arguments,
            'success': False,
            'response_time': result.response_time,
            'status_code': result.status_code,
            'error': result.error_message
        })
    
    def _get_learned_optimizations(self, method: str, path: str,
                                 arguments: Dict[str, Any]) -> List[str]:
        """Get learned optimizations for this endpoint."""
        pattern_key = f"{method.upper()}:{path}"
        pattern = self.api_patterns.get(pattern_key)
        
        if not pattern:
            return []
        
        optimizations = []
        
        # Suggest based on success rate
        if pattern.success_rate < 0.8:
            optimizations.append(f"Low success rate ({pattern.success_rate:.1%}), consider parameter validation")
        
        # Suggest based on response time
        if pattern.avg_response_time > 2.0:
            optimizations.append(f"Slow response time ({pattern.avg_response_time:.1f}s), consider caching")
        
        # Suggest based on common parameters
        for param, values in pattern.common_params.items():
            if param not in arguments:
                most_common = max(values.items(), key=lambda x: x[1])
                if most_common[1] > pattern.usage_count * 0.5:  # Used in >50% of calls
                    optimizations.append(f"Consider adding common parameter '{param}': {most_common[0]}")
        
        return optimizations
    
    def _update_metrics(self, result: APICallResult):
        """Update performance metrics."""
        self.performance_metrics['total_calls'] += 1
        
        if result.success:
            self.performance_metrics['successful_calls'] += 1
        else:
            self.performance_metrics['failed_calls'] += 1
        
        # Update average response time
        total_calls = self.performance_metrics['total_calls']
        current_avg = self.performance_metrics['avg_response_time']
        self.performance_metrics['avg_response_time'] = (
            (current_avg * (total_calls - 1) + result.response_time) / total_calls
        )
        
        # Update error rate
        self.performance_metrics['error_rate'] = (
            self.performance_metrics['failed_calls'] / total_calls * 100
        )
    
    def get_analytics_report(self) -> Dict[str, Any]:
        """Generate intelligent analytics report."""
        report = {
            'performance_metrics': self.performance_metrics.copy(),
            'api_patterns': {},
            'recommendations': [],
            'generated_at': datetime.now().isoformat()
        }
        
        # Add pattern summaries
        for key, pattern in self.api_patterns.items():
            report['api_patterns'][key] = {
                'endpoint': pattern.endpoint,
                'method': pattern.method,
                'usage_count': pattern.usage_count,
                'success_rate': pattern.success_rate,
                'avg_response_time': pattern.avg_response_time,
                'last_used': pattern.last_used.isoformat(),
                'error_count': len(pattern.error_patterns)
            }
        
        # Generate recommendations
        if self.llm_available:
            try:
                recommendations = self._generate_analytics_recommendations()
                report['recommendations'] = recommendations
            except Exception as e:
                logger.error(f"Failed to generate recommendations: {e}")
        
        return report
    
    def _generate_analytics_recommendations(self) -> List[str]:
        """Generate intelligent recommendations based on analytics."""
        try:
            # Prepare analytics summary
            summary = {
                'total_calls': self.performance_metrics['total_calls'],
                'error_rate': self.performance_metrics['error_rate'],
                'avg_response_time': self.performance_metrics['avg_response_time'],
                'top_endpoints': sorted(
                    [(k, v.usage_count, v.success_rate) for k, v in self.api_patterns.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            }
            
            prompt = f"""
Analyze these API usage analytics and provide optimization recommendations:

**Overall Metrics:**
- Total API calls: {summary['total_calls']}
- Error rate: {summary['error_rate']:.1f}%
- Average response time: {summary['avg_response_time']:.2f}s

**Top Endpoints:**
{chr(10).join([f"- {endpoint}: {usage} calls, {success_rate:.1%} success" for endpoint, usage, success_rate in summary['top_endpoints']])}

Provide 3-5 specific recommendations for:
1. Performance optimization
2. Error reduction
3. API usage patterns
4. Monitoring and alerting

Make recommendations actionable and prioritized.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API performance analyst. Provide actionable optimization recommendations."},
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
            logger.error(f"Recommendation generation failed: {e}")
            return []
    
    def suggest_parameters(self, method: str, path: str) -> Dict[str, Any]:
        """Suggest parameters based on learned patterns."""
        pattern_key = f"{method.upper()}:{path}"
        pattern = self.api_patterns.get(pattern_key)
        
        if not pattern:
            return {}
        
        suggestions = {}
        
        # Suggest most common parameter values
        for param, values in pattern.common_params.items():
            if values:
                most_common = max(values.items(), key=lambda x: x[1])
                usage_percentage = most_common[1] / pattern.usage_count * 100
                
                if usage_percentage > 30:  # Used in >30% of calls
                    try:
                        # Try to parse as JSON for complex values
                        suggestions[param] = json.loads(most_common[0])
                    except json.JSONDecodeError:
                        suggestions[param] = most_common[0]
        
        return suggestions
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'http_client'):
            self.http_client.close()
        logger.info("🔒 Intelligent API Client closed")

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = {
        "apis": [
            {
                "name": "test-api",
                "base_url": "http://localhost:8000"
            }
        ],
        "azure_openai": {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "deployment": "gpt-4"
        },
        "intelligence": {
            "learning_enabled": True,
            "auto_retry_enabled": True,
            "suggestion_enabled": True
        }
    }
    
    # Create intelligent client
    client = IntelligentAPIClient(config)
    
    # Example API call
    result = client.make_request(
        method="GET",
        path="/api/payments",
        arguments={"status": "completed", "limit": 10}
    )
    
    print(f"Result: {result.success}")
    print(f"Suggestions: {result.suggestions}")
    
    # Get analytics
    analytics = client.get_analytics_report()
    print(f"Analytics: {json.dumps(analytics, indent=2)}")
    
    # Clean up
    client.close()