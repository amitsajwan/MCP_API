#!/usr/bin/env python3
"""
Examples of how to extend the Dynamic Tool Categorizer for different business domains.

This script demonstrates:
1. Adding custom categories for different industries
2. Testing categorization with various tool patterns
3. Showing how the system handles unknown APIs
"""

from tool_categorizer import DynamicToolCategorizer, ToolCategory

def setup_healthcare_categorizer():
    """Setup categorizer for healthcare domain."""
    categorizer = DynamicToolCategorizer()
    
    # Add healthcare-specific categories
    categorizer.add_category("healthcare_patient", ToolCategory(
        name="Patient Management",
        description="Tools for patient records, appointments, and care management",
        keywords=["patient", "appointment", "medical_record", "care"],
        priority=95
    ))
    
    categorizer.add_category("healthcare_clinical", ToolCategory(
        name="Clinical Operations",
        description="Tools for diagnosis, treatment, and clinical workflows",
        keywords=["diagnosis", "treatment", "clinical", "lab", "prescription"],
        priority=90
    ))
    
    categorizer.add_category("healthcare_billing", ToolCategory(
        name="Medical Billing",
        description="Tools for insurance, billing, and financial operations",
        keywords=["insurance", "billing", "claim", "payment"],
        priority=85
    ))
    
    return categorizer

def setup_ecommerce_categorizer():
    """Setup categorizer for e-commerce domain."""
    categorizer = DynamicToolCategorizer()
    
    # Add e-commerce specific categories
    categorizer.add_category("ecommerce_catalog", ToolCategory(
        name="Product Catalog",
        description="Tools for product management, inventory, and catalog operations",
        keywords=["product", "catalog", "inventory", "sku", "stock"],
        priority=95
    ))
    
    categorizer.add_category("ecommerce_orders", ToolCategory(
        name="Order Management",
        description="Tools for order processing, fulfillment, and tracking",
        keywords=["order", "cart", "checkout", "fulfillment", "shipping"],
        priority=90
    ))
    
    categorizer.add_category("ecommerce_customer", ToolCategory(
        name="Customer Experience",
        description="Tools for customer management, reviews, and support",
        keywords=["customer", "review", "support", "loyalty", "recommendation"],
        priority=85
    ))
    
    return categorizer

def setup_logistics_categorizer():
    """Setup categorizer for logistics domain."""
    categorizer = DynamicToolCategorizer()
    
    # Add logistics-specific categories
    categorizer.add_category("logistics_shipping", ToolCategory(
        name="Shipping & Delivery",
        description="Tools for shipping, delivery, and transportation management",
        keywords=["shipping", "delivery", "transport", "carrier", "tracking"],
        priority=95
    ))
    
    categorizer.add_category("logistics_warehouse", ToolCategory(
        name="Warehouse Operations",
        description="Tools for warehouse management, picking, and storage",
        keywords=["warehouse", "picking", "storage", "location", "receiving"],
        priority=90
    ))
    
    categorizer.add_category("logistics_fleet", ToolCategory(
        name="Fleet Management",
        description="Tools for vehicle tracking, route optimization, and fleet operations",
        keywords=["fleet", "vehicle", "route", "driver", "fuel"],
        priority=85
    ))
    
    return categorizer

def test_healthcare_tools():
    """Test healthcare tool categorization."""
    print("=== Healthcare Domain Test ===")
    categorizer = setup_healthcare_categorizer()
    
    healthcare_tools = [
        {"name": "patient_api_getRecord", "description": "Get patient medical record"},
        {"name": "appointment_api_schedule", "description": "Schedule patient appointment"},
        {"name": "lab_api_getResults", "description": "Get laboratory test results"},
        {"name": "prescription_api_create", "description": "Create new prescription"},
        {"name": "insurance_api_verifyBenefits", "description": "Verify insurance benefits"},
        {"name": "billing_api_generateClaim", "description": "Generate insurance claim"},
        {"name": "radiology_api_getImages", "description": "Get radiology images"},
        {"name": "login", "description": "Authenticate healthcare provider"}
    ]
    
    for tool in healthcare_tools:
        category = categorizer.categorize_tool(tool["name"], tool["description"])
        category_info = categorizer.get_category_info(category)
        print(f"{tool['name']} -> {category_info.name}")
    
    print("\n=== Healthcare Categorized Description ===")
    print(categorizer.build_categorized_description(healthcare_tools))

