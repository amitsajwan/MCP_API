#!/usr/bin/env python3
"""
Intelligent Documentation Generator with Azure OpenAI Integration
This module automatically generates comprehensive API documentation
using LLM capabilities to understand code and create user-friendly docs.
"""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import yaml
from openai import AzureOpenAI
import re
import ast
import inspect
from enum import Enum
import markdown
from jinja2 import Template

logger = logging.getLogger(__name__)

class DocumentationType(Enum):
    """Types of documentation to generate."""
    API_REFERENCE = "api_reference"
    USER_GUIDE = "user_guide"
    DEVELOPER_GUIDE = "developer_guide"
    QUICK_START = "quick_start"
    TROUBLESHOOTING = "troubleshooting"
    CHANGELOG = "changelog"
    README = "readme"

@dataclass
class APIEndpoint:
    """API endpoint documentation."""
    name: str
    method: str
    path: str
    description: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Intelligence features
    generated_description: str = ""
    usage_patterns: List[str] = field(default_factory=list)
    common_errors: List[Dict[str, str]] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    related_endpoints: List[str] = field(default_factory=list)

@dataclass
class DocumentationSection:
    """Documentation section."""
    title: str
    content: str
    section_type: str
    order: int = 0
    subsections: List['DocumentationSection'] = field(default_factory=list)
    
    # Metadata
    generated_by: str = "intelligent_generator"
    confidence_score: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class Documentation:
    """Complete documentation package."""
    title: str
    description: str
    version: str
    api_name: str
    base_url: str
    
    # Content sections
    sections: List[DocumentationSection] = field(default_factory=list)
    endpoints: List[APIEndpoint] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "intelligent_generator"
    
    # Configuration
    theme: str = "default"
    language: str = "en"
    output_formats: List[str] = field(default_factory=lambda: ["markdown", "html"])

