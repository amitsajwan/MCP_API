#!/usr/bin/env python3
"""
Intelligent Argument Validator with Azure OpenAI Integration
This version uses LLM capabilities to provide smart validation,
error messages, and argument suggestions.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, ValidationError, Field
from enum import Enum
from openai import AzureOpenAI
import os

logger = logging.getLogger(__name__)

class ValidationResult:
    """Enhanced validation result with intelligent suggestions."""
    
    def __init__(self, is_valid: bool, cleaned_args: Dict[str, Any] = None, 
                 errors: List[str] = None, suggestions: List[str] = None,
                 confidence_score: float = 1.0):
        self.is_valid = is_valid
        self.cleaned_args = cleaned_args or {}
        self.errors = errors or []
        self.suggestions = suggestions or []
        self.confidence_score = confidence_score
    
    def __str__(self):
        status = "Valid" if self.is_valid else "Invalid"
        return f"ValidationResult(status={status}, errors={len(self.errors)}, suggestions={len(self.suggestions)})"

class IntelligentArgumentValidator:
    """Intelligent argument validator with LLM-powered features."""
    
    def __init__(self, azure_endpoint: str = None, azure_key: str = None, 
                 azure_deployment: str = None):
        self.logger = logging.getLogger(__name__)
        
        # Initialize Azure OpenAI client
        try:
            self.llm_client = AzureOpenAI(
                azure_endpoint=azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=azure_key or os.getenv("AZURE_OPENAI_API_KEY"),
                api_version="2024-02-15-preview"
            )
            self.deployment_name = azure_deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
            self.llm_available = True
            logger.info("✅ Intelligent validator initialized with Azure OpenAI")
        except Exception as e:
            logger.warning(f"⚠️  Azure OpenAI not available: {e}")
            self.llm_client = None
            self.llm_available = False
    
    def validate_arguments(self, arguments: Dict[str, Any], 
                         tool_schema: Dict[str, Any], method: str = 'GET',
                         tool_name: str = None, tool_description: str = None) -> ValidationResult:
        """Enhanced validation with intelligent analysis."""
        logger.info(f"🧠 Intelligently validating arguments for {method} request: {arguments}")
        
        # Basic validation first
        basic_result = self._basic_validation(arguments, tool_schema)
        
        if not self.llm_available:
            return basic_result
        
        # If basic validation passes, return it
        if basic_result.is_valid:
            return basic_result
        
        # Use LLM for intelligent error analysis and suggestions
        enhanced_result = self._enhance_validation_with_llm(
            arguments, tool_schema, basic_result, method, tool_name, tool_description
        )
        
        return enhanced_result
    
    def _basic_validation(self, arguments: Dict[str, Any], 
                         tool_schema: Dict[str, Any]) -> ValidationResult:
        """Perform basic schema validation."""
        try:
            # Clean arguments
            cleaned_args = self._clean_arguments(arguments)
            
            # Validate against schema
            errors = self._validate_against_schema(cleaned_args, tool_schema)
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                cleaned_args=cleaned_args,
                errors=errors
            )
        except Exception as e:
            logger.error(f"Basic validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
    
    def _enhance_validation_with_llm(self, arguments: Dict[str, Any],
                                   tool_schema: Dict[str, Any],
                                   basic_result: ValidationResult,
                                   method: str, tool_name: str = None,
                                   tool_description: str = None) -> ValidationResult:
        """Use LLM to provide intelligent validation enhancement."""
        try:
            # Prepare context for LLM
            context = {
                "tool_name": tool_name or "unknown",
                "tool_description": tool_description or "No description",
                "method": method,
                "provided_arguments": arguments,
                "expected_schema": tool_schema,
                "validation_errors": basic_result.errors
            }
            
            # Create LLM prompt
            prompt = self._create_validation_prompt(context)
            
            # Get LLM response
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert API validation assistant. Analyze validation errors and provide helpful suggestions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse LLM response
            llm_analysis = self._parse_llm_response(response.choices[0].message.content)
            
            # Enhance the basic result
            enhanced_result = ValidationResult(
                is_valid=basic_result.is_valid,
                cleaned_args=basic_result.cleaned_args,
                errors=llm_analysis.get('enhanced_errors', basic_result.errors),
                suggestions=llm_analysis.get('suggestions', []),
                confidence_score=llm_analysis.get('confidence', 0.8)
            )
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
            # Return basic result if LLM fails
            return basic_result
    
    def _create_validation_prompt(self, context: Dict[str, Any]) -> str:
        """Create intelligent validation prompt for LLM."""
        return f"""
Analyze this API validation scenario and provide intelligent feedback:

**API Tool Information:**
- Name: {context['tool_name']}
- Description: {context['tool_description']}
- HTTP Method: {context['method']}

**User Provided Arguments:**
```json
{json.dumps(context['provided_arguments'], indent=2)}
```

