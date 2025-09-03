#!/usr/bin/env python3
"""
Intelligent Test Generator with Azure OpenAI Integration
This module automatically generates comprehensive test cases for APIs
using LLM capabilities to understand schemas and create edge cases.
"""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import yaml
from openai import AzureOpenAI
import re
import random
import string
from enum import Enum

logger = logging.getLogger(__name__)

class TestType(Enum):
    """Types of tests to generate."""
    POSITIVE = "positive"  # Valid inputs, expected success
    NEGATIVE = "negative"  # Invalid inputs, expected failure
    EDGE_CASE = "edge_case"  # Boundary conditions
    PERFORMANCE = "performance"  # Load and stress tests
    SECURITY = "security"  # Security-focused tests
    INTEGRATION = "integration"  # End-to-end tests

@dataclass
class TestCase:
    """Individual test case."""
    name: str
    description: str
    test_type: TestType
    method: str
    path: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    expected_status: int = 200
    expected_response: Optional[Dict[str, Any]] = None
    should_pass: bool = True
    timeout: float = 30.0
    retry_count: int = 0
    tags: List[str] = field(default_factory=list)
    priority: str = "medium"  # low, medium, high, critical
    
    # Intelligence features
    confidence_score: float = 1.0
    generated_by: str = "intelligent_generator"
    reasoning: str = ""
    related_tests: List[str] = field(default_factory=list)

@dataclass
class TestSuite:
    """Collection of test cases for an API."""
    name: str
    description: str
    api_name: str
    base_url: str
    test_cases: List[TestCase] = field(default_factory=list)
    setup_steps: List[str] = field(default_factory=list)
    teardown_steps: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "intelligent_generator"
    version: str = "1.0"
    
    # Statistics
    total_tests: int = 0
    positive_tests: int = 0
    negative_tests: int = 0
    edge_case_tests: int = 0
    performance_tests: int = 0
    security_tests: int = 0
    integration_tests: int = 0