class IntelligentDocumentationGenerator:
    """Intelligent documentation generator with LLM-powered content creation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM client
        self._init_llm_client()
        
        # Documentation settings
        self.doc_settings = self.config.get('documentation', {
            'include_examples': True,
            'include_troubleshooting': True,
            'include_best_practices': True,
            'generate_diagrams': False,
            'audience_level': 'intermediate',  # beginner, intermediate, advanced
            'writing_style': 'professional',  # casual, professional, technical
            'include_code_samples': True
        })
        
        # Templates for different documentation types
        self.templates = {
            'api_reference': self._get_api_reference_template(),
            'user_guide': self._get_user_guide_template(),
            'quick_start': self._get_quick_start_template(),
            'readme': self._get_readme_template()
        }
        
        logger.info("📚 Intelligent Documentation Generator initialized")
    
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
            logger.info("✅ Documentation generator LLM initialized")
        except Exception as e:
            logger.warning(f"⚠️  Documentation generator LLM not available: {e}")
            self.llm_client = None
            self.llm_available = False
    
    def generate_documentation(self, api_spec: Dict[str, Any], 
                            doc_type: DocumentationType = DocumentationType.API_REFERENCE,
                            api_name: str = "API") -> Documentation:
        """Generate comprehensive documentation for an API."""
        logger.info(f"📖 Generating {doc_type.value} documentation for {api_name}")
        
        # Create documentation object
        doc = Documentation(
            title=f"{api_name} {doc_type.value.replace('_', ' ').title()}",
            description=f"Comprehensive {doc_type.value.replace('_', ' ')} for {api_name}",
            version=api_spec.get('version', '1.0.0'),
            api_name=api_name,
            base_url=api_spec.get('base_url', 'http://localhost:8000')
        )
        
        # Process endpoints
        endpoints = api_spec.get('endpoints', [])
        for endpoint_spec in endpoints:
            endpoint = self._process_endpoint(endpoint_spec)
            doc.endpoints.append(endpoint)
        
        # Generate sections based on documentation type
        if doc_type == DocumentationType.API_REFERENCE:
            doc.sections = self._generate_api_reference_sections(doc)
        elif doc_type == DocumentationType.USER_GUIDE:
            doc.sections = self._generate_user_guide_sections(doc)
        elif doc_type == DocumentationType.QUICK_START:
            doc.sections = self._generate_quick_start_sections(doc)
        elif doc_type == DocumentationType.README:
            doc.sections = self._generate_readme_sections(doc)
        else:
            doc.sections = self._generate_generic_sections(doc)
        
        # Enhance with LLM if available
        if self.llm_available:
            doc = self._enhance_documentation_with_llm(doc, doc_type)
        
        logger.info(f"✅ Generated documentation with {len(doc.sections)} sections and {len(doc.endpoints)} endpoints")
        return doc
    
    def _process_endpoint(self, endpoint_spec: Dict[str, Any]) -> APIEndpoint:
        """Process and enhance endpoint specification."""
        endpoint = APIEndpoint(
            name=endpoint_spec.get('name', 'unnamed_endpoint'),
            method=endpoint_spec.get('method', 'GET'),
            path=endpoint_spec.get('path', '/'),
            description=endpoint_spec.get('description', '')
        )
        
        # Process schema if available
        schema = endpoint_spec.get('schema', {})
        if schema:
            endpoint.parameters = self._extract_parameters(schema)
            endpoint.request_body = self._extract_request_body(schema)
            endpoint.responses = self._extract_responses(endpoint_spec)
        
        # Generate examples
        endpoint.examples = self._generate_endpoint_examples(endpoint)
        
        # Extract tags
        endpoint.tags = endpoint_spec.get('tags', [])
        
        return endpoint
    
    def _extract_parameters(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract parameters from schema."""
        parameters = []
        
        if 'properties' not in schema:
            return parameters
        
        required_fields = schema.get('required', [])
        
        for param_name, param_schema in schema['properties'].items():
            parameter = {
                'name': param_name,
                'type': param_schema.get('type', 'string'),
                'required': param_name in required_fields,
                'description': param_schema.get('description', ''),
                'example': self._generate_example_value(param_schema)
            }
            
            # Add constraints
            if 'enum' in param_schema:
                parameter['enum'] = param_schema['enum']
            if 'minimum' in param_schema:
                parameter['minimum'] = param_schema['minimum']
            if 'maximum' in param_schema:
                parameter['maximum'] = param_schema['maximum']
            if 'minLength' in param_schema:
                parameter['minLength'] = param_schema['minLength']
            if 'maxLength' in param_schema:
                parameter['maxLength'] = param_schema['maxLength']
            if 'pattern' in param_schema:
                parameter['pattern'] = param_schema['pattern']
            
            parameters.append(parameter)
        
        return parameters
    
    def _extract_request_body(self, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract request body schema."""
        if 'body' in schema:
            return {
                'content_type': 'application/json',
                'schema': schema['body'],
                'example': self._generate_example_body(schema['body'])
            }
        return None
    
    def _extract_responses(self, endpoint_spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract response specifications."""
        responses = {}
        
        # Default success response
        responses['200'] = {
            'description': 'Successful response',
            'content_type': 'application/json',
            'example': {'status': 'success', 'data': {}}
        }
        
        # Common error responses
        responses['400'] = {
            'description': 'Bad request - Invalid parameters',
            'content_type': 'application/json',
            'example': {'error': 'Invalid parameters', 'details': {}}
        }
        
        responses['401'] = {
            'description': 'Unauthorized - Authentication required',
            'content_type': 'application/json',
            'example': {'error': 'Authentication required'}
        }
        
        responses['500'] = {
            'description': 'Internal server error',
            'content_type': 'application/json',
            'example': {'error': 'Internal server error'}
        }
        
        return responses
    
    def _generate_endpoint_examples(self, endpoint: APIEndpoint) -> List[Dict[str, Any]]:
        """Generate examples for endpoint."""
        examples = []
        
        # Basic example
        example = {
            'name': 'Basic Example',
            'description': f'Basic usage of {endpoint.method} {endpoint.path}',
            'request': {
                'method': endpoint.method,
                'url': endpoint.path,
                'headers': {'Content-Type': 'application/json'}
            },
            'response': {
                'status': 200,
                'body': {'status': 'success'}
            }
        }
        
        # Add parameters if available
        if endpoint.parameters:
            example['request']['parameters'] = {}
            for param in endpoint.parameters:
                if param.get('example'):
                    example['request']['parameters'][param['name']] = param['example']
        
        # Add request body if available
        if endpoint.request_body and endpoint.request_body.get('example'):
            example['request']['body'] = endpoint.request_body['example']
        
        examples.append(example)
        
        return examples
    
    def _generate_example_value(self, param_schema: Dict[str, Any]) -> Any:
        """Generate example value for parameter."""
        param_type = param_schema.get('type', 'string')
        
        if 'enum' in param_schema:
            return param_schema['enum'][0]
        elif param_type == 'string':
            return 'example_string'
        elif param_type == 'integer':
            minimum = param_schema.get('minimum', 1)
            maximum = param_schema.get('maximum', 100)
            return min(maximum, max(minimum, 42))
        elif param_type == 'number':
            minimum = param_schema.get('minimum', 1.0)
            maximum = param_schema.get('maximum', 100.0)
            return min(maximum, max(minimum, 42.5))
        elif param_type == 'boolean':
            return True
        elif param_type == 'array':
            return ['example_item']
        else:
            return 'example_value'
    
    def _generate_example_body(self, body_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate example request body."""
        example = {}
        
        if 'properties' in body_schema:
            for prop_name, prop_schema in body_schema['properties'].items():
                example[prop_name] = self._generate_example_value(prop_schema)
        
        return example
    
    def _generate_api_reference_sections(self, doc: Documentation) -> List[DocumentationSection]:
        """Generate API reference sections."""
        sections = []
        
        # Introduction
        sections.append(DocumentationSection(
            title="Introduction",
            content=f"This document provides a comprehensive reference for the {doc.api_name} API.",
            section_type="introduction",
            order=1
        ))
        
        # Authentication
        sections.append(DocumentationSection(
            title="Authentication",
            content="Information about API authentication and authorization.",
            section_type="authentication",
            order=2
        ))
        
        # Base URL
        sections.append(DocumentationSection(
            title="Base URL",
            content=f"All API requests should be made to: `{doc.base_url}`",
            section_type="base_url",
            order=3
        ))
        
        # Endpoints
        endpoints_section = DocumentationSection(
            title="API Endpoints",
            content="Detailed information about all available API endpoints.",
            section_type="endpoints",
            order=4
        )
        
        # Add subsection for each endpoint
        for i, endpoint in enumerate(doc.endpoints):
            endpoint_content = self._generate_endpoint_documentation(endpoint)
            endpoint_section = DocumentationSection(
                title=f"{endpoint.method} {endpoint.path}",
                content=endpoint_content,
                section_type="endpoint",
                order=i + 1
            )
            endpoints_section.subsections.append(endpoint_section)
        
        sections.append(endpoints_section)
        
        # Error Codes
        sections.append(DocumentationSection(
            title="Error Codes",
            content="Common HTTP status codes and error responses.",
            section_type="error_codes",
            order=5
        ))
        
        return sections
    
    def _generate_user_guide_sections(self, doc: Documentation) -> List[DocumentationSection]:
        """Generate user guide sections."""
        sections = []
        
        # Getting Started
        sections.append(DocumentationSection(
            title="Getting Started",
            content=f"Welcome to the {doc.api_name} user guide. This guide will help you get started with using the API.",
            section_type="getting_started",
            order=1
        ))
        
        # Quick Start
        sections.append(DocumentationSection(
            title="Quick Start",
            content="Follow these steps to make your first API call.",
            section_type="quick_start",
            order=2
        ))
        
        # Common Use Cases
        sections.append(DocumentationSection(
            title="Common Use Cases",
            content="Examples of common scenarios and how to implement them.",
            section_type="use_cases",
            order=3
        ))
        
        # Best Practices
        sections.append(DocumentationSection(
            title="Best Practices",
            content="Recommended practices for using the API effectively.",
            section_type="best_practices",
            order=4
        ))
        
        # Troubleshooting
        sections.append(DocumentationSection(
            title="Troubleshooting",
            content="Common issues and their solutions.",
            section_type="troubleshooting",
            order=5
        ))
        
        return sections
    
    def _generate_quick_start_sections(self, doc: Documentation) -> List[DocumentationSection]:
        """Generate quick start sections."""
        sections = []
        
        # Prerequisites
        sections.append(DocumentationSection(
            title="Prerequisites",
            content="What you need before getting started.",
            section_type="prerequisites",
            order=1
        ))
        
        # Installation
        sections.append(DocumentationSection(
            title="Installation",
            content="How to install and set up the API client.",
            section_type="installation",
            order=2
        ))
        
        # First API Call
        sections.append(DocumentationSection(
            title="Your First API Call",
            content="Step-by-step guide to making your first API call.",
            section_type="first_call",
            order=3
        ))
        
        # Next Steps
        sections.append(DocumentationSection(
            title="Next Steps",
            content="Where to go from here.",
            section_type="next_steps",
            order=4
        ))
        
        return sections
    
    def _generate_readme_sections(self, doc: Documentation) -> List[DocumentationSection]:
        """Generate README sections."""
        sections = []
        
        # Description
        sections.append(DocumentationSection(
            title="Description",
            content=f"{doc.api_name} - {doc.description}",
            section_type="description",
            order=1
        ))
        
        # Features
        sections.append(DocumentationSection(
            title="Features",
            content="Key features and capabilities.",
            section_type="features",
            order=2
        ))
        
        # Installation
        sections.append(DocumentationSection(
            title="Installation",
            content="How to install and set up.",
            section_type="installation",
            order=3
        ))
        
        # Usage
        sections.append(DocumentationSection(
            title="Usage",
            content="Basic usage examples.",
            section_type="usage",
            order=4
        ))
        
        # Contributing
        sections.append(DocumentationSection(
            title="Contributing",
            content="How to contribute to the project.",
            section_type="contributing",
            order=5
        ))
        
        # License
        sections.append(DocumentationSection(
            title="License",
            content="License information.",
            section_type="license",
            order=6
        ))
        
        return sections
    
    def _generate_generic_sections(self, doc: Documentation) -> List[DocumentationSection]:
        """Generate generic documentation sections."""
        return self._generate_api_reference_sections(doc)
    
    def _generate_endpoint_documentation(self, endpoint: APIEndpoint) -> str:
        """Generate documentation content for an endpoint."""
        content = []
        
        # Description
        if endpoint.description:
            content.append(endpoint.description)
        else:
            content.append(f"Endpoint for {endpoint.method} {endpoint.path}")
        
        content.append("")
        
        # Method and path
        content.append(f"**Method:** `{endpoint.method}`")
        content.append(f"**Path:** `{endpoint.path}`")
        content.append("")
        
        # Parameters
        if endpoint.parameters:
            content.append("### Parameters")
            content.append("")
            content.append("| Name | Type | Required | Description | Example |")
            content.append("|------|------|----------|-------------|---------|")
            
            for param in endpoint.parameters:
                required = "Yes" if param.get('required', False) else "No"
                example = param.get('example', '')
                description = param.get('description', '')
                
                content.append(f"| {param['name']} | {param['type']} | {required} | {description} | `{example}` |")
            
            content.append("")
        
        # Request body
        if endpoint.request_body:
            content.append("### Request Body")
            content.append("")
            content.append(f"**Content-Type:** `{endpoint.request_body.get('content_type', 'application/json')}`")
            content.append("")
            
            if endpoint.request_body.get('example'):
                content.append("**Example:**")
                content.append("```json")
                content.append(json.dumps(endpoint.request_body['example'], indent=2))
                content.append("```")
                content.append("")
        
        # Responses
        if endpoint.responses:
            content.append("### Responses")
            content.append("")
            
            for status_code, response in endpoint.responses.items():
                content.append(f"#### {status_code} - {response.get('description', 'Response')}")
                content.append("")
                
                if response.get('example'):
                    content.append("**Example:**")
                    content.append("```json")
                    content.append(json.dumps(response['example'], indent=2))
                    content.append("```")
                    content.append("")
        
        # Examples
        if endpoint.examples:
            content.append("### Examples")
            content.append("")
            
            for example in endpoint.examples:
                content.append(f"#### {example.get('name', 'Example')}")
                content.append("")
                
                if example.get('description'):
                    content.append(example['description'])
                    content.append("")
                
                # Request example
                if 'request' in example:
                    content.append("**Request:**")
                    content.append("```bash")
                    
                    request = example['request']
                    curl_cmd = f"curl -X {request.get('method', 'GET')}"
                    
                    if request.get('headers'):
                        for header, value in request['headers'].items():
                            curl_cmd += f" -H '{header}: {value}'"
                    
                    if request.get('body'):
                        curl_cmd += f" -d '{json.dumps(request['body'])}'"
                    
                    curl_cmd += f" {request.get('url', endpoint.path)}"
                    
                    content.append(curl_cmd)
                    content.append("```")
                    content.append("")
                
                # Response example
                if 'response' in example:
                    content.append("**Response:**")
                    content.append("```json")
                    content.append(json.dumps(example['response'].get('body', {}), indent=2))
                    content.append("```")
                    content.append("")
        
        return "\n".join(content)
    
    def _enhance_documentation_with_llm(self, doc: Documentation, 
                                       doc_type: DocumentationType) -> Documentation:
        """Enhance documentation using LLM capabilities."""
        if not self.llm_available:
            return doc
        
        try:
            logger.info("🧠 Enhancing documentation with LLM")
            
            # Enhance endpoint descriptions
            for endpoint in doc.endpoints:
                if not endpoint.description or len(endpoint.description) < 50:
                    enhanced_description = self._generate_endpoint_description(endpoint)
                    if enhanced_description:
                        endpoint.generated_description = enhanced_description
                
                # Generate usage patterns
                endpoint.usage_patterns = self._generate_usage_patterns(endpoint)
                
                # Generate best practices
                endpoint.best_practices = self._generate_endpoint_best_practices(endpoint)
                
                # Generate common errors
                endpoint.common_errors = self._generate_common_errors(endpoint)
            
            # Enhance section content
            for section in doc.sections:
                if section.section_type in ['introduction', 'getting_started', 'best_practices']:
                    enhanced_content = self._enhance_section_content(section, doc)
                    if enhanced_content:
                        section.content = enhanced_content
                        section.generated_by = "llm_enhanced"
            
            logger.info("✅ Documentation enhanced with LLM")
            
        except Exception as e:
            logger.error(f"❌ Failed to enhance documentation with LLM: {e}")
        
        return doc
    
    def _generate_endpoint_description(self, endpoint: APIEndpoint) -> str:
        """Generate intelligent endpoint description."""
        try:
            prompt = f"""
Generate a clear, concise description for this API endpoint:

**Endpoint:** {endpoint.method} {endpoint.path}
**Name:** {endpoint.name}
**Current Description:** {endpoint.description or 'None'}
**Parameters:** {len(endpoint.parameters)} parameters
**Has Request Body:** {endpoint.request_body is not None}

Generate a 1-2 sentence description that explains:
1. What this endpoint does
2. When you would use it

Make it user-friendly and avoid technical jargon.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a technical writer specializing in API documentation. Write clear, concise descriptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate endpoint description: {e}")
            return ""
    
    def _generate_usage_patterns(self, endpoint: APIEndpoint) -> List[str]:
        """Generate common usage patterns for endpoint."""
        try:
            prompt = f"""
Analyze this API endpoint and suggest 3-5 common usage patterns:

**Endpoint:** {endpoint.method} {endpoint.path}
**Parameters:** {[p['name'] for p in endpoint.parameters]}
**Method:** {endpoint.method}

Suggest realistic scenarios where this endpoint would be used.
Provide as a simple list, one pattern per line.

Example format:
- Retrieving user profile information
- Updating account settings
- Searching for products by category
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API usage expert. Suggest practical usage patterns."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=300
            )
            
            patterns = []
            lines = response.choices[0].message.content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    pattern = line[1:].strip()
                    if pattern:
                        patterns.append(pattern)
            
            return patterns[:5]
            
        except Exception as e:
            logger.error(f"Failed to generate usage patterns: {e}")
            return []
    
    def _generate_endpoint_best_practices(self, endpoint: APIEndpoint) -> List[str]:
        """Generate best practices for endpoint usage."""
        try:
            prompt = f"""
Suggest 3-5 best practices for using this API endpoint:

**Endpoint:** {endpoint.method} {endpoint.path}
**Parameters:** {[p['name'] for p in endpoint.parameters]}
**Method:** {endpoint.method}

Focus on:
- Performance optimization
- Error handling
- Security considerations
- Data validation

Provide as a simple list, one practice per line.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API best practices expert. Provide actionable advice."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            practices = []
            lines = response.choices[0].message.content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    practice = line[1:].strip()
                    if practice:
                        practices.append(practice)
            
            return practices[:5]
            
        except Exception as e:
            logger.error(f"Failed to generate best practices: {e}")
            return []
    
    def _generate_common_errors(self, endpoint: APIEndpoint) -> List[Dict[str, str]]:
        """Generate common errors and solutions."""
        try:
            prompt = f"""
Identify 3-4 common errors users might encounter with this endpoint:

**Endpoint:** {endpoint.method} {endpoint.path}
**Parameters:** {[p['name'] for p in endpoint.parameters]}
**Required Parameters:** {[p['name'] for p in endpoint.parameters if p.get('required')]}

For each error, provide:
1. Error description
2. Likely cause
3. Solution

Format as JSON array:
[
  {
    "error": "Error description",
    "cause": "Why this happens",
    "solution": "How to fix it"
  }
]
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API troubleshooting expert. Identify common issues and solutions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                errors = json.loads(json_match.group(1))
            else:
                errors = json.loads(response_text)
            
            return errors if isinstance(errors, list) else []
            
        except Exception as e:
            logger.error(f"Failed to generate common errors: {e}")
            return []
    
    def _enhance_section_content(self, section: DocumentationSection, 
                               doc: Documentation) -> str:
        """Enhance section content with LLM."""
        try:
            prompt = f"""
Enhance this documentation section for the {doc.api_name} API:

**Section:** {section.title}
**Current Content:** {section.content}
**Section Type:** {section.section_type}
**API Name:** {doc.api_name}
**Number of Endpoints:** {len(doc.endpoints)}

Rewrite the content to be:
1. More informative and helpful
2. User-friendly and clear
3. Appropriate for the section type
4. 2-3 paragraphs long

Don't include markdown headers (##, ###) as they will be added automatically.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a technical writer specializing in API documentation. Write clear, helpful content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to enhance section content: {e}")
            return section.content
    
    def export_documentation(self, doc: Documentation, output_path: str, 
                           format: str = "markdown") -> bool:
        """Export documentation to file."""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "markdown":
                content = self._generate_markdown(doc)
            elif format.lower() == "html":
                content = self._generate_html(doc)
            elif format.lower() == "json":
                content = self._generate_json(doc)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"📤 Documentation exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to export documentation: {e}")
            return False
    
    def _generate_markdown(self, doc: Documentation) -> str:
        """Generate markdown documentation."""
        content = []
        
        # Title
        content.append(f"# {doc.title}")
        content.append("")
        content.append(doc.description)
        content.append("")
        
        # Table of contents
        content.append("## Table of Contents")
        content.append("")
        for section in doc.sections:
            content.append(f"- [{section.title}](#{section.title.lower().replace(' ', '-')})")
            for subsection in section.subsections:
                content.append(f"  - [{subsection.title}](#{subsection.title.lower().replace(' ', '-').replace('/', '').replace('{', '').replace('}', '')})")
        content.append("")
        
        # Sections
        for section in doc.sections:
            content.append(f"## {section.title}")
            content.append("")
            content.append(section.content)
            content.append("")
            
            # Subsections
            for subsection in section.subsections:
                content.append(f"### {subsection.title}")
                content.append("")
                content.append(subsection.content)
                content.append("")
        
        return "\n".join(content)
    
    def _generate_html(self, doc: Documentation) -> str:
        """Generate HTML documentation."""
        markdown_content = self._generate_markdown(doc)
        html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
        # Wrap in HTML template
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .toc {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""
        
        return html_template
    
    def _generate_json(self, doc: Documentation) -> str:
        """Generate JSON documentation."""
        doc_data = {
            "title": doc.title,
            "description": doc.description,
            "version": doc.version,
            "api_name": doc.api_name,
            "base_url": doc.base_url,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat(),
            "generated_by": doc.generated_by,
            "sections": [],
            "endpoints": []
        }
        
        # Convert sections
        for section in doc.sections:
            section_data = {
                "title": section.title,
                "content": section.content,
                "section_type": section.section_type,
                "order": section.order,
                "generated_by": section.generated_by,
                "confidence_score": section.confidence_score,
                "subsections": []
            }
            
            for subsection in section.subsections:
                subsection_data = {
                    "title": subsection.title,
                    "content": subsection.content,
                    "section_type": subsection.section_type,
                    "order": subsection.order
                }
                section_data["subsections"].append(subsection_data)
            
            doc_data["sections"].append(section_data)
        
        # Convert endpoints
        for endpoint in doc.endpoints:
            endpoint_data = {
                "name": endpoint.name,
                "method": endpoint.method,
                "path": endpoint.path,
                "description": endpoint.description,
                "generated_description": endpoint.generated_description,
                "parameters": endpoint.parameters,
                "request_body": endpoint.request_body,
                "responses": endpoint.responses,
                "examples": endpoint.examples,
                "tags": endpoint.tags,
                "usage_patterns": endpoint.usage_patterns,
                "common_errors": endpoint.common_errors,
                "best_practices": endpoint.best_practices,
                "related_endpoints": endpoint.related_endpoints
            }
            doc_data["endpoints"].append(endpoint_data)
        
        return json.dumps(doc_data, indent=2, default=str)
    
    def _get_api_reference_template(self) -> str:
        """Get API reference template."""
        return """
# {{ doc.title }}

{{ doc.description }}

## Base URL
{{ doc.base_url }}

## Authentication
Information about authentication requirements.

## Endpoints
{% for endpoint in doc.endpoints %}
### {{ endpoint.method }} {{ endpoint.path }}
{{ endpoint.description }}
{% endfor %}
"""
    
    def _get_user_guide_template(self) -> str:
        """Get user guide template."""
        return """
# {{ doc.title }}

Welcome to the {{ doc.api_name }} user guide.

## Getting Started
Steps to get started with the API.

## Common Use Cases
Examples of how to use the API.
"""
    
    def _get_quick_start_template(self) -> str:
        """Get quick start template."""
        return """
# {{ doc.title }}

Get up and running with {{ doc.api_name }} in minutes.

## Prerequisites
What you need before starting.

## Installation
How to install the client.

## Your First API Call
Make your first request.
"""
    
    def _get_readme_template(self) -> str:
        """Get README template."""
        return """
# {{ doc.api_name }}

{{ doc.description }}

## Features
- Feature 1
- Feature 2

## Installation
Installation instructions.

## Usage
Basic usage examples.

## Contributing
How to contribute.

## License
License information.
"""

# Example usage
if __name__ == "__main__":
    # Example API specification
    api_spec = {
        "name": "payment-api",
        "version": "1.0.0",
        "base_url": "https://api.example.com",
        "endpoints": [
            {
                "name": "create_payment",
                "method": "POST",
                "path": "/api/payments",
                "description": "Create a new payment",
                "schema": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number", "minimum": 0.01, "maximum": 10000, "description": "Payment amount"},
                        "currency": {"type": "string", "enum": ["USD", "EUR", "GBP"], "description": "Payment currency"},
                        "description": {"type": "string", "minLength": 1, "maxLength": 255, "description": "Payment description"}
                    },
                    "required": ["amount", "currency"]
                },
                "tags": ["payments"]
            },
            {
                "name": "get_payments",
                "method": "GET",
                "path": "/api/payments",
                "description": "Retrieve payments",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pending", "completed", "failed"], "description": "Payment status filter"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Number of results to return"},
                        "offset": {"type": "integer", "minimum": 0, "description": "Number of results to skip"}
                    }
                },
                "tags": ["payments"]
            }
        ]
    }
    
    # Create documentation generator
    generator = IntelligentDocumentationGenerator({
        "azure_openai": {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "deployment": "gpt-4"
        },
        "documentation": {
            "include_examples": True,
            "include_troubleshooting": True,
            "include_best_practices": True,
            "audience_level": "intermediate",
            "writing_style": "professional",
            "include_code_samples": True
        }
    })
    
    # Generate different types of documentation
    api_ref = generator.generate_documentation(api_spec, DocumentationType.API_REFERENCE, "Payment API")
    user_guide = generator.generate_documentation(api_spec, DocumentationType.USER_GUIDE, "Payment API")
    quick_start = generator.generate_documentation(api_spec, DocumentationType.QUICK_START, "Payment API")
    readme = generator.generate_documentation(api_spec, DocumentationType.README, "Payment API")
    
    # Export documentation
    generator.export_documentation(api_ref, "api_reference.md", "markdown")
    generator.export_documentation(api_ref, "api_reference.html", "html")
    generator.export_documentation(user_guide, "user_guide.md", "markdown")
    generator.export_documentation(quick_start, "quick_start.md", "markdown")
    generator.export_documentation(readme, "README.md", "markdown")
    
    print("✅ Documentation generated successfully!")
    print(f"  - API Reference: {len(api_ref.sections)} sections, {len(api_ref.endpoints)} endpoints")
    print(f"  - User Guide: {len(user_guide.sections)} sections")
    print(f"  - Quick Start: {len(quick_start.sections)} sections")
    print(f"  - README: {len(readme.sections)} sections")