**Expected Schema:**
```json
{json.dumps(context['expected_schema'], indent=2)}
```

**Current Validation Errors:**
{chr(10).join(f"- {error}" for error in context['validation_errors'])}

**Please provide a JSON response with:**
1. `enhanced_errors`: More user-friendly error messages
2. `suggestions`: Specific suggestions to fix the issues
3. `confidence`: Your confidence in the analysis (0.0-1.0)
4. `auto_fix_possible`: Whether you can suggest automatic fixes
5. `corrected_arguments`: If possible, provide corrected arguments

Focus on:
- Making error messages more understandable
- Providing specific examples of correct values
- Suggesting common fixes for typical mistakes
- Understanding the business context of the API
"""
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured data."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to parse entire response as JSON
            return json.loads(response_text)
            
        except json.JSONDecodeError:
            # Fallback: extract suggestions from text
            suggestions = []
            lines = response_text.split('\n')
            for line in lines:
                if line.strip().startswith('-') or line.strip().startswith('•'):
                    suggestions.append(line.strip()[1:].strip())
            
            return {
                'enhanced_errors': [],
                'suggestions': suggestions[:5],  # Limit to 5 suggestions
                'confidence': 0.6
            }
    
    def suggest_corrections(self, arguments: Dict[str, Any],
                          tool_schema: Dict[str, Any],
                          tool_name: str = None) -> Dict[str, Any]:
        """Use LLM to suggest argument corrections."""
        if not self.llm_available:
            return arguments
        
        try:
            prompt = f"""
Given this API call that has validation issues, suggest corrected arguments:

**API Tool:** {tool_name or 'Unknown'}
**Current Arguments:**
```json
{json.dumps(arguments, indent=2)}
```

**Expected Schema:**
```json
{json.dumps(tool_schema, indent=2)}
```

Provide corrected arguments as JSON that would pass validation.
Focus on:
- Fixing type mismatches
- Adding missing required fields with reasonable defaults
- Correcting enum values
- Fixing format issues

Return only the corrected JSON arguments.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API correction assistant. Provide only valid JSON arguments."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            # Parse corrected arguments
            response_text = response.choices[0].message.content
            json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            return json.loads(response_text)
            
        except Exception as e:
            logger.error(f"Argument correction failed: {e}")
            return arguments
    
    def explain_schema(self, tool_schema: Dict[str, Any], 
                      tool_name: str = None, tool_description: str = None) -> str:
        """Use LLM to explain API schema in human-friendly terms."""
        if not self.llm_available:
            return "Schema explanation not available (LLM not configured)"
        
        try:
            prompt = f"""
Explain this API schema in simple, user-friendly terms:

**API Tool:** {tool_name or 'Unknown API'}
**Description:** {tool_description or 'No description available'}

**Schema:**
```json
{json.dumps(tool_schema, indent=2)}
```

Provide a clear explanation that includes:
1. What this API does
2. Required parameters and their purpose
3. Optional parameters and when to use them
4. Examples of valid requests
5. Common mistakes to avoid

Make it conversational and helpful for developers.
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful API documentation assistant. Explain technical schemas in simple terms."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Schema explanation failed: {e}")
            return f"Unable to explain schema: {str(e)}"
    
    def _clean_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Clean arguments by removing empty/null values."""
        cleaned = {}
        
        for key, value in arguments.items():
            if isinstance(value, dict):
                # Recursively clean nested objects
                cleaned_nested = self._clean_arguments(value)
                if cleaned_nested:  # Only add if not empty
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
                    errors.append(f"Missing required field in body: {field}")
            
            # Validate body fields
            for field_name, field_value in body.items():
                if field_name in body_properties:
                    field_errors = self._validate_field(field_name, field_value, body_properties[field_name])
                    errors.extend(field_errors)
        
        return errors
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
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

# Example usage and integration
if __name__ == "__main__":
    # Example of how to use the intelligent validator
    validator = IntelligentArgumentValidator()
    
    # Test schema
    test_schema = {
        "type": "object",
        "properties": {
            "body": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "minimum": 0.01},
                    "currency": {"type": "string", "enum": ["USD", "EUR", "GBP"]}
                },
                "required": ["amount", "currency"]
            }
        }
    }
    
    # Test arguments with issues
    test_args = {
        "body": {
            "amount": -10,  # Invalid: negative
            "currency": "JPY"  # Invalid: not in enum
        }
    }
    
    # Validate with intelligence
    result = validator.validate_arguments(
        test_args, test_schema, 'POST', 
        tool_name="createPayment",
        tool_description="Create a new payment transaction"
    )
    
    print(f"Validation Result: {result}")
    print(f"Errors: {result.errors}")
    print(f"Suggestions: {result.suggestions}")
    
    # Get schema explanation
    explanation = validator.explain_schema(
        test_schema, 
        "createPayment", 
        "Create a new payment transaction"
    )
    print(f"\nSchema Explanation:\n{explanation}")