class IntelligentTestGenerator:
    """Intelligent test generator with LLM-powered test case creation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM client
        self._init_llm_client()
        
        # Test generation settings
        self.generation_settings = self.config.get('generation', {
            'max_tests_per_endpoint': 20,
            'include_edge_cases': True,
            'include_security_tests': True,
            'include_performance_tests': False,
            'confidence_threshold': 0.7,
            'creativity_level': 0.3  # 0.0 = conservative, 1.0 = creative
        })
        
        # Data generators for realistic test data
        self.data_generators = {
            'email': self._generate_email,
            'phone': self._generate_phone,
            'name': self._generate_name,
            'address': self._generate_address,
            'date': self._generate_date,
            'uuid': self._generate_uuid,
            'url': self._generate_url,
            'credit_card': self._generate_credit_card,
            'password': self._generate_password
        }
        
        logger.info("🧠 Intelligent Test Generator initialized")
    
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
            logger.info("✅ Test generator LLM initialized")
        except Exception as e:
            logger.warning(f"⚠️  Test generator LLM not available: {e}")
            self.llm_client = None
            self.llm_available = False
    
    def generate_test_suite(self, api_spec: Dict[str, Any], 
                          api_name: str = "api") -> TestSuite:
        """Generate comprehensive test suite for an API."""
        logger.info(f"🧪 Generating test suite for {api_name}")
        
        # Create test suite
        suite = TestSuite(
            name=f"{api_name}_test_suite",
            description=f"Intelligent test suite for {api_name} API",
            api_name=api_name,
            base_url=api_spec.get('base_url', 'http://localhost:8000')
        )
        
        # Generate tests for each endpoint
        endpoints = api_spec.get('endpoints', [])
        for endpoint in endpoints:
            endpoint_tests = self._generate_endpoint_tests(endpoint)
            suite.test_cases.extend(endpoint_tests)
        
        # Update statistics
        self._update_suite_statistics(suite)
        
        # Generate setup/teardown if needed
        if self.llm_available:
            suite.setup_steps = self._generate_setup_steps(api_spec)
            suite.teardown_steps = self._generate_teardown_steps(api_spec)
        
        logger.info(f"✅ Generated {len(suite.test_cases)} test cases for {api_name}")
        return suite
    
    def _generate_endpoint_tests(self, endpoint: Dict[str, Any]) -> List[TestCase]:
        """Generate test cases for a single endpoint."""
        tests = []
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '/')
        schema = endpoint.get('schema', {})
        
        logger.info(f"🔍 Generating tests for {method} {path}")
        
        # Generate positive tests
        positive_tests = self._generate_positive_tests(endpoint)
        tests.extend(positive_tests)
        
        # Generate negative tests
        negative_tests = self._generate_negative_tests(endpoint)
        tests.extend(negative_tests)
        
        # Generate edge case tests
        if self.generation_settings.get('include_edge_cases', True):
            edge_tests = self._generate_edge_case_tests(endpoint)
            tests.extend(edge_tests)
        
        # Generate security tests
        if self.generation_settings.get('include_security_tests', True):
            security_tests = self._generate_security_tests(endpoint)
            tests.extend(security_tests)
        
        # Generate performance tests
        if self.generation_settings.get('include_performance_tests', False):
            performance_tests = self._generate_performance_tests(endpoint)
            tests.extend(performance_tests)
        
        # Use LLM for additional intelligent tests
        if self.llm_available:
            llm_tests = self._generate_llm_tests(endpoint)
            tests.extend(llm_tests)
        
        # Limit number of tests per endpoint
        max_tests = self.generation_settings.get('max_tests_per_endpoint', 20)
        if len(tests) > max_tests:
            # Prioritize tests by type and confidence
            tests.sort(key=lambda t: (t.priority == 'critical', t.confidence_score), reverse=True)
            tests = tests[:max_tests]
        
        return tests
    
    def _generate_positive_tests(self, endpoint: Dict[str, Any]) -> List[TestCase]:
        """Generate positive test cases (valid inputs)."""
        tests = []
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '/')
        schema = endpoint.get('schema', {})
        
        # Basic valid test
        test = TestCase(
            name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_valid",
            description=f"Test {method} {path} with valid parameters",
            test_type=TestType.POSITIVE,
            method=method,
            path=path,
            expected_status=200,
            should_pass=True,
            priority="high",
            reasoning="Basic positive test with valid parameters"
        )
        
        # Generate valid parameters based on schema
        if schema:
            test.parameters = self._generate_valid_parameters(schema)
            if method.upper() in ['POST', 'PUT', 'PATCH'] and 'body' in schema:
                test.body = self._generate_valid_body(schema['body'])
        
        tests.append(test)
        
        # Generate additional positive variations
        if schema and 'properties' in schema:
            for i in range(2):  # Generate 2 more variations
                variation_test = TestCase(
                    name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_valid_variation_{i+1}",
                    description=f"Test {method} {path} with valid parameters (variation {i+1})",
                    test_type=TestType.POSITIVE,
                    method=method,
                    path=path,
                    expected_status=200,
                    should_pass=True,
                    priority="medium",
                    reasoning=f"Positive test variation {i+1} with different valid values"
                )
                
                variation_test.parameters = self._generate_valid_parameters(schema, variation=i+1)
                if method.upper() in ['POST', 'PUT', 'PATCH'] and 'body' in schema:
                    variation_test.body = self._generate_valid_body(schema['body'], variation=i+1)
                
                tests.append(variation_test)
        
        return tests
    
    def _generate_negative_tests(self, endpoint: Dict[str, Any]) -> List[TestCase]:
        """Generate negative test cases (invalid inputs)."""
        tests = []
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '/')
        schema = endpoint.get('schema', {})
        
        if not schema:
            return tests
        
        # Test missing required parameters
        if 'required' in schema:
            for required_param in schema['required']:
                test = TestCase(
                    name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_missing_{required_param}",
                    description=f"Test {method} {path} with missing required parameter: {required_param}",
                    test_type=TestType.NEGATIVE,
                    method=method,
                    path=path,
                    expected_status=400,
                    should_pass=False,
                    priority="high",
                    reasoning=f"Test missing required parameter: {required_param}"
                )
                
                # Generate parameters without the required one
                test.parameters = self._generate_valid_parameters(schema)
                if required_param in test.parameters:
                    del test.parameters[required_param]
                
                tests.append(test)
        
        # Test invalid parameter types
        if 'properties' in schema:
            for param_name, param_schema in schema['properties'].items():
                param_type = param_schema.get('type', 'string')
                
                test = TestCase(
                    name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_invalid_{param_name}_type",
                    description=f"Test {method} {path} with invalid type for {param_name}",
                    test_type=TestType.NEGATIVE,
                    method=method,
                    path=path,
                    expected_status=400,
                    should_pass=False,
                    priority="medium",
                    reasoning=f"Test invalid type for parameter: {param_name}"
                )
                
                test.parameters = self._generate_valid_parameters(schema)
                test.parameters[param_name] = self._generate_invalid_value(param_type)
                
                tests.append(test)
        
        # Test invalid enum values
        if 'properties' in schema:
            for param_name, param_schema in schema['properties'].items():
                if 'enum' in param_schema:
                    test = TestCase(
                        name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_invalid_{param_name}_enum",
                        description=f"Test {method} {path} with invalid enum value for {param_name}",
                        test_type=TestType.NEGATIVE,
                        method=method,
                        path=path,
                        expected_status=400,
                        should_pass=False,
                        priority="medium",
                        reasoning=f"Test invalid enum value for parameter: {param_name}"
                    )
                    
                    test.parameters = self._generate_valid_parameters(schema)
                    test.parameters[param_name] = "invalid_enum_value_12345"
                    
                    tests.append(test)
        
        return tests
    
    def _generate_edge_case_tests(self, endpoint: Dict[str, Any]) -> List[TestCase]:
        """Generate edge case test cases (boundary conditions)."""
        tests = []
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '/')
        schema = endpoint.get('schema', {})
        
        if not schema or 'properties' not in schema:
            return tests
        
        # Test boundary values
        for param_name, param_schema in schema['properties'].items():
            param_type = param_schema.get('type', 'string')
            
            # String length boundaries
            if param_type == 'string':
                if 'minLength' in param_schema:
                    # Test minimum length
                    test = TestCase(
                        name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_min_length_{param_name}",
                        description=f"Test {method} {path} with minimum length for {param_name}",
                        test_type=TestType.EDGE_CASE,
                        method=method,
                        path=path,
                        expected_status=200,
                        should_pass=True,
                        priority="medium",
                        reasoning=f"Test minimum string length boundary for {param_name}"
                    )
                    
                    test.parameters = self._generate_valid_parameters(schema)
                    min_length = param_schema['minLength']
                    test.parameters[param_name] = 'a' * min_length
                    
                    tests.append(test)
                
                if 'maxLength' in param_schema:
                    # Test maximum length
                    test = TestCase(
                        name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_max_length_{param_name}",
                        description=f"Test {method} {path} with maximum length for {param_name}",
                        test_type=TestType.EDGE_CASE,
                        method=method,
                        path=path,
                        expected_status=200,
                        should_pass=True,
                        priority="medium",
                        reasoning=f"Test maximum string length boundary for {param_name}"
                    )
                    
                    test.parameters = self._generate_valid_parameters(schema)
                    max_length = param_schema['maxLength']
                    test.parameters[param_name] = 'a' * max_length
                    
                    tests.append(test)
            
            # Numeric boundaries
            elif param_type in ['integer', 'number']:
                if 'minimum' in param_schema:
                    # Test minimum value
                    test = TestCase(
                        name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_min_value_{param_name}",
                        description=f"Test {method} {path} with minimum value for {param_name}",
                        test_type=TestType.EDGE_CASE,
                        method=method,
                        path=path,
                        expected_status=200,
                        should_pass=True,
                        priority="medium",
                        reasoning=f"Test minimum numeric value boundary for {param_name}"
                    )
                    
                    test.parameters = self._generate_valid_parameters(schema)
                    test.parameters[param_name] = param_schema['minimum']
                    
                    tests.append(test)
                
                if 'maximum' in param_schema:
                    # Test maximum value
                    test = TestCase(
                        name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_max_value_{param_name}",
                        description=f"Test {method} {path} with maximum value for {param_name}",
                        test_type=TestType.EDGE_CASE,
                        method=method,
                        path=path,
                        expected_status=200,
                        should_pass=True,
                        priority="medium",
                        reasoning=f"Test maximum numeric value boundary for {param_name}"
                    )
                    
                    test.parameters = self._generate_valid_parameters(schema)
                    test.parameters[param_name] = param_schema['maximum']
                    
                    tests.append(test)
        
        return tests
    
    def _generate_security_tests(self, endpoint: Dict[str, Any]) -> List[TestCase]:
        """Generate security-focused test cases."""
        tests = []
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '/')
        schema = endpoint.get('schema', {})
        
        # SQL Injection tests
        if schema and 'properties' in schema:
            for param_name, param_schema in schema['properties'].items():
                if param_schema.get('type') == 'string':
                    test = TestCase(
                        name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_sql_injection_{param_name}",
                        description=f"Test {method} {path} for SQL injection vulnerability in {param_name}",
                        test_type=TestType.SECURITY,
                        method=method,
                        path=path,
                        expected_status=400,
                        should_pass=False,
                        priority="critical",
                        reasoning=f"Test SQL injection vulnerability in parameter: {param_name}",
                        tags=["security", "sql_injection"]
                    )
                    
                    test.parameters = self._generate_valid_parameters(schema)
                    test.parameters[param_name] = "'; DROP TABLE users; --"
                    
                    tests.append(test)
        
        # XSS tests
        if schema and 'properties' in schema:
            for param_name, param_schema in schema['properties'].items():
                if param_schema.get('type') == 'string':
                    test = TestCase(
                        name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_xss_{param_name}",
                        description=f"Test {method} {path} for XSS vulnerability in {param_name}",
                        test_type=TestType.SECURITY,
                        method=method,
                        path=path,
                        expected_status=400,
                        should_pass=False,
                        priority="critical",
                        reasoning=f"Test XSS vulnerability in parameter: {param_name}",
                        tags=["security", "xss"]
                    )
                    
                    test.parameters = self._generate_valid_parameters(schema)
                    test.parameters[param_name] = "<script>alert('XSS')</script>"
                    
                    tests.append(test)
        
        # Authentication bypass test
        test = TestCase(
            name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_no_auth",
            description=f"Test {method} {path} without authentication",
            test_type=TestType.SECURITY,
            method=method,
            path=path,
            expected_status=401,
            should_pass=False,
            priority="high",
            reasoning="Test authentication requirement",
            tags=["security", "authentication"]
        )
        
        if schema:
            test.parameters = self._generate_valid_parameters(schema)
        
        tests.append(test)
        
        return tests
    
    def _generate_performance_tests(self, endpoint: Dict[str, Any]) -> List[TestCase]:
        """Generate performance test cases."""
        tests = []
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '/')
        schema = endpoint.get('schema', {})
        
        # Response time test
        test = TestCase(
            name=f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_response_time",
            description=f"Test {method} {path} response time",
            test_type=TestType.PERFORMANCE,
            method=method,
            path=path,
            expected_status=200,
            should_pass=True,
            timeout=2.0,  # Expect response within 2 seconds
            priority="medium",
            reasoning="Test API response time performance",
            tags=["performance", "response_time"]
        )
        
        if schema:
            test.parameters = self._generate_valid_parameters(schema)
        
        tests.append(test)
        
        return tests
    
    def _generate_llm_tests(self, endpoint: Dict[str, Any]) -> List[TestCase]:
        """Generate additional test cases using LLM intelligence."""
        if not self.llm_available:
            return []
        
        try:
            method = endpoint.get('method', 'GET')
            path = endpoint.get('path', '/')
            schema = endpoint.get('schema', {})
            
            prompt = f"""