def test_ecommerce_tools():
    """Test e-commerce tool categorization."""
    print("\n=== E-commerce Domain Test ===")
    categorizer = setup_ecommerce_categorizer()
    
    ecommerce_tools = [
        {"name": "product_api_search", "description": "Search products in catalog"},
        {"name": "inventory_api_checkStock", "description": "Check product stock levels"},
        {"name": "cart_api_addItem", "description": "Add item to shopping cart"},
        {"name": "order_api_create", "description": "Create new customer order"},
        {"name": "shipping_api_calculateRate", "description": "Calculate shipping rates"},
        {"name": "customer_api_getProfile", "description": "Get customer profile"},
        {"name": "review_api_getReviews", "description": "Get product reviews"},
        {"name": "recommendation_api_getSuggestions", "description": "Get product recommendations"},
        {"name": "payment_api_processPayment", "description": "Process customer payment"}
    ]
    
    for tool in ecommerce_tools:
        category = categorizer.categorize_tool(tool["name"], tool["description"])
        category_info = categorizer.get_category_info(category)
        print(f"{tool['name']} -> {category_info.name}")

def test_logistics_tools():
    """Test logistics tool categorization."""
    print("\n=== Logistics Domain Test ===")
    categorizer = setup_logistics_categorizer()
    
    logistics_tools = [
        {"name": "shipping_api_createLabel", "description": "Create shipping label"},
        {"name": "tracking_api_getStatus", "description": "Get package tracking status"},
        {"name": "warehouse_api_pickOrder", "description": "Pick order from warehouse"},
        {"name": "location_api_findBin", "description": "Find storage bin location"},
        {"name": "fleet_api_trackVehicle", "description": "Track delivery vehicle"},
        {"name": "route_api_optimize", "description": "Optimize delivery routes"},
        {"name": "driver_api_assignDelivery", "description": "Assign delivery to driver"},
        {"name": "fuel_api_getConsumption", "description": "Get fuel consumption data"}
    ]
    
    for tool in logistics_tools:
        category = categorizer.categorize_tool(tool["name"], tool["description"])
        category_info = categorizer.get_category_info(category)
        print(f"{tool['name']} -> {category_info.name}")

def test_unknown_apis():
    """Test how the system handles completely unknown API patterns."""
    print("\n=== Unknown API Pattern Test ===")
    categorizer = DynamicToolCategorizer()
    
    unknown_tools = [
        {"name": "gaming_api_getPlayerStats", "description": "Get player statistics"},
        {"name": "social_api_postMessage", "description": "Post social media message"},
        {"name": "weather_api_getForecast", "description": "Get weather forecast"},
        {"name": "crypto_api_getPrice", "description": "Get cryptocurrency price"},
        {"name": "ai_api_generateText", "description": "Generate AI text content"},
        {"name": "blockchain_api_verifyTransaction", "description": "Verify blockchain transaction"}
    ]
    
    print("Before processing - Available categories:")
    for cat_id, cat_info in categorizer.get_all_categories().items():
        print(f"  {cat_id}: {cat_info.name}")
    
    print("\nCategorizing unknown tools:")
    for tool in unknown_tools:
        category = categorizer.categorize_tool(tool["name"], tool["description"])
        category_info = categorizer.get_category_info(category)
        print(f"{tool['name']} -> {category_info.name}")
    
    print("\nAfter processing - Available categories:")
    for cat_id, cat_info in categorizer.get_all_categories().items():
        print(f"  {cat_id}: {cat_info.name}")

def main():
    """Run all categorization examples."""
    print("Dynamic Tool Categorization Examples")
    print("====================================")
    
    # Test different business domains
    test_healthcare_tools()
    test_ecommerce_tools()
    test_logistics_tools()
    
    # Test unknown API handling
    test_unknown_apis()
    
    print("\n=== Summary ===")
    print("The Dynamic Tool Categorizer successfully:")
    print("1. Handles domain-specific categories for healthcare, e-commerce, and logistics")
    print("2. Automatically creates new categories for unknown API patterns")
    print("3. Maintains priority-based organization")
    print("4. Provides extensible framework for any business domain")

if __name__ == "__main__":
    main()