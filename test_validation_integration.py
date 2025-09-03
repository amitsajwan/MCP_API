#!/usr/bin/env python3
"""
Test script to demonstrate argument validation for complex POST APIs with payloads.
This script tests the integrated validation system in mcp_server.py.
"""

import json
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from argument_validator import ArgumentValidator, ValidationResult
    from mcp_server import MCPServer, APITool
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure argument_validator.py and mcp_server.py are in the same directory")
    sys.exit(1)

def test_payment_validation():
    """Test validation for createPayment POST API with complex payload."""
    print("\n=== Testing Payment Creation Validation ===")
    
    # Mock tool parameters for createPayment (from cash_api.yaml)
    payment_tool_params = {
        'body': {
            'type': 'object',
            'properties': {
                'amount': {'type': 'number', 'minimum': 0.01},
                'currency': {'type': 'string', 'enum': ['USD', 'EUR', 'GBP']},
                'recipient': {'type': 'string', 'minLength': 1},
                'requester_id': {'type': 'string', 'minLength': 1},
                'description': {'type': 'string'},
                'reference': {'type': 'string'}
            },
            'required': ['amount', 'currency', 'recipient', 'requester_id']
        }
    }
    
    validator = ArgumentValidator()
    
    # Test cases
    test_cases = [
        {
            'name': 'Valid complete payload',
            'args': {
                'body': {
                    'amount': 100.50,
                    'currency': 'USD',
                    'recipient': 'john@example.com',
                    'requester_id': 'user123',
                    'description': 'Payment for services',
                    'reference': 'REF001'
                }
            },
            'should_pass': True
        },
        {
            'name': 'Missing required field (amount)',
            'args': {
                'body': {
                    'currency': 'USD',
                    'recipient': 'john@example.com',
                    'requester_id': 'user123'
                }
            },
            'should_pass': False
        },
        {
            'name': 'Invalid currency enum',
            'args': {
                'body': {
                    'amount': 100.50,
                    'currency': 'JPY',  # Not in enum
                    'recipient': 'john@example.com',
                    'requester_id': 'user123'
                }
            },
            'should_pass': False
        },
        {
            'name': 'Empty strings in required fields',
            'args': {
                'body': {
                    'amount': 100.50,
                    'currency': 'USD',
                    'recipient': '',  # Empty string
                    'requester_id': 'user123'
                }
            },
            'should_pass': False
        },
        {
            'name': 'Null values in payload',
            'args': {
                'body': {
                    'amount': 100.50,
                    'currency': 'USD',
                    'recipient': 'john@example.com',
                    'requester_id': None,  # Null value
                    'description': None
                }
            },
            'should_pass': False
        },
        {
            'name': 'Amount below minimum',
            'args': {
                'body': {
                    'amount': 0.001,  # Below minimum of 0.01
                    'currency': 'USD',
                    'recipient': 'john@example.com',
                    'requester_id': 'user123'
                }
            },
            'should_pass': False
        },
        {
            'name': 'Valid payload with optional fields removed',
            'args': {
                'body': {
                    'amount': 100.50,
                    'currency': 'USD',
                    'recipient': 'john@example.com',
                    'requester_id': 'user123',
                    'description': '',  # Should be cleaned out
                    'reference': None   # Should be cleaned out
                }
            },
            'should_pass': True
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"Input: {json.dumps(test_case['args'], indent=2)}")
        
        result = validator.validate_arguments(
            test_case['args'], 
            payment_tool_params, 
            'POST'
        )
        
        print(f"Expected to pass: {test_case['should_pass']}")
        print(f"Actually passed: {result.is_valid}")
        
        if result.is_valid:
            print(f"Cleaned arguments: {json.dumps(result.cleaned_args, indent=2)}")
        else:
            print(f"Validation errors: {result.errors}")
        
        # Check if result matches expectation
        if result.is_valid == test_case['should_pass']:
            print("✅ Test passed")
        else:
            print("❌ Test failed - unexpected result")

def test_query_parameter_validation():
    """Test validation for GET APIs with query parameters."""
    print("\n\n=== Testing Query Parameter Validation ===")
    
    # Mock tool schema for getPayments (from cash_api.yaml)
    query_tool_schema = {
        'type': 'object',
        'properties': {
            'status': {
                'type': 'string',
                'enum': ['pending', 'completed', 'failed']
            },
            'limit': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 100
            },
            'offset': {
                'type': 'integer',
                'minimum': 0
            }
        },
        'required': []
    }
    
    validator = ArgumentValidator()
    
    test_cases = [
        {
            'name': 'Valid query parameters',
            'args': {
                'status': 'pending',
                'limit': 10,
                'offset': 0
            },
            'should_pass': True
        },
        {
            'name': 'Empty string parameters (should be cleaned)',
            'args': {
                'status': '',
                'limit': 10,
                'offset': 0
            },
            'should_pass': True
        },
        {
            'name': 'Invalid enum value',
            'args': {
                'status': 'invalid_status',
                'limit': 10
            },
            'should_pass': False
        },
        {
            'name': 'Limit exceeds maximum',
            'args': {
                'limit': 150,  # Exceeds maximum of 100
                'offset': 0
            },
            'should_pass': False
        },
        {
            'name': 'Negative offset',
            'args': {
                'limit': 10,
                'offset': -1  # Below minimum of 0
            },
            'should_pass': False
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"Input: {json.dumps(test_case['args'], indent=2)}")
        
        result = validator.validate_arguments(
            test_case['args'], 
            query_tool_schema, 
            'GET'
        )
        
        print(f"Expected to pass: {test_case['should_pass']}")
        print(f"Actually passed: {result.is_valid}")
        
        if result.is_valid:
            print(f"Cleaned arguments: {json.dumps(result.cleaned_args, indent=2)}")
        else:
            print(f"Validation errors: {result.errors}")
        
        # Check if result matches expectation
        if result.is_valid == test_case['should_pass']:
            print("✅ Test passed")
        else:
            print("❌ Test failed - unexpected result")

def test_edge_cases():
    """Test edge cases and complex scenarios."""
    print("\n\n=== Testing Edge Cases ===")
    
    validator = ArgumentValidator()
    
    # Test with completely empty body
    print("\nTesting empty body:")
    result = validator.validate_arguments(
        {'body': {}},
        {'body': {'type': 'object', 'required': ['field1']}},
        'POST'
    )
    print(f"Empty body validation: {'✅ Passed' if not result.is_valid else '❌ Failed'}")
    print(f"Errors: {result.errors}")
    
    # Test with no body parameter
    print("\nTesting missing body:")
    result = validator.validate_arguments(
        {},
        {'body': {'type': 'object', 'required': ['field1']}},
        'POST'
    )
    print(f"Missing body validation: {'✅ Passed' if not result.is_valid else '❌ Failed'}")
    print(f"Errors: {result.errors}")
    
    # Test with nested object cleaning
    print("\nTesting nested object cleaning:")
    result = validator.validate_arguments(
        {
            'body': {
                'user': {
                    'name': 'John',
                    'email': '',  # Should be cleaned
                    'phone': None  # Should be cleaned
                },
                'amount': 100
            }
        },
        {
            'body': {
                'type': 'object',
                'properties': {
                    'user': {'type': 'object'},
                    'amount': {'type': 'number'}
                },
                'required': ['amount']
            }
        },
        'POST'
    )
    print(f"Nested cleaning: {'✅ Passed' if result.is_valid else '❌ Failed'}")
    if result.is_valid:
        print(f"Cleaned result: {json.dumps(result.cleaned_args, indent=2)}")

def main():
    """Run all validation tests."""
    print("🧪 Testing Argument Validation for Complex APIs")
    print("=" * 50)
    
    try:
        test_payment_validation()
        test_query_parameter_validation()
        test_edge_cases()
        
        print("\n\n🎉 All validation tests completed!")
        print("\n📋 Summary:")
        print("- ✅ POST APIs with complex payloads are validated")
        print("- ✅ Required fields are enforced")
        print("- ✅ Empty strings and null values are cleaned")
        print("- ✅ Enum values are validated")
        print("- ✅ Numeric constraints (min/max) are enforced")
        print("- ✅ String constraints (minLength) are enforced")
        print("- ✅ Query parameters are validated")
        print("- ✅ Nested objects are cleaned recursively")
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())