Analyze this API endpoint and suggest additional intelligent test cases:

**Endpoint:**
- Method: {method}
- Path: {path}
- Schema: {json.dumps(schema, indent=2) if schema else 'No schema provided'}

**Context:**
I already have basic positive, negative, edge case, and security tests.
Suggest 3-5 additional creative test cases that would be valuable for thorough testing.

For each test case, provide:
1. Test name (descriptive)
2. Test description
3. Test type (positive/negative/edge_case/security/performance/integration)
4. Expected HTTP status code
5. Test parameters (if any)
6. Request body (if applicable)
7. Reasoning for why this test is important
8. Priority (low/medium/high/critical)

Provide response as JSON array of test cases:
[
  {{
    "name": "test_name",
    "description": "test description",
    "test_type": "positive|negative|edge_case|security|performance|integration",
    "expected_status": 200,
    "parameters": {{}},
    "body": null,
    "reasoning": "why this test is important",
    "priority": "medium",
    "confidence": 0.8
  }}
]

Focus on realistic scenarios and edge cases that might be missed.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert API testing specialist. Generate comprehensive and creative test cases."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.generation_settings.get('creativity_level', 0.3),
                max_tokens=1000
            )
            
            # Parse LLM response
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                test_data = json.loads(json_match.group(1))
            else:
                test_data = json.loads(response_text)
            
            # Convert to TestCase objects
            tests = []
            for test_info in test_data:
                if test_info.get('confidence', 0) >= self.generation_settings.get('confidence_threshold', 0.7):
                    test = TestCase(
                        name=test_info['name'],
                        description=test_info['description'],
                        test_type=TestType(test_info['test_type']),
                        method=method,
                        path=path,
                        parameters=test_info.get('parameters', {}),
                        body=test_info.get('body'),
                        expected_status=test_info.get('expected_status', 200),
                        should_pass=test_info.get('expected_status', 200) < 400,
                        priority=test_info.get('priority', 'medium'),
                        reasoning=test_info.get('reasoning', ''),
                        confidence_score=test_info.get('confidence', 0.8),
                        generated_by="llm",
                        tags=["llm_generated"]
                    )
                    tests.append(test)
            
            logger.info(f"🧠 Generated {len(tests)} LLM-powered test cases for {method} {path}")
            return tests
            
        except Exception as e:
            logger.error(f"❌ Failed to generate LLM tests: {e}")
            return []
    
    def _generate_valid_parameters(self, schema: Dict[str, Any], variation: int = 0) -> Dict[str, Any]:
        """Generate valid parameters based on schema."""
        parameters = {}
        
        if 'properties' not in schema:
            return parameters
        
        for param_name, param_schema in schema['properties'].items():
            param_type = param_schema.get('type', 'string')
            
            if param_type == 'string':
                if 'enum' in param_schema:
                    # Choose from enum values
                    enum_values = param_schema['enum']
                    parameters[param_name] = enum_values[variation % len(enum_values)]
                elif param_name.lower() in self.data_generators:
                    # Use specialized generator
                    parameters[param_name] = self.data_generators[param_name.lower()]()
                else:
                    # Generate based on constraints
                    min_length = param_schema.get('minLength', 1)
                    max_length = param_schema.get('maxLength', 50)
                    length = min(min_length + variation * 5, max_length)
                    parameters[param_name] = self._generate_string(length)
            
            elif param_type == 'integer':
                minimum = param_schema.get('minimum', 1)
                maximum = param_schema.get('maximum', 1000)
                parameters[param_name] = minimum + (variation * 10) % (maximum - minimum + 1)
            
            elif param_type == 'number':
                minimum = param_schema.get('minimum', 1.0)
                maximum = param_schema.get('maximum', 1000.0)
                parameters[param_name] = minimum + (variation * 10.5) % (maximum - minimum)
            
            elif param_type == 'boolean':
                parameters[param_name] = variation % 2 == 0
            
            elif param_type == 'array':
                # Generate simple array
                item_type = param_schema.get('items', {}).get('type', 'string')
                if item_type == 'string':
                    parameters[param_name] = [f"item_{i}_{variation}" for i in range(1, 4)]
                elif item_type == 'integer':
                    parameters[param_name] = [i + variation for i in range(1, 4)]
        
        return parameters
    
    def _generate_valid_body(self, body_schema: Dict[str, Any], variation: int = 0) -> Dict[str, Any]:
        """Generate valid request body based on schema."""
        return self._generate_valid_parameters(body_schema, variation)
    
    def _generate_invalid_value(self, param_type: str) -> Any:
        """Generate invalid value for a parameter type."""
        if param_type == 'string':
            return 12345  # Number instead of string
        elif param_type == 'integer':
            return "not_a_number"  # String instead of integer
        elif param_type == 'number':
            return "not_a_number"  # String instead of number
        elif param_type == 'boolean':
            return "not_a_boolean"  # String instead of boolean
        elif param_type == 'array':
            return "not_an_array"  # String instead of array
        else:
            return None
    
    def _generate_string(self, length: int) -> str:
        """Generate random string of specified length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    # Data generators for realistic test data
    def _generate_email(self) -> str:
        """Generate realistic email address."""
        domains = ['example.com', 'test.org', 'demo.net']
        username = ''.join(random.choices(string.ascii_lowercase, k=8))
        domain = random.choice(domains)
        return f"{username}@{domain}"
    
    def _generate_phone(self) -> str:
        """Generate realistic phone number."""
        return f"+1-{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    
    def _generate_name(self) -> str:
        """Generate realistic name."""
        first_names = ['John', 'Jane', 'Alice', 'Bob', 'Charlie', 'Diana']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia']
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    
    def _generate_address(self) -> str:
        """Generate realistic address."""
        streets = ['Main St', 'Oak Ave', 'Pine Rd', 'Elm Dr', 'Cedar Ln']
        return f"{random.randint(100, 9999)} {random.choice(streets)}"
    
    def _generate_date(self) -> str:
        """Generate realistic date."""
        year = random.randint(2020, 2024)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year}-{month:02d}-{day:02d}"
    
    def _generate_uuid(self) -> str:
        """Generate UUID-like string."""
        import uuid
        return str(uuid.uuid4())
    
    def _generate_url(self) -> str:
        """Generate realistic URL."""
        domains = ['example.com', 'test.org', 'demo.net']
        paths = ['api/v1', 'data', 'resources', 'items']
        return f"https://{random.choice(domains)}/{random.choice(paths)}"
    
    def _generate_credit_card(self) -> str:
        """Generate test credit card number."""
        # Generate test Visa number (starts with 4)
        return f"4{random.randint(100000000000000, 999999999999999)}"
    
    def _generate_password(self) -> str:
        """Generate realistic password."""
        return ''.join(random.choices(string.ascii_letters + string.digits + '!@#$%', k=12))
    
    def _generate_setup_steps(self, api_spec: Dict[str, Any]) -> List[str]:
        """Generate intelligent setup steps for test suite."""
        if not self.llm_available:
            return []
        
        try:
            prompt = f"""
