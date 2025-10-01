"""
Validators for Demo MCP System
"""

from typing import Dict, List, Any, Optional, Union
import re


def validate_parameters(tool_params: Dict[str, str], provided_params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate tool parameters"""
    errors = []
    warnings = []
    
    # Check required parameters
    for param_name, param_type in tool_params.items():
        if param_name not in provided_params:
            errors.append(f"Missing required parameter: {param_name}")
        else:
            # Type validation
            value = provided_params[param_name]
            if param_type == "string" and not isinstance(value, str):
                errors.append(f"Parameter {param_name} should be string")
            elif param_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Parameter {param_name} should be number")
            elif param_type == "object" and not isinstance(value, dict):
                errors.append(f"Parameter {param_name} should be object")
    
    # Check for extra parameters
    for param_name in provided_params:
        if param_name not in tool_params:
            warnings.append(f"Unknown parameter: {param_name}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_use_case(use_case: Dict[str, Any]) -> Dict[str, Any]:
    """Validate use case structure"""
    errors = []
    warnings = []
    
    # Required fields
    required_fields = ["id", "name", "description", "tools", "category"]
    for field in required_fields:
        if field not in use_case:
            errors.append(f"Missing required field: {field}")
    
    # Validate tools
    if "tools" in use_case:
        if not isinstance(use_case["tools"], list):
            errors.append("Tools should be a list")
        elif len(use_case["tools"]) == 0:
            warnings.append("Use case has no tools")
    
    # Validate complexity
    if "complexity" in use_case:
        valid_complexities = ["Low", "Medium", "High"]
        if use_case["complexity"] not in valid_complexities:
            errors.append(f"Invalid complexity: {use_case['complexity']}")
    
    # Validate business value
    if "business_value" in use_case:
        valid_values = ["Low", "Medium", "High", "Critical"]
        if use_case["business_value"] not in valid_values:
            errors.append(f"Invalid business value: {use_case['business_value']}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_tool(tool: Dict[str, Any]) -> Dict[str, Any]:
    """Validate tool structure"""
    errors = []
    warnings = []
    
    # Required fields
    required_fields = ["name", "description", "parameters", "category"]
    for field in required_fields:
        if field not in tool:
            errors.append(f"Missing required field: {field}")
    
    # Validate name
    if "name" in tool:
        if not isinstance(tool["name"], str) or len(tool["name"]) == 0:
            errors.append("Tool name should be a non-empty string")
        elif not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', tool["name"]):
            errors.append("Tool name should contain only letters, numbers, and underscores")
    
    # Validate parameters
    if "parameters" in tool:
        if not isinstance(tool["parameters"], dict):
            errors.append("Parameters should be a dictionary")
        else:
            for param_name, param_type in tool["parameters"].items():
                if not isinstance(param_type, str):
                    errors.append(f"Parameter type for {param_name} should be string")
                elif param_type not in ["string", "number", "object", "boolean"]:
                    errors.append(f"Invalid parameter type for {param_name}: {param_type}")
    
    # Validate category
    if "category" in tool:
        valid_categories = [
            "Authentication", "Account", "Payment", "Investment", 
            "Market Data", "Risk Analysis", "Support", "General"
        ]
        if tool["category"] not in valid_categories:
            warnings.append(f"Unknown category: {tool['category']}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_json_schema(data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Validate data against JSON schema (simplified)"""
    errors = []
    
    if "type" in schema:
        expected_type = schema["type"]
        if expected_type == "object" and not isinstance(data, dict):
            errors.append(f"Expected object, got {type(data).__name__}")
        elif expected_type == "array" and not isinstance(data, list):
            errors.append(f"Expected array, got {type(data).__name__}")
        elif expected_type == "string" and not isinstance(data, str):
            errors.append(f"Expected string, got {type(data).__name__}")
        elif expected_type == "number" and not isinstance(data, (int, float)):
            errors.append(f"Expected number, got {type(data).__name__}")
        elif expected_type == "boolean" and not isinstance(data, bool):
            errors.append(f"Expected boolean, got {type(data).__name__}")
    
    if "required" in schema and isinstance(data, dict):
        for field in schema["required"]:
            if field not in data:
                errors.append(f"Missing required field: {field}")
    
    if "properties" in schema and isinstance(data, dict):
        for field, field_schema in schema["properties"].items():
            if field in data:
                field_result = validate_json_schema(data[field], field_schema)
                errors.extend(field_result["errors"])
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return re.match(pattern, url) is not None


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    # Check if it's a valid length (7-15 digits)
    return 7 <= len(digits) <= 15


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID format"""
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return re.match(pattern, uuid_str, re.IGNORECASE) is not None


def validate_date_format(date_str: str, format_str: str = "%Y-%m-%d") -> bool:
    """Validate date format"""
    try:
        from datetime import datetime
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False


def validate_range(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> bool:
    """Validate value is within range"""
    return min_val <= value <= max_val


def validate_list_length(lst: List[Any], min_length: int = 0, max_length: Optional[int] = None) -> bool:
    """Validate list length"""
    if len(lst) < min_length:
        return False
    if max_length is not None and len(lst) > max_length:
        return False
    return True


def validate_string_length(text: str, min_length: int = 0, max_length: Optional[int] = None) -> bool:
    """Validate string length"""
    if len(text) < min_length:
        return False
    if max_length is not None and len(text) > max_length:
        return False
    return True
