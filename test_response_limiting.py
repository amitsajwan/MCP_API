#!/usr/bin/env python3
"""
Test script for response limiting functionality in MCP server
"""

import sys
import os
import json

# Add the current directory to Python path to import from mcp_server_fastmcp2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server_fastmcp2 import limit_response_items

def test_list_response_limiting():
    """Test limiting of list responses"""
    print("🧪 Testing list response limiting...")
    
    # Test case 1: Small list (should not be limited)
    small_list = [{"id": i, "name": f"item_{i}"} for i in range(50)]
    result = limit_response_items(small_list, 100)
    assert result == small_list, "Small list should not be limited"
    print("✅ Small list (50 items) - not limited")
    
    # Test case 2: Large list (should be limited)
    large_list = [{"id": i, "name": f"item_{i}"} for i in range(250)]
    result = limit_response_items(large_list, 100)
    
    assert isinstance(result, dict), "Large list should be wrapped in dict with metadata"
    assert "items" in result, "Result should contain 'items' field"
    assert len(result["items"]) == 100, f"Limited list should have 100 items, got {len(result['items'])}"
    assert result["total_count"] == 250, f"Total count should be 250, got {result['total_count']}"
    assert result["truncated"] == True, "Should be marked as truncated"
    print("✅ Large list (250 items) - limited to 100 items")
    
    # Test case 3: Very large list with custom limit
    very_large_list = [{"id": i, "name": f"item_{i}"} for i in range(1000)]
    result = limit_response_items(very_large_list, 50)
    
    assert len(result["items"]) == 50, f"Should be limited to 50 items, got {len(result['items'])}"
    assert result["total_count"] == 1000, f"Total count should be 1000, got {result['total_count']}"
    print("✅ Very large list (1000 items) - limited to 50 items")

def test_dict_response_limiting():
    """Test limiting of dict responses with list fields"""
    print("\n🧪 Testing dict response limiting...")
    
    # Test case 1: Dict with small list field
    small_dict = {
        "status": "success",
        "data": [{"id": i, "name": f"item_{i}"} for i in range(50)],
        "count": 50
    }
    result = limit_response_items(small_dict, 100)
    assert result == small_dict, "Dict with small list should not be limited"
    print("✅ Dict with small list field - not limited")
    
    # Test case 2: Dict with large list field
    large_dict = {
        "status": "success",
        "data": [{"id": i, "name": f"item_{i}"} for i in range(250)],
        "count": 250
    }
    result = limit_response_items(large_dict, 100)
    
    assert len(result["data"]) == 100, f"Data field should be limited to 100 items, got {len(result['data'])}"
    assert "_truncation_info" in result, "Should contain truncation info"
    assert result["_truncation_info"]["data_truncated"] == True, "Should mark data as truncated"
    assert result["_truncation_info"]["data_total_count"] == 250, "Should record original count"
    print("✅ Dict with large list field - limited")
    
    # Test case 3: Dict with multiple list fields
    multi_dict = {
        "items": [{"id": i} for i in range(150)],
        "results": [{"id": i} for i in range(200)],
        "records": [{"id": i} for i in range(50)],
        "metadata": {"total": 400}
    }
    result = limit_response_items(multi_dict, 100)
    
    assert len(result["items"]) == 100, "Items should be limited"
    assert len(result["results"]) == 100, "Results should be limited"
    assert len(result["records"]) == 50, "Records should not be limited (already under limit)"
    assert "_truncation_info" in result, "Should contain truncation info"
    print("✅ Dict with multiple list fields - appropriate fields limited")

def test_non_list_responses():
    """Test that non-list responses are not affected"""
    print("\n🧪 Testing non-list responses...")
    
    # Test string response
    string_response = "This is a string response"
    result = limit_response_items(string_response, 100)
    assert result == string_response, "String response should not be modified"
    print("✅ String response - not modified")
    
    # Test number response
    number_response = 42
    result = limit_response_items(number_response, 100)
    assert result == number_response, "Number response should not be modified"
    print("✅ Number response - not modified")
    
    # Test dict without list fields
    simple_dict = {"status": "success", "message": "Operation completed"}
    result = limit_response_items(simple_dict, 100)
    assert result == simple_dict, "Simple dict should not be modified"
    print("✅ Simple dict - not modified")

def test_edge_cases():
    """Test edge cases"""
    print("\n🧪 Testing edge cases...")
    
    # Test empty list
    empty_list = []
    result = limit_response_items(empty_list, 100)
    assert result == empty_list, "Empty list should not be modified"
    print("✅ Empty list - not modified")
    
    # Test list with exactly the limit
    exact_limit_list = [{"id": i} for i in range(100)]
    result = limit_response_items(exact_limit_list, 100)
    assert result == exact_limit_list, "List at exact limit should not be modified"
    print("✅ List at exact limit - not modified")
    
    # Test list with one more than limit
    over_limit_list = [{"id": i} for i in range(101)]
    result = limit_response_items(over_limit_list, 100)
    assert len(result["items"]) == 100, "Should be limited to 100 items"
    assert result["total_count"] == 101, "Should record original count"
    print("✅ List one over limit - limited correctly")

def main():
    """Run all tests"""
    print("🚀 Starting response limiting tests...\n")
    
    try:
        test_list_response_limiting()
        test_dict_response_limiting()
        test_non_list_responses()
        test_edge_cases()
        
        print("\n🎉 All tests passed! Response limiting is working correctly.")
        print("\n📊 Summary:")
        print("   ✅ List responses are limited to 100 items by default")
        print("   ✅ Dict responses with list fields are limited appropriately")
        print("   ✅ Non-list responses are not affected")
        print("   ✅ Edge cases are handled correctly")
        print("   ✅ Truncation metadata is added when limiting occurs")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())