#!/usr/bin/env python3
"""
Enhanced Schema Processor - POC Implementation
Handles complex OpenAPI schema features:
- External $ref resolution
- allOf/oneOf/anyOf composition
- Recursive schema validation
- Custom format extensions
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import aiohttp
import copy

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of schema validation."""
    valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    cleaned_data: Any = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

@dataclass
class SchemaContext:
    """Context for schema resolution and validation."""
    base_url: str = ""
    visited_refs: Set[str] = None
    max_depth: int = 10
    current_depth: int = 0
    
    def __post_init__(self):
        if self.visited_refs is None:
            self.visited_refs = set()

class EnhancedSchemaProcessor:
    """Advanced OpenAPI schema processor with full feature support."""
    
    def __init__(self, cache_size: int = 100):
        self.schema_cache: Dict[str, Dict[str, Any]] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache_size = cache_size
        
        # Custom format validators
        self.format_validators = {
            'email': self._validate_email,
            'uri': self._validate_uri,
            'date': self._validate_date,
            'date-time': self._validate_datetime,
            'uuid': self._validate_uuid,
            'financial-account': self._validate_financial_account,
            'currency-code': self._validate_currency_code,
            'payment-reference': self._validate_payment_reference
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def resolve_schema(self, schema: Dict[str, Any], context: SchemaContext = None) -> Dict[str, Any]:
        """
        Resolve a schema with all its references and compositions.
        
        Args:
            schema: The schema to resolve
            context: Resolution context
            
        Returns:
            Fully resolved schema
        """
        if context is None:
            context = SchemaContext()
        
        if context.current_depth > context.max_depth:
            logger.warning(f"Max recursion depth {context.max_depth} exceeded")
            return schema
        
        # Handle $ref resolution
        if '$ref' in schema:
            return await self._resolve_ref(schema['$ref'], context)
        
        # Handle composition keywords
        if any(key in schema for key in ['allOf', 'oneOf', 'anyOf']):
            return await self._resolve_composition(schema, context)
        
        # Recursively resolve nested schemas
        resolved = copy.deepcopy(schema)
        
        # Handle properties
        if 'properties' in resolved:
            new_context = SchemaContext(
                base_url=context.base_url,
                visited_refs=context.visited_refs.copy(),
                max_depth=context.max_depth,
                current_depth=context.current_depth + 1
            )
            for prop_name, prop_schema in resolved['properties'].items():
                resolved['properties'][prop_name] = await self.resolve_schema(prop_schema, new_context)
        
        # Handle array items
        if 'items' in resolved:
            new_context = SchemaContext(
                base_url=context.base_url,
                visited_refs=context.visited_refs.copy(),
                max_depth=context.max_depth,
                current_depth=context.current_depth + 1
            )
            resolved['items'] = await self.resolve_schema(resolved['items'], new_context)
        
        # Handle additionalProperties
        if isinstance(resolved.get('additionalProperties'), dict):
            new_context = SchemaContext(
                base_url=context.base_url,
                visited_refs=context.visited_refs.copy(),
                max_depth=context.max_depth,
                current_depth=context.current_depth + 1
            )
            resolved['additionalProperties'] = await self.resolve_schema(
                resolved['additionalProperties'], new_context
            )
        
        return resolved
    
    async def _resolve_ref(self, ref: str, context: SchemaContext) -> Dict[str, Any]:
        """Resolve a $ref, handling both internal and external references."""
        
        # Prevent infinite recursion
        if ref in context.visited_refs:
            logger.warning(f"Circular reference detected: {ref}")
            return {"type": "object", "description": f"Circular reference to {ref}"}
        
        context.visited_refs.add(ref)
        
        try:
            # Internal reference
            if ref.startswith('#/'):
                return await self._resolve_internal_ref(ref, context)
            
            # External reference
            elif ref.startswith(('http://', 'https://')):
                return await self._resolve_external_ref(ref, context)
            
            # Relative reference
            else:
                full_url = urljoin(context.base_url, ref)
                return await self._resolve_external_ref(full_url, context)
                
        except Exception as e:
            logger.error(f"Failed to resolve $ref {ref}: {e}")
            return {"type": "object", "description": f"Failed to resolve reference: {ref}"}
        
        finally:
            context.visited_refs.discard(ref)
    
    async def _resolve_internal_ref(self, ref: str, context: SchemaContext) -> Dict[str, Any]:
        """Resolve internal reference like #/components/schemas/User."""
        # This would need access to the root document
        # For POC, return a placeholder
        logger.info(f"Resolving internal ref: {ref}")
        return {
            "type": "object",
            "description": f"Internal reference: {ref}",
            "x-ref-resolved": ref
        }
    
    async def _resolve_external_ref(self, url: str, context: SchemaContext) -> Dict[str, Any]:
        """Resolve external reference by fetching the schema."""
        
        # Check cache first
        if url in self.schema_cache:
            logger.debug(f"Using cached schema for {url}")
            cached_schema = self.schema_cache[url]
        else:
            # Fetch external schema
            logger.info(f"Fetching external schema: {url}")
            cached_schema = await self._fetch_external_schema(url)
            
            # Cache it (with size limit)
            if len(self.schema_cache) >= self.cache_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self.schema_cache))
                del self.schema_cache[oldest_key]
            
            self.schema_cache[url] = cached_schema
        
        # Handle fragment identifier (e.g., #/definitions/User)
        parsed_url = urlparse(url)
        if parsed_url.fragment:
            return self._extract_fragment(cached_schema, parsed_url.fragment)
        
        return cached_schema
    
    async def _fetch_external_schema(self, url: str) -> Dict[str, Any]:
        """Fetch schema from external URL."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                content_type = response.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    return await response.json()
                elif 'application/yaml' in content_type or url.endswith(('.yaml', '.yml')):
                    import yaml
                    text = await response.text()
                    return yaml.safe_load(text)
                else:
                    # Try JSON first, then YAML
                    text = await response.text()
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        import yaml
                        return yaml.safe_load(text)
                        
        except Exception as e:
            logger.error(f"Failed to fetch schema from {url}: {e}")
            raise
    
    def _extract_fragment(self, schema: Dict[str, Any], fragment: str) -> Dict[str, Any]:
        """Extract a fragment from a schema document."""
        if fragment.startswith('#/'):
            fragment = fragment[2:]
        
        parts = fragment.split('/')
        current = schema
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise ValueError(f"Fragment path not found: {fragment}")
        
        return current if isinstance(current, dict) else {"type": "object"}
    
    async def _resolve_composition(self, schema: Dict[str, Any], context: SchemaContext) -> Dict[str, Any]:
        """Resolve schema composition keywords: allOf, oneOf, anyOf."""
        
        if 'allOf' in schema:
            return await self._resolve_all_of(schema, context)
        elif 'oneOf' in schema:
            return await self._resolve_one_of(schema, context)
        elif 'anyOf' in schema:
            return await self._resolve_any_of(schema, context)
        
        return schema
    
    async def _resolve_all_of(self, schema: Dict[str, Any], context: SchemaContext) -> Dict[str, Any]:
        """Resolve allOf by merging all schemas."""
        result = {}
        required_fields = set()
        properties = {}
        
        for sub_schema in schema['allOf']:
            resolved_sub = await self.resolve_schema(sub_schema, context)
            
            # Merge properties
            if 'properties' in resolved_sub:
                properties.update(resolved_sub['properties'])
            
            # Collect required fields
            if 'required' in resolved_sub:
                required_fields.update(resolved_sub['required'])
            
            # Merge other properties (type, description, etc.)
            for key, value in resolved_sub.items():
                if key not in ['properties', 'required']:
                    if key in result:
                        # Handle conflicts - for POC, take the last value
                        logger.debug(f"Conflict in allOf for key {key}, using latest value")
                    result[key] = value
        
        # Add merged properties and required fields
        if properties:
            result['properties'] = properties
        if required_fields:
            result['required'] = list(required_fields)
        
        # Ensure we have a type
        if 'type' not in result:
            result['type'] = 'object'
        
        return result
    
    async def _resolve_one_of(self, schema: Dict[str, Any], context: SchemaContext) -> Dict[str, Any]:
        """Resolve oneOf by creating a union type representation."""
        resolved_options = []
        
        for sub_schema in schema['oneOf']:
            resolved_sub = await self.resolve_schema(sub_schema, context)
            resolved_options.append(resolved_sub)
        
        # For POC, create a combined schema with all possible properties
        # In a real implementation, you might want to keep the union structure
        result = {
            'type': 'object',
            'description': f"One of {len(resolved_options)} possible schemas",
            'x-oneOf-options': resolved_options,
            'properties': {},
            'required': []
        }
        
        # Collect all possible properties
        for option in resolved_options:
            if 'properties' in option:
                result['properties'].update(option['properties'])
        
        return result
    
    async def _resolve_any_of(self, schema: Dict[str, Any], context: SchemaContext) -> Dict[str, Any]:
        """Resolve anyOf by creating a flexible schema."""
        resolved_options = []
        
        for sub_schema in schema['anyOf']:
            resolved_sub = await self.resolve_schema(sub_schema, context)
            resolved_options.append(resolved_sub)
        
        # Similar to oneOf but more permissive
        result = {
            'type': 'object',
            'description': f"Any of {len(resolved_options)} possible schemas",
            'x-anyOf-options': resolved_options,
            'properties': {},
            'required': []
        }
        
        # Collect all possible properties
        for option in resolved_options:
            if 'properties' in option:
                result['properties'].update(option['properties'])
        
        return result
    
    async def validate_data(self, data: Any, schema: Dict[str, Any], context: SchemaContext = None) -> ValidationResult:
        """
        Validate data against a schema with full validation support.
        
        Args:
            data: Data to validate
            schema: Schema to validate against
            context: Validation context
            
        Returns:
            ValidationResult with validation outcome
        """
        if context is None:
            context = SchemaContext()
        
        errors = []
        warnings = []
        cleaned_data = data
        
        try:
            # First resolve the schema
            resolved_schema = await self.resolve_schema(schema, context)
            
            # Validate type
            schema_type = resolved_schema.get('type')
            if schema_type:
                type_valid, type_error = self._validate_type(data, schema_type)
                if not type_valid:
                    errors.append(type_error)
                    return ValidationResult(valid=False, errors=errors)
            
            # Validate format if specified
            format_name = resolved_schema.get('format')
            if format_name and format_name in self.format_validators:
                format_valid, format_error = self.format_validators[format_name](data)
                if not format_valid:
                    errors.append(format_error)
            
            # Validate object properties
            if schema_type == 'object' and isinstance(data, dict):
                properties = resolved_schema.get('properties', {})
                required = resolved_schema.get('required', [])
                
                # Check required fields
                for req_field in required:
                    if req_field not in data:
                        errors.append(f"Required field '{req_field}' is missing")
                
                # Validate each property
                for prop_name, prop_value in data.items():
                    if prop_name in properties:
                        prop_result = await self.validate_data(prop_value, properties[prop_name], context)
                        if not prop_result.valid:
                            errors.extend([f"{prop_name}.{err}" for err in prop_result.errors])
                        warnings.extend([f"{prop_name}.{warn}" for warn in prop_result.warnings])
            
            # Validate array items
            elif schema_type == 'array' and isinstance(data, list):
                items_schema = resolved_schema.get('items')
                if items_schema:
                    for i, item in enumerate(data):
                        item_result = await self.validate_data(item, items_schema, context)
                        if not item_result.valid:
                            errors.extend([f"[{i}].{err}" for err in item_result.errors])
                        warnings.extend([f"[{i}].{warn}" for warn in item_result.warnings])
            
            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                cleaned_data=cleaned_data
            )
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return ValidationResult(valid=False, errors=[f"Validation exception: {str(e)}"])
    
    def _validate_type(self, data: Any, expected_type: str) -> tuple[bool, str]:
        """Validate data type."""
        type_map = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type and not isinstance(data, expected_python_type):
            return False, f"Expected {expected_type}, got {type(data).__name__}"
        
        return True, ""
    
    # Custom format validators
    def _validate_email(self, value: str) -> tuple[bool, str]:
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, value):
            return True, ""
        return False, f"Invalid email format: {value}"
    
    def _validate_uri(self, value: str) -> tuple[bool, str]:
        """Validate URI format."""
        from urllib.parse import urlparse
        try:
            result = urlparse(value)
            if result.scheme and result.netloc:
                return True, ""
            return False, f"Invalid URI format: {value}"
        except:
            return False, f"Invalid URI format: {value}"
    
    def _validate_date(self, value: str) -> tuple[bool, str]:
        """Validate date format (YYYY-MM-DD)."""
        import re
        from datetime import datetime
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if re.match(date_pattern, value):
            try:
                datetime.strptime(value, '%Y-%m-%d')
                return True, ""
            except ValueError:
                pass
        return False, f"Invalid date format: {value} (expected YYYY-MM-DD)"
    
    def _validate_datetime(self, value: str) -> tuple[bool, str]:
        """Validate datetime format (ISO 8601)."""
        from datetime import datetime
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return True, ""
        except ValueError:
            return False, f"Invalid datetime format: {value} (expected ISO 8601)"
    
    def _validate_uuid(self, value: str) -> tuple[bool, str]:
        """Validate UUID format."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, value.lower()):
            return True, ""
        return False, f"Invalid UUID format: {value}"
    
    # Financial domain-specific validators
    def _validate_financial_account(self, value: str) -> tuple[bool, str]:
        """Validate financial account number format."""
        import re
        # Simple pattern for demo - real implementation would be more sophisticated
        account_pattern = r'^[A-Z0-9]{8,20}$'
        if re.match(account_pattern, value):
            return True, ""
        return False, f"Invalid financial account format: {value}"
    
    def _validate_currency_code(self, value: str) -> tuple[bool, str]:
        """Validate ISO 4217 currency code."""
        # Common currency codes for demo
        valid_codes = {'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY'}
        if value.upper() in valid_codes:
            return True, ""
        return False, f"Invalid currency code: {value}"
    
    def _validate_payment_reference(self, value: str) -> tuple[bool, str]:
        """Validate payment reference format."""
        import re
        # Payment reference pattern for demo
        ref_pattern = r'^PAY-[0-9]{4}-[A-Z0-9]{6}$'
        if re.match(ref_pattern, value):
            return True, ""
        return False, f"Invalid payment reference format: {value} (expected PAY-YYYY-XXXXXX)"


