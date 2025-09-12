#!/usr/bin/env python3
"""
Test Runner for MCP System
==========================
Runs all test cases and provides comprehensive reporting
"""

import unittest
import sys
import os
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_all_tests():
    """Run all test cases and provide comprehensive reporting"""
    print("🧪 MCP System Test Suite")
    print("=" * 50)
    print()
    
    # Test modules to run
    test_modules = [
        'test_mcp_server',
        'test_mcp_client', 
        'test_mcp_service',
        'test_web_ui',
        'test_integration'
    ]
    
    # Results tracking
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    
    start_time = time.time()
    
    for module_name in test_modules:
        print(f"🔍 Running {module_name}...")
        print("-" * 30)
        
        try:
            # Import and run the test module
            module = __import__(module_name)
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)
            
            # Run tests
            runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
            result = runner.run(suite)
            
            # Track results
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            total_skipped += len(result.skipped)
            
            print(f"✅ {module_name} completed: {result.testsRun} tests")
            if result.failures:
                print(f"   ❌ Failures: {len(result.failures)}")
            if result.errors:
                print(f"   ❌ Errors: {len(result.errors)}")
            if result.skipped:
                print(f"   ⏭️ Skipped: {len(result.skipped)}")
            
        except Exception as e:
            print(f"❌ Error running {module_name}: {e}")
            total_errors += 1
        
        print()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Print summary
    print("📊 Test Summary")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_tests - total_failures - total_errors - total_skipped}")
    print(f"Failed: {total_failures}")
    print(f"Errors: {total_errors}")
    print(f"Skipped: {total_skipped}")
    print(f"Duration: {duration:.2f} seconds")
    print()
    
    if total_failures == 0 and total_errors == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed or had errors")
        return False

def run_specific_tests(test_names):
    """Run specific test cases"""
    print(f"🔍 Running specific tests: {', '.join(test_names)}")
    print("=" * 50)
    
    for test_name in test_names:
        try:
            module = __import__(test_name)
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)
            
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            
            print(f"✅ {test_name} completed: {result.testsRun} tests")
            
        except Exception as e:
            print(f"❌ Error running {test_name}: {e}")

def run_quick_tests():
    """Run quick tests (unit tests only)"""
    print("⚡ Running Quick Tests (Unit Tests Only)")
    print("=" * 50)
    
    quick_modules = [
        'test_mcp_server',
        'test_mcp_client',
        'test_mcp_service',
        'test_web_ui'
    ]
    
    return run_specific_tests(quick_modules)

def run_integration_tests():
    """Run integration tests only"""
    print("🔗 Running Integration Tests")
    print("=" * 50)
    
    return run_specific_tests(['test_integration'])

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'quick':
            success = run_quick_tests()
        elif command == 'integration':
            success = run_integration_tests()
        elif command == 'specific':
            if len(sys.argv) > 2:
                test_names = sys.argv[2:]
                run_specific_tests(test_names)
                success = True
            else:
                print("❌ Please specify test names after 'specific'")
                success = False
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: quick, integration, specific <test_names>")
            success = False
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)