Analyze this API specification and suggest setup steps for testing:

**API Spec:**
{json.dumps(api_spec, indent=2)}

Suggest 3-5 setup steps that should be performed before running tests.
For example:
- Authentication setup
- Database initialization
- Test data creation
- Environment configuration

Provide as a JSON array of strings:
["step 1", "step 2", "step 3"]
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a test automation expert. Suggest practical setup steps."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                steps = json.loads(json_match.group(1))
            else:
                steps = json.loads(response_text)
            
            return steps if isinstance(steps, list) else []
            
        except Exception as e:
            logger.error(f"Failed to generate setup steps: {e}")
            return []
    
    def _generate_teardown_steps(self, api_spec: Dict[str, Any]) -> List[str]:
        """Generate intelligent teardown steps for test suite."""
        if not self.llm_available:
            return []
        
        try:
            prompt = f"""
Analyze this API specification and suggest teardown steps for testing:

**API Spec:**
{json.dumps(api_spec, indent=2)}

Suggest 3-5 teardown steps that should be performed after running tests.
For example:
- Clean up test data
- Reset database state
- Clear authentication tokens
- Restore environment

Provide as a JSON array of strings:
["step 1", "step 2", "step 3"]
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a test automation expert. Suggest practical teardown steps."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                steps = json.loads(json_match.group(1))
            else:
                steps = json.loads(response_text)
            
            return steps if isinstance(steps, list) else []
            
        except Exception as e:
            logger.error(f"Failed to generate teardown steps: {e}")
            return []
    
    def _update_suite_statistics(self, suite: TestSuite):
        """Update test suite statistics."""
        suite.total_tests = len(suite.test_cases)
        
        for test in suite.test_cases:
            if test.test_type == TestType.POSITIVE:
                suite.positive_tests += 1
            elif test.test_type == TestType.NEGATIVE:
                suite.negative_tests += 1
            elif test.test_type == TestType.EDGE_CASE:
                suite.edge_case_tests += 1
            elif test.test_type == TestType.PERFORMANCE:
                suite.performance_tests += 1
            elif test.test_type == TestType.SECURITY:
                suite.security_tests += 1
            elif test.test_type == TestType.INTEGRATION:
                suite.integration_tests += 1
    
    def export_test_suite(self, suite: TestSuite, output_path: str, 
                         format: str = "json") -> bool:
        """Export test suite to file."""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dictionary
            suite_data = {
                "name": suite.name,
                "description": suite.description,
                "api_name": suite.api_name,
                "base_url": suite.base_url,
                "version": suite.version,
                "created_at": suite.created_at.isoformat(),
                "updated_at": suite.updated_at.isoformat(),
                "generated_by": suite.generated_by,
                "statistics": {
                    "total_tests": suite.total_tests,
                    "positive_tests": suite.positive_tests,
                    "negative_tests": suite.negative_tests,
                    "edge_case_tests": suite.edge_case_tests,
                    "performance_tests": suite.performance_tests,
                    "security_tests": suite.security_tests,
                    "integration_tests": suite.integration_tests
                },
                "setup_steps": suite.setup_steps,
                "teardown_steps": suite.teardown_steps,
                "test_cases": []
            }
            
            # Convert test cases
            for test in suite.test_cases:
                test_data = {
                    "name": test.name,
                    "description": test.description,
                    "test_type": test.test_type.value,
                    "method": test.method,
                    "path": test.path,
                    "parameters": test.parameters,
                    "headers": test.headers,
                    "body": test.body,
                    "expected_status": test.expected_status,
                    "expected_response": test.expected_response,
                    "should_pass": test.should_pass,
                    "timeout": test.timeout,
                    "retry_count": test.retry_count,
                    "tags": test.tags,
                    "priority": test.priority,
                    "confidence_score": test.confidence_score,
                    "generated_by": test.generated_by,
                    "reasoning": test.reasoning,
                    "related_tests": test.related_tests
                }
                suite_data["test_cases"].append(test_data)
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                if format.lower() == 'yaml':
                    yaml.dump(suite_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(suite_data, f, indent=2, default=str)
            
            logger.info(f"📤 Test suite exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to export test suite: {e}")
            return False
    
    def generate_test_report(self, suite: TestSuite) -> Dict[str, Any]:
        """Generate intelligent test report."""
        report = {
            "suite_info": {
                "name": suite.name,
                "description": suite.description,
                "api_name": suite.api_name,
                "total_tests": suite.total_tests,
                "generated_at": datetime.now().isoformat()
            },
            "statistics": {
                "positive_tests": suite.positive_tests,
                "negative_tests": suite.negative_tests,
                "edge_case_tests": suite.edge_case_tests,
                "performance_tests": suite.performance_tests,
                "security_tests": suite.security_tests,
                "integration_tests": suite.integration_tests
            },
            "test_coverage": {
                "endpoints_covered": len(set(test.path for test in suite.test_cases)),
                "methods_covered": list(set(test.method for test in suite.test_cases)),
                "test_types_covered": list(set(test.test_type.value for test in suite.test_cases))
            },
            "priority_distribution": {},
            "confidence_analysis": {
                "high_confidence_tests": 0,
                "medium_confidence_tests": 0,
                "low_confidence_tests": 0,
                "average_confidence": 0.0
            },
            "recommendations": []
        }
        
        # Calculate priority distribution
        priorities = [test.priority for test in suite.test_cases]
        for priority in ['critical', 'high', 'medium', 'low']:
            report["priority_distribution"][priority] = priorities.count(priority)
        
        # Calculate confidence analysis
        confidences = [test.confidence_score for test in suite.test_cases]
        if confidences:
            report["confidence_analysis"]["average_confidence"] = sum(confidences) / len(confidences)
            
            for confidence in confidences:
                if confidence >= 0.8:
                    report["confidence_analysis"]["high_confidence_tests"] += 1
                elif confidence >= 0.6:
                    report["confidence_analysis"]["medium_confidence_tests"] += 1
                else:
                    report["confidence_analysis"]["low_confidence_tests"] += 1
        
        # Generate recommendations
        if self.llm_available:
            try:
                recommendations = self._generate_test_recommendations(suite)
                report["recommendations"] = recommendations
            except Exception as e:
                logger.error(f"Failed to generate test recommendations: {e}")
        
        return report
    
    def _generate_test_recommendations(self, suite: TestSuite) -> List[str]:
        """Generate intelligent test recommendations."""
        try:
            summary = {
                "total_tests": suite.total_tests,
                "test_distribution": {
                    "positive": suite.positive_tests,
                    "negative": suite.negative_tests,
                    "edge_case": suite.edge_case_tests,
                    "security": suite.security_tests,
                    "performance": suite.performance_tests
                },
                "endpoints": len(set(test.path for test in suite.test_cases)),
                "methods": list(set(test.method for test in suite.test_cases))
            }
            
            prompt = f"""
