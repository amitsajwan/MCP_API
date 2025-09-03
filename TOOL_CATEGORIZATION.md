# Dynamic Tool Categorization System

This document explains the enhanced tool categorization system that dynamically handles different OpenAPI specifications and tool domains.

## Problem Statement

The original system used hardcoded keyword matching to categorize tools, which had limitations:
- Only worked with predefined financial API categories
- Couldn't handle new or unknown OpenAPI specifications
- Required manual updates for each new API domain
- Limited flexibility for different business domains

## Solution: Dynamic Tool Categorizer

The new `DynamicToolCategorizer` class provides:

### 1. **Flexible Category System**
- Predefined categories with priority levels
- Dynamic category creation for unknown API patterns
- Extensible keyword-based matching
- Domain pattern recognition

### 2. **Multi-Level Categorization Strategy**

The categorizer uses a hierarchical approach:

#### Level 1: Priority-Based Keyword Matching
```python
categories = {
    "authentication": ToolCategory(
        name="Authentication & Security",
        keywords=["auth", "login", "credential", "token"],
        priority=100
    ),
    "financial_cash": ToolCategory(
        name="Cash Management",
        keywords=["cash", "payment", "transaction"],
        priority=90
    ),
    # ... more categories
}
```

#### Level 2: API Prefix Pattern Detection
- Detects patterns like `cash_api_`, `user_mgmt_`, `inventory_api_`
- Automatically creates new categories for unknown prefixes
- Example: `inventory_api_getStock` → Creates "Inventory API" category

#### Level 3: Domain Pattern Recognition
- Recognizes common business domain patterns:
  - `*_user_*` → User Management
  - `*_order_*` → Order Management
  - `*_inventory_*` → Inventory Management
  - `*_customer_*` → Customer Management
  - `*_billing_*` → Billing Management

#### Level 4: Fallback to Utility
- Unknown tools default to "Utility & System" category

### 3. **Usage Examples**

#### Basic Categorization
```python
from tool_categorizer import DynamicToolCategorizer

categorizer = DynamicToolCategorizer()

# Categorize individual tools
category = categorizer.categorize_tool(
    "cash_api_getPayments", 
    "Get all cash payments"
)
print(category)  # Output: "financial_cash"
```

#### Batch Categorization
```python
tools = [
    {"name": "cash_api_getPayments", "description": "Get payments"},
    {"name": "user_mgmt_createUser", "description": "Create user"},
    {"name": "login", "description": "Authenticate user"}
]

categorized = categorizer.categorize_tools(tools)
# Returns tools grouped by category
```

#### Adding Custom Categories
```python
from tool_categorizer import ToolCategory

# Add a new category for HR tools
categorizer.add_category(
    "hr_management",
    ToolCategory(
        name="Human Resources",
        description="Tools for HR and employee management",
        keywords=["employee", "hr", "payroll", "benefits"],
        priority=85
    )
)
```

### 4. **Integration with MCP Client**

The MCP client now uses the dynamic categorizer in `_build_enhanced_tools_description()`:

```python
def _build_enhanced_tools_description(self) -> str:
    # Convert MCP tools to dict format
    tools_dict = [{
        'name': tool.name,
        'description': tool.description,
        'inputSchema': tool.inputSchema
    } for tool in self.available_tools]
    
    # Use dynamic categorizer
    categorized = self.tool_categorizer.categorize_tools(tools_dict)
    
    # Build prioritized description
    # Categories are sorted by priority (highest first)
```

### 5. **Benefits**

#### For Different OpenAPI Specifications
- **Financial APIs**: `cash_api_*`, `securities_api_*`, `cls_api_*`
- **E-commerce APIs**: `product_api_*`, `order_api_*`, `inventory_api_*`
- **User Management APIs**: `user_mgmt_*`, `auth_api_*`
- **Custom APIs**: Any `*_api_*` pattern creates dynamic categories

#### For LLM Tool Selection
- **Prioritized presentation**: High-priority tools (auth, financial) shown first
- **Contextual grouping**: Related tools grouped together
- **Clear descriptions**: Each category has descriptive metadata
- **Parameter details**: Full parameter information included

#### For System Extensibility
- **No code changes needed**: New APIs automatically categorized
- **Custom categories**: Easy to add domain-specific categories
- **Pattern recognition**: Learns from tool naming conventions
- **Backward compatible**: Works with existing tool structures

### 6. **Example Output**

The categorizer produces organized tool descriptions like:

```
Authentication & Security:
  Tools for authentication, credentials, and security operations
  • login: Authenticate user credentials
  • getCredentials: Retrieve stored credentials

Cash Management:
  Tools for cash transactions, payments, and cash positions
  • cash_api_getPayments: Get all cash payments
    Parameters: status (string): Filter by payment status; date_from (string): Start date
  • cash_api_createPayment: Create a new payment
    Parameters: amount (number): Payment amount; recipient (string): Payment recipient

Securities & Trading:
  Tools for securities, portfolios, trades, and positions
  • securities_api_getPortfolio: Get portfolio information
  • securities_api_executeTrade: Execute a securities trade

Inventory API:  # Dynamically created category
  Tools for inventory API operations
  • inventory_api_getStock: Get current stock levels
  • inventory_api_updateStock: Update stock quantities
```

### 7. **Configuration and Customization**

The system can be customized for different business domains:

```python
# For healthcare domain
categorizer.add_category("healthcare", ToolCategory(
    name="Healthcare & Medical",
    description="Tools for patient management and medical operations",
    keywords=["patient", "medical", "diagnosis", "treatment"],
    priority=95
))

# For logistics domain
categorizer.add_category("logistics", ToolCategory(
    name="Logistics & Shipping",
    description="Tools for shipping, tracking, and logistics",
    keywords=["shipping", "tracking", "logistics", "delivery"],
    priority=85
))
```

## Conclusion

The Dynamic Tool Categorization System solves the original problem by:

1. **Handling any OpenAPI specification** - No manual configuration needed
2. **Learning from naming patterns** - Automatically creates categories
3. **Prioritizing tool presentation** - Important tools shown first
4. **Maintaining flexibility** - Easy to extend and customize
5. **Improving LLM performance** - Better organized tool descriptions

This system can handle financial APIs, e-commerce APIs, healthcare APIs, or any other domain without requiring code changes, making it truly dynamic and extensible.