#!/usr/bin/env python3
"""
Test script to verify payload validation and handling of empty/null arguments
in complex POST API operations.
"""

import json
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simulate_argument_processing(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate how the current system processes arguments before API calls."""
    
    # This mirrors the logic in mcp_server.py _execute_tool method
    request_data = None
    query_params = {}
    
    print(f"\n📥 Input arguments: {json.dumps(arguments, indent=2)}")
    
    for param_name, value in arguments.items():
        if param_name == 'body':
            request_data = value
            print(f"📦 Request body set: {json.dumps(request_data, indent=2)}")
        else:
            # Simulate query parameter processing
            query_params[param_name] = value
            print(f"🔍 Query param added: {param_name} = {repr(value)}")
    
    print(f"\n📤 Final request data: {json.dumps(request_data, indent=2)}")
    print(f"📤 Final query params: {json.dumps(query_params, indent=2)}")
    
    return {
        "request_data": request_data,
        "query_params": query_params
    }

def test_payment_creation_scenarios():
    """Test various payment creation scenarios."""
    
    test_cases = [
        {
            "name": "✅ Complete valid payload",
            "args": {
                "body": {
                    "amount": 100.50,
                    "currency": "USD",
                    "recipient": "John Doe",
                    "requester_id": "user123",
                    "description": "Test payment"
                }
            }
        },
        {
            "name": "⚠️  Empty string in required field",
            "args": {
                "body": {
                    "amount": 100.50,
                    "currency": "USD",
                    "recipient": "",  # Empty string - should be invalid
                    "requester_id": "user123",
                    "description": "Test payment"
                }
            }
        },
        {
            "name": "❌ Null value in required field",
            "args": {
                "body": {
                    "amount": 100.50,
                    "currency": "USD",
                    "recipient": None,  # Null - should be invalid
                    "requester_id": "user123",
                    "description": "Test payment"
                }
            }
        },
        {
            "name": "❌ Missing required fields",
            "args": {
                "body": {
                    "amount": 100.50,
                    "currency": "USD"
                    # Missing: recipient, requester_id
                }
            }
        },
        {
            "name": "❌ Empty body",
            "args": {
                "body": {}
            }
        },
        {
            "name": "❌ No body at all",
            "args": {}
        }
    ]
    
    print("\n" + "="*60)
    print("🧪 TESTING PAYMENT CREATION SCENARIOS")
    print("="*60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 50)
        
        result = simulate_argument_processing(test_case['args'])
        
        # Analyze the result
        request_data = result['request_data']
        if request_data:
            issues = analyze_payload_issues(request_data)
            if issues:
                print(f"🚨 VALIDATION ISSUES DETECTED:")
                for issue in issues:
                    print(f"   • {issue}")
            else:
                print(f"✅ Payload appears valid")
        else:
            print(f"🚨 NO REQUEST BODY - API call will likely fail")

def test_query_parameter_scenarios():
    """Test query parameter handling."""
    
    test_cases = [
        {
            "name": "✅ Valid query parameters",
            "args": {
                "status": "pending",
                "date_from": "2024-01-01",
                "amount_min": 100
            }
        },
        {
            "name": "⚠️  Empty string parameters",
            "args": {
                "status": "",
                "date_from": "",
                "amount_min": ""
            }
        },
        {
            "name": "❌ Null parameters",
            "args": {
                "status": None,
                "date_from": None,
                "amount_min": None
            }
        }
    ]
    
    print("\n" + "="*60)
    print("🧪 TESTING QUERY PARAMETER SCENARIOS")
    print("="*60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 50)
        
        result = simulate_argument_processing(test_case['args'])
        
        # Analyze query parameters
        query_params = result['query_params']
        issues = analyze_query_param_issues(query_params)
        
        if issues:
            print(f"🚨 QUERY PARAMETER ISSUES:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print(f"✅ Query parameters appear valid")

def analyze_payload_issues(payload: Dict[str, Any]) -> list:
    """Analyze payload for potential validation issues."""
    issues = []
    
    # Required fields for PaymentRequest (from OpenAPI spec)
    required_fields = ['amount', 'currency', 'recipient', 'requester_id']
    
    for field in required_fields:
        if field not in payload:
            issues.append(f"Missing required field: {field}")
        elif payload[field] is None:
            issues.append(f"Required field '{field}' is null")
        elif isinstance(payload[field], str) and payload[field].strip() == "":
            issues.append(f"Required field '{field}' is empty string")
    
    # Check data types
    if 'amount' in payload and payload['amount'] is not None:
        if not isinstance(payload['amount'], (int, float)):
            issues.append(f"Field 'amount' should be numeric, got {type(payload['amount'])}")
    
    return issues

def analyze_query_param_issues(params: Dict[str, Any]) -> list:
    """Analyze query parameters for issues."""
    issues = []
    
    for param_name, value in params.items():
        if value is None:
            issues.append(f"Parameter '{param_name}' is null (may cause API issues)")
        elif isinstance(value, str) and value.strip() == "":
            issues.append(f"Parameter '{param_name}' is empty string (may cause API issues)")
    
    return issues

def show_current_system_analysis():
    """Show analysis of current system behavior."""
    
    print("\n" + "="*60)
    print("📊 CURRENT SYSTEM ANALYSIS")
    print("="*60)
    
    print("\n🔍 ARGUMENT PROCESSING:")
    print("   • Arguments passed directly from LLM to API")
    print("   • 'body' parameter becomes request JSON payload")
    print("   • Other parameters become query parameters")
    print("   • NO validation before API call")
    
    print("\n❌ MISSING VALIDATIONS:")
    print("   • Required field validation")
    print("   • Data type validation")
    print("   • Empty/null value filtering")
    print("   • Schema constraint enforcement")
    print("   • Enum value validation")
    
    print("\n⚠️  RISK SCENARIOS:")
    print("   • POST requests with incomplete payloads reach APIs")
    print("   • Empty strings in required fields cause API errors")
    print("   • Null values may break API processing")
    print("   • Invalid data types cause runtime errors")
    print("   • Poor error messages confuse users")
    
    print("\n✅ RECOMMENDED IMPROVEMENTS:")
    print("   • Add pre-request payload validation")
    print("   • Filter out null/empty values where appropriate")
    print("   • Validate against OpenAPI schema constraints")
    print("   • Provide clear validation error messages")
    print("   • Use Pydantic models for automatic validation")

if __name__ == "__main__":
    try:
        show_current_system_analysis()
        test_payment_creation_scenarios()
        test_query_parameter_scenarios()
        
        print("\n" + "="*60)
        print("🎯 CONCLUSION")
        print("="*60)
        print("\nThe current system DOES NOT validate arguments before API calls.")
        print("Empty strings, null values, and missing required fields are")
        print("passed directly to APIs, potentially causing failures.")
        print("\nImplementing validation would prevent these issues and improve")
        print("user experience with better error messages.")
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        print(f"\nTest execution failed: {e}")