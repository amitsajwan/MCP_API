#!/usr/bin/env python3
"""
Argument validation module for MCP API server.
Provides comprehensive validation for API arguments before they reach endpoints.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, ValidationError, Field
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationResult:
    """Result of argument validation."""
    
    def __init__(self, is_valid: bool, cleaned_args: Dict[str, Any] = None, errors: List[str] = None):
        self.is_valid = is_valid
        self.cleaned_args = cleaned_args or {}
        self.errors = errors or []
    
    def __str__(self):
        if self.is_valid:
            return f"ValidationResult(valid=True, args={len(self.cleaned_args)} items)"
        else:
            return f"ValidationResult(valid=False, errors={self.errors})"

class ArgumentValidator:
    """Validates API arguments against OpenAPI schemas."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_arguments(self, arguments: Dict[str, Any], 
                         tool_schema: Dict[str, Any], method: str = 'GET') -> ValidationResult:
        """Validate arguments against tool schema.
        
        Args:
            arguments: Arguments provided by the LLM
            tool_schema: OpenAPI-derived schema for the tool
            method: HTTP method (GET, POST, etc.)
            
        Returns:
            ValidationResult with validation status and cleaned arguments
        """
        try:
            self.logger.info(f"Validating arguments for {method} request: {arguments}")
            
            # Clean and validate arguments
            cleaned_args = self._clean_arguments(arguments)
            
            # Validate against schema
            validation_errors = self._validate_against_schema(cleaned_args, tool_schema)
            
            if validation_errors:
                return ValidationResult(
                    is_valid=False,
                    errors=validation_errors
                )
            
            return ValidationResult(
                is_valid=True,
                cleaned_args=cleaned_args
            )
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
    
    def _clean_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Clean arguments by removing null/empty values where appropriate."""
        cleaned = {}
        
        for key, value in arguments.items():
            if key == 'body' and isinstance(value, dict):
                # Clean body payload recursively
                cleaned_body = self._clean_payload(value)
                if cleaned_body:  # Only include non-empty body
                    cleaned[key] = cleaned_body
            elif self._is_valid_value(value):
                # Include non-null, non-empty string values
                cleaned[key] = value
        
        return cleaned
    
    def _clean_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Clean payload by removing null/empty values."""
        cleaned = {}
        
        for key, value in payload.items():
            if isinstance(value, dict):
                # Recursively clean nested objects
                cleaned_nested = self._clean_payload(value)
                if cleaned_nested:
                    cleaned[key] = cleaned_nested
            elif isinstance(value, list):
                # Clean list items
                cleaned_list = [item for item in value if self._is_valid_value(item)]
                if cleaned_list:
                    cleaned[key] = cleaned_list
            elif self._is_valid_value(value):
                cleaned[key] = value
        
        return cleaned
    
    def _is_valid_value(self, value: Any) -> bool:
        """Check if a value is valid (not null, not empty string)."""
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        return True
    
    def _validate_against_schema(self, arguments: Dict[str, Any], 
                               schema: Dict[str, Any]) -> List[str]:
        """Validate arguments against OpenAPI schema."""
        errors = []
        
        # Get schema properties
        properties = schema.get('properties', {})
        required_fields = schema.get('required', [])
        
        # Check for missing required fields
        for field in required_fields:
            if field not in arguments:
                errors.append(f"Missing required field: {field}")
        
        # Validate each argument
        for arg_name, arg_value in arguments.items():
            if arg_name in properties:
                field_errors = self._validate_field(arg_name, arg_value, properties[arg_name])
                errors.extend(field_errors)
            elif arg_name == 'body':
                # Special handling for request body
                body_errors = self._validate_request_body(arg_value, schema)
                errors.extend(body_errors)
        
        return errors
    
    def _validate_field(self, field_name: str, value: Any, 
                       field_schema: Dict[str, Any]) -> List[str]:
        """Validate a single field against its schema."""
        errors = []
        
        # Type validation
        expected_type = field_schema.get('type')
        if expected_type and not self._check_type(value, expected_type):
            errors.append(f"Field '{field_name}' should be {expected_type}, got {type(value).__name__}")
        
        # Enum validation
        enum_values = field_schema.get('enum')
        if enum_values and value not in enum_values:
            errors.append(f"Field '{field_name}' must be one of {enum_values}, got '{value}'")
        
        # String constraints
        if isinstance(value, str):
            min_length = field_schema.get('minLength')
            max_length = field_schema.get('maxLength')
            pattern = field_schema.get('pattern')
            
            if min_length and len(value) < min_length:
                errors.append(f"Field '{field_name}' must be at least {min_length} characters")
            if max_length and len(value) > max_length:
                errors.append(f"Field '{field_name}' must be at most {max_length} characters")
            if pattern:
                import re
                if not re.match(pattern, value):
                    errors.append(f"Field '{field_name}' does not match required pattern")
        
        # Numeric constraints
        if isinstance(value, (int, float)):
            minimum = field_schema.get('minimum')
            maximum = field_schema.get('maximum')
            
            if minimum is not None and value < minimum:
                errors.append(f"Field '{field_name}' must be at least {minimum}")
            if maximum is not None and value > maximum:
                errors.append(f"Field '{field_name}' must be at most {maximum}")
        
        return errors
    
    def _validate_request_body(self, body: Dict[str, Any], 
                             schema: Dict[str, Any]) -> List[str]:
        """Validate request body against schema."""
        errors = []
        
        # Look for body schema in the tool schema
        body_schema = None
        if 'body' in schema.get('properties', {}):
            body_schema = schema['properties']['body']
        
        if body_schema and 'properties' in body_schema:
            body_properties = body_schema['properties']
            body_required = body_schema.get('required', [])
            
            # Check required fields in body
            for field in body_required:
                if field not in body:
                    errors.append(f"Missing required field in request body: {field}")
            
            # Validate body fields
            for field_name, field_value in body.items():
                if field_name in body_properties:
                    field_errors = self._validate_field(
                        f"body.{field_name}", field_value, body_properties[field_name]
                    )
                    errors.extend(field_errors)
        
        return errors
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected OpenAPI type."""
        type_mapping = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True  # Unknown type, assume valid

class PaymentRequestValidator(BaseModel):
    """Pydantic model for payment request validation."""
    
    amount: float = Field(..., gt=0, description="Payment amount must be positive")
    currency: str = Field(..., min_length=3, max_length=3, description="3-letter currency code")
    recipient: str = Field(..., min_length=1, description="Recipient name cannot be empty")
    requester_id: str = Field(..., min_length=1, description="Requester ID cannot be empty")
    description: Optional[str] = Field(None, max_length=500, description="Optional payment description")
    
    class Config:
        str_strip_whitespace = True  # Automatically strip whitespace
        validate_assignment = True   # Validate on assignment

def create_pydantic_validator(schema: Dict[str, Any]) -> Optional[BaseModel]:
    """Create a Pydantic model from OpenAPI schema for validation."""
    try:
        # This is a simplified example - in practice, you'd need more complex
        # schema-to-Pydantic conversion logic
        if 'PaymentRequest' in str(schema):
            return PaymentRequestValidator
        return None
    except Exception as e:
        logger.error(f"Failed to create Pydantic validator: {e}")
        return None

# Example usage and testing
if __name__ == "__main__":
    validator = ArgumentValidator()
    
    # Test payment validation
    test_schema = {
        "properties": {
            "body": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "minimum": 0.01},
                    "currency": {"type": "string", "minLength": 3, "maxLength": 3},
                    "recipient": {"type": "string", "minLength": 1},
                    "requester_id": {"type": "string", "minLength": 1}
                },
                "required": ["amount", "currency", "recipient", "requester_id"]
            }
        },
        "required": ["body"]
    }
    
    # Test cases
    test_cases = [
        {
            "name": "Valid payment",
            "args": {
                "body": {
                    "amount": 100.50,
                    "currency": "USD",
                    "recipient": "John Doe",
                    "requester_id": "user123"
                }
            }
        },
        {
            "name": "Invalid payment - empty recipient",
            "args": {
                "body": {
                    "amount": 100.50,
                    "currency": "USD",
                    "recipient": "",
                    "requester_id": "user123"
                }
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        result = validator.validate_arguments("createPayment", test_case['args'], test_schema)
        print(f"Result: {result}")
        if not result.is_valid:
            for error in result.errors:
                print(f"  Error: {error}")