#!/usr/bin/env python3
"""
Test script to check OpenAPI specs loading
"""

import os
import yaml
from pathlib import Path

def test_openapi_loading():
    """Test loading OpenAPI specs"""
    print("🧪 Testing OpenAPI Specs Loading")
    print("=" * 50)
    
    openapi_dir = Path("./openapi_specs")
    if not openapi_dir.exists():
        print("❌ OpenAPI directory not found")
        return
    
    print(f"📂 OpenAPI directory: {openapi_dir}")
    
    for spec_file in openapi_dir.glob("*.yaml"):
        print(f"\n📄 Loading: {spec_file}")
        try:
            with open(spec_file, 'r') as f:
                spec_data = yaml.safe_load(f)
            
            print(f"  ✅ Loaded successfully")
            print(f"  📋 Title: {spec_data.get('info', {}).get('title', 'Unknown')}")
            print(f"  🔗 Servers: {len(spec_data.get('servers', []))}")
            print(f"  🛠️  Paths: {len(spec_data.get('paths', {}))}")
            
            # Count operations
            operation_count = 0
            for path, path_item in spec_data.get('paths', {}).items():
                for method in ['get', 'post', 'put', 'delete', 'patch']:
                    if method in path_item:
                        operation_count += 1
            
            print(f"  🔧 Operations: {operation_count}")
            
        except Exception as e:
            print(f"  ❌ Failed to load: {e}")

if __name__ == "__main__":
    test_openapi_loading()