Analyze this test suite and provide recommendations for improvement:

**Test Suite Summary:**
- Total tests: {summary['total_tests']}
- Positive tests: {summary['test_distribution']['positive']}
- Negative tests: {summary['test_distribution']['negative']}
- Edge case tests: {summary['test_distribution']['edge_case']}
- Security tests: {summary['test_distribution']['security']}
- Performance tests: {summary['test_distribution']['performance']}
- Endpoints covered: {summary['endpoints']}
- HTTP methods: {', '.join(summary['methods'])}

Provide 3-5 specific recommendations for:
1. Test coverage improvement
2. Test quality enhancement
3. Missing test scenarios
4. Test maintenance

Make recommendations actionable and prioritized.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a test strategy expert. Provide actionable recommendations for test improvement."},
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
            logger.error(f"Test recommendation generation failed: {e}")
            return []

# Example usage
if __name__ == "__main__":
    # Example API specification
    api_spec = {
        "name": "payment-api",
        "base_url": "http://localhost:8000",
        "endpoints": [
            {
                "name": "create_payment",
                "method": "POST",
                "path": "/api/payments",
                "schema": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number", "minimum": 0.01, "maximum": 10000},
                        "currency": {"type": "string", "enum": ["USD", "EUR", "GBP"]},
                        "description": {"type": "string", "minLength": 1, "maxLength": 255}
                    },
                    "required": ["amount", "currency"]
                }
            },
            {
                "name": "get_payments",
                "method": "GET",
                "path": "/api/payments",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pending", "completed", "failed"]},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                        "offset": {"type": "integer", "minimum": 0}
                    }
                }
            }
        ]
    }
    
    # Create test generator
    generator = IntelligentTestGenerator({
        "azure_openai": {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "deployment": "gpt-4"
        },
        "generation": {
            "max_tests_per_endpoint": 15,
            "include_edge_cases": True,
            "include_security_tests": True,
            "include_performance_tests": True,
            "confidence_threshold": 0.7,
            "creativity_level": 0.4
        }
    })
    
    # Generate test suite
    suite = generator.generate_test_suite(api_spec, "payment-api")
    
    # Export test suite
    generator.export_test_suite(suite, "generated_test_suite.json")
    
    # Generate report
    report = generator.generate_test_report(suite)
    print(json.dumps(report, indent=2))
    
    print(f"\n✅ Generated {suite.total_tests} test cases:")
    print(f"  - Positive: {suite.positive_tests}")
    print(f"  - Negative: {suite.negative_tests}")
    print(f"  - Edge cases: {suite.edge_case_tests}")
    print(f"  - Security: {suite.security_tests}")
    print(f"  - Performance: {suite.performance_tests}")