import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class ToolCategory:
    """Represents a tool category with metadata."""
    name: str
    description: str
    keywords: List[str]
    priority: int = 0  # Higher priority categories are checked first

class DynamicToolCategorizer:
    """Dynamic tool categorization system that can handle various OpenAPI specifications."""
    
    def __init__(self):
        # Default categories - can be extended dynamically
        self.categories = {
            "authentication": ToolCategory(
                name="Authentication & Security",
                description="Tools for authentication, credentials, and security operations",
                keywords=["auth", "login", "credential", "token", "security", "permission"],
                priority=100
            ),
            "financial_cash": ToolCategory(
                name="Cash Management",
                description="Tools for cash transactions, payments, and cash positions",
                keywords=["cash", "payment", "transaction", "balance", "settlement"],
                priority=90
            ),
            "financial_securities": ToolCategory(
                name="Securities & Trading",
                description="Tools for securities, portfolios, trades, and positions",
                keywords=["securities", "portfolio", "trade", "position", "stock", "bond"],
                priority=90
            ),
            "financial_cls": ToolCategory(
                name="CLS Settlement",
                description="Tools for Continuous Linked Settlement operations",
                keywords=["cls", "settlement", "clearing"],
                priority=90
            ),
            "communication": ToolCategory(
                name="Communication & Messaging",
                description="Tools for messages, notifications, and communication",
                keywords=["message", "mailbox", "notification", "alert", "email"],
                priority=80
            ),
            "data_analytics": ToolCategory(
                name="Data & Analytics",
                description="Tools for data analysis, reporting, and insights",
                keywords=["report", "analytics", "data", "insight", "metric", "dashboard"],
                priority=70
            ),
            "workflow": ToolCategory(
                name="Workflow & Process",
                description="Tools for workflow management and business processes",
                keywords=["workflow", "process", "approval", "task", "step"],
                priority=60
            ),
            "integration": ToolCategory(
                name="Integration & External APIs",
                description="Tools for external system integration and API calls",
                keywords=["api", "external", "integration", "webhook", "sync"],
                priority=50
            ),
            "utility": ToolCategory(
                name="Utility & System",
                description="General utility tools and system operations",
                keywords=["util", "system", "config", "health", "status"],
                priority=40
            )
        }
    
    def add_category(self, category_id: str, category: ToolCategory):
        """Add a new category to the categorizer."""
        self.categories[category_id] = category
    
    def categorize_tool(self, tool_name: str, tool_description: str = "") -> str:
        """Categorize a tool based on its name and description."""
        # Combine name and description for analysis
        text_to_analyze = f"{tool_name} {tool_description}".lower()
        
        # Sort categories by priority (highest first)
        sorted_categories = sorted(
            self.categories.items(), 
            key=lambda x: x[1].priority, 
            reverse=True
        )
        
        # Check each category's keywords
        for category_id, category in sorted_categories:
            for keyword in category.keywords:
                if keyword in text_to_analyze:
                    return category_id
        
        # Try to extract API prefix pattern (e.g., "cash_api_", "user_mgmt_")
        api_match = re.match(r'^([a-zA-Z]+)_api_', tool_name)
        if api_match:
            api_prefix = api_match.group(1)
            # Create dynamic category for unknown API prefixes
            dynamic_category_id = f"api_{api_prefix}"
            if dynamic_category_id not in self.categories:
                self.add_category(
                    dynamic_category_id,
                    ToolCategory(
                        name=f"{api_prefix.title()} API",
                        description=f"Tools for {api_prefix} API operations",
                        keywords=[api_prefix],
                        priority=75
                    )
                )
            return dynamic_category_id
        
        # Try to extract domain from tool name patterns
        domain_patterns = [
            (r'.*_(user|account|profile)_.*', 'user_management'),
            (r'.*_(order|booking|reservation)_.*', 'order_management'),
            (r'.*_(inventory|stock|item)_.*', 'inventory_management'),
            (r'.*_(customer|client|contact)_.*', 'customer_management'),
            (r'.*_(product|catalog|item)_.*', 'product_management'),
            (r'.*_(billing|invoice|charge)_.*', 'billing_management'),
        ]
        
        for pattern, domain in domain_patterns:
            if re.match(pattern, tool_name.lower()):
                dynamic_category_id = domain
                if dynamic_category_id not in self.categories:
                    domain_name = domain.replace('_', ' ').title()
                    self.add_category(
                        dynamic_category_id,
                        ToolCategory(
                            name=domain_name,
                            description=f"Tools for {domain_name.lower()} operations",
                            keywords=[domain.split('_')[0]],
                            priority=65
                        )
                    )
                return dynamic_category_id
        
        # Default to utility category
        return "utility"
    
    def get_category_info(self, category_id: str) -> Optional[ToolCategory]:
        """Get information about a specific category."""
        return self.categories.get(category_id)
    
    def get_all_categories(self) -> Dict[str, ToolCategory]:
        """Get all available categories."""
        return self.categories.copy()
    
    def categorize_tools(self, tools: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize a list of tools and return them grouped by category."""
        categorized = {}
        
        for tool in tools:
            tool_name = tool.get('name', '')
            tool_description = tool.get('description', '')
            category_id = self.categorize_tool(tool_name, tool_description)
            
            if category_id not in categorized:
                categorized[category_id] = []
            
            categorized[category_id].append({
                **tool,
                'category_id': category_id,
                'category_name': self.categories[category_id].name
            })
        
        return categorized
    
    def build_categorized_description(self, tools: List[Dict[str, Any]]) -> str:
        """Build a categorized description of tools for LLM consumption."""
        categorized = self.categorize_tools(tools)
        
        # Sort categories by priority
        sorted_categories = sorted(
            categorized.items(),
            key=lambda x: self.categories[x[0]].priority,
            reverse=True
        )
        
        result = []
        for category_id, category_tools in sorted_categories:
            category = self.categories[category_id]
            result.append(f"\n{category.name}:")
            result.append(f"  {category.description}")
            
            for tool in category_tools:
                desc = f"  • {tool['name']}: {tool.get('description', 'No description')}"
                
                # Add parameter information if available
                input_schema = tool.get('inputSchema', {})
                if input_schema and 'properties' in input_schema:
                    props = input_schema['properties']
                    if props:
                        param_details = []
                        for param_name, param_info in props.items():
                            param_type = param_info.get('type', 'string')
                            param_desc = param_info.get('description', '')
                            if param_desc:
                                param_details.append(f"{param_name} ({param_type}): {param_desc}")
                            else:
                                param_details.append(f"{param_name} ({param_type})")
                        
                        if param_details:
                            desc += f"\n    Parameters: {'; '.join(param_details)}"
                
                result.append(desc)
        
        return '\n'.join(result)

# Example usage and testing
if __name__ == "__main__":
    categorizer = DynamicToolCategorizer()
    
    # Test with sample tools
    sample_tools = [
        {"name": "cash_api_getPayments", "description": "Get all cash payments"},
        {"name": "securities_api_getPortfolio", "description": "Get portfolio information"},
        {"name": "user_mgmt_createUser", "description": "Create a new user account"},
        {"name": "inventory_api_getStock", "description": "Get current stock levels"},
        {"name": "login", "description": "Authenticate user credentials"},
        {"name": "generate_report", "description": "Generate analytics report"},
        {"name": "unknown_tool", "description": "Some unknown functionality"}
    ]
    
    print("=== Tool Categorization Test ===")
    for tool in sample_tools:
        category = categorizer.categorize_tool(tool["name"], tool["description"])
        category_info = categorizer.get_category_info(category)
        print(f"{tool['name']} -> {category_info.name}")
    
    print("\n=== Categorized Description ===")
    print(categorizer.build_categorized_description(sample_tools))