# Usage example and test
async def main():
    """Test the enhanced schema processor."""
    
    # Example complex schema with allOf
    complex_schema = {
        "allOf": [
            {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "created_at": {"type": "string", "format": "date-time"}
                },
                "required": ["id"]
            },
            {
                "type": "object", 
                "properties": {
                    "amount": {"type": "number", "minimum": 0},
                    "currency": {"type": "string", "format": "currency-code"},
                    "reference": {"type": "string", "format": "payment-reference"}
                },
                "required": ["amount", "currency"]
            }
        ]
    }
    
    # Test data
    test_data = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "created_at": "2024-01-15T10:30:00Z",
        "amount": 1500.00,
        "currency": "USD",
        "reference": "PAY-2024-ABC123"
    }
    
    async with EnhancedSchemaProcessor() as processor:
        print("🔧 Testing Enhanced Schema Processor")
        print("=" * 50)
        
        # Resolve the complex schema
        print("📋 Resolving complex schema...")
        resolved = await processor.resolve_schema(complex_schema)
        print(f"Resolved schema: {json.dumps(resolved, indent=2)}")
        
        # Validate the test data
        print("\n✅ Validating test data...")
        result = await processor.validate_data(test_data, complex_schema)
        
        print(f"Validation result: {result.valid}")
        if result.errors:
            print(f"Errors: {result.errors}")
        if result.warnings:
            print(f"Warnings: {result.warnings}")
        
        print("\n🎯 Enhanced Schema Processor POC Complete!")

if __name__ == "__main__":
    asyncio.run(main())
