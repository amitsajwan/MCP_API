#!/usr/bin/env python3
"""
Demo Dependency Concept
======================
Simple demonstration of the dependency-aware concept without MCP complexity.
"""

import json

class SimpleDependencyDemo:
    """Simple demo of dependency-aware tool behavior"""
    
    def __init__(self):
        self.mock_data = {
            'users': [
                {'id': 'user_1', 'name': 'John Doe', 'email': 'john@example.com'},
                {'id': 'user_2', 'name': 'Jane Smith', 'email': 'jane@example.com'}
            ],
            'accounts': [
                {'id': 'acc_1', 'user_id': 'user_1', 'name': 'Personal Account', 'type': 'checking'},
                {'id': 'acc_2', 'user_id': 'user_1', 'name': 'Business Account', 'type': 'business'},
                {'id': 'acc_3', 'user_id': 'user_2', 'name': 'Savings Account', 'type': 'savings'}
            ],
            'mails': [
                {'id': 'mail_1', 'account_id': 'acc_1', 'subject': 'Welcome Email', 'from': 'system@bank.com'},
                {'id': 'mail_2', 'account_id': 'acc_1', 'subject': 'Account Statement', 'from': 'statements@bank.com'},
                {'id': 'mail_3', 'account_id': 'acc_2', 'subject': 'Business Update', 'from': 'business@bank.com'},
                {'id': 'mail_4', 'account_id': 'acc_3', 'subject': 'Interest Rate Change', 'from': 'rates@bank.com'}
            ]
        }
    
    def get_users(self):
        """Get all users"""
        return {
            "status": "success",
            "data": self.mock_data['users'],
            "message": "Users retrieved successfully"
        }
    
    def get_accounts(self, user_id=None):
        """Get accounts, optionally filtered by user_id"""
        accounts = self.mock_data['accounts']
        if user_id:
            accounts = [acc for acc in accounts if acc['user_id'] == user_id]
        
        return {
            "status": "success",
            "data": accounts,
            "message": f"Found {len(accounts)} accounts"
        }
    
    def get_mails(self, account_id=None, user_id=None):
        """
        Get emails for a specific account.
        
        DEPENDENCIES:
        - account_id: Required parameter that must be obtained from getAccounts
        - user_id: Optional, if provided will get accounts for user first
        """
        
        # Check dependencies
        if not account_id and not user_id:
            return {
                "status": "prerequisite_required",
                "message": "account_id is required to get emails",
                "prerequisite": {
                    "operation": "getAccounts",
                    "purpose": "Get account_id for email retrieval",
                    "description": "Call getAccounts first to obtain the account_id needed for getMails"
                },
                "suggested_workflow": [
                    "1. Call getAccounts() to get available accounts",
                    "2. Select account_id from the results", 
                    "3. Call getMails(account_id='acc_123') with the selected account_id"
                ],
                "example_usage": "getAccounts() → getMails(account_id='acc_123')"
            }
        
        # If user_id provided but no account_id, get accounts first
        if user_id and not account_id:
            accounts = [acc for acc in self.mock_data['accounts'] if acc['user_id'] == user_id]
            return {
                "status": "accounts_found",
                "message": f"Found {len(accounts)} accounts for user {user_id}",
                "accounts": accounts,
                "next_step": "Call getMails with account_id from the accounts above",
                "example": f"getMails(account_id='{accounts[0]['id'] if accounts else 'acc_1'}')"
            }
        
        # Get emails for the account
        mails = [mail for mail in self.mock_data['mails'] if mail['account_id'] == account_id]
        
        return {
            "status": "success",
            "data": mails,
            "message": f"Found {len(mails)} emails for account {account_id}",
            "account_id": account_id
        }
    
    def get_mails_smart(self, account_identifier=None, user_identifier=None):
        """
        Smart email retrieval that can resolve dependencies automatically.
        """
        
        # No identifiers provided - show available options
        if not account_identifier and not user_identifier:
            return {
                "status": "identifiers_required",
                "message": "Please provide account_identifier or user_identifier",
                "available_options": {
                    "users": self.mock_data['users'],
                    "accounts": self.mock_data['accounts']
                },
                "examples": [
                    "get_mails_smart(account_identifier='acc_1')",
                    "get_mails_smart(user_identifier='user_1')",
                    "get_mails_smart(account_identifier='Personal Account')"
                ]
            }
        
        # Try to resolve account_id
        account_id = None
        
        if account_identifier:
            # Check if it's a direct account_id
            if account_identifier.startswith('acc_'):
                account_id = account_identifier
            else:
                # Try to find by account name
                for acc in self.mock_data['accounts']:
                    if acc['name'].lower() == account_identifier.lower():
                        account_id = acc['id']
                        break
                
                # If not found by name, might be user_id
                if not account_id:
                    for acc in self.mock_data['accounts']:
                        if acc['user_id'] == account_identifier:
                            account_id = acc['id']
                            break
        
        # If user_identifier provided, get accounts for that user
        if user_identifier and not account_id:
            user_accounts = []
            for acc in self.mock_data['accounts']:
                if acc['user_id'] == user_identifier:
                    user_accounts.append(acc)
            
            if user_accounts:
                return {
                    "status": "user_accounts_found",
                    "message": f"Found {len(user_accounts)} accounts for user {user_identifier}",
                    "accounts": user_accounts,
                    "next_step": "Call get_mails_smart with account_identifier from the accounts above",
                    "example": f"get_mails_smart(account_identifier='{user_accounts[0]['id']}')"
                }
        
        # Get emails for the resolved account
        if account_id:
            mails = [mail for mail in self.mock_data['mails'] if mail['account_id'] == account_id]
            return {
                "status": "success",
                "data": mails,
                "message": f"Found {len(mails)} emails for account {account_id}",
                "account_id": account_id,
                "dependency_resolved": True
            }
        else:
            return {
                "status": "account_not_found",
                "message": f"Could not resolve account for identifier: {account_identifier}",
                "available_accounts": self.mock_data['accounts']
            }

def demo_flow():
    """Demonstrate the dependency flow"""
    
    print("🎯 Dependency-Aware Tool Demo")
    print("=" * 40)
    
    demo = SimpleDependencyDemo()
    
    print("\n📞 Scenario 1: User asks 'Get my emails'")
    print("-" * 30)
    result = demo.get_mails()
    print("Result:", json.dumps(result, indent=2))
    
    print("\n📞 Scenario 2: MCP Client gets accounts first")
    print("-" * 30)
    result = demo.get_accounts()
    print("Result:", json.dumps(result, indent=2))
    
    print("\n📞 Scenario 3: MCP Client calls getMails with account_id")
    print("-" * 30)
    result = demo.get_mails(account_id="acc_1")
    print("Result:", json.dumps(result, indent=2))
    
    print("\n📞 Scenario 4: Smart tool with user_id")
    print("-" * 30)
    result = demo.get_mails_smart(user_identifier="user_1")
    print("Result:", json.dumps(result, indent=2))
    
    print("\n📞 Scenario 5: Smart tool with account name")
    print("-" * 30)
    result = demo.get_mails_smart(account_identifier="Personal Account")
    print("Result:", json.dumps(result, indent=2))
    
    print("\n📞 Scenario 6: Smart tool without parameters")
    print("-" * 30)
    result = demo.get_mails_smart()
    print("Result:", json.dumps(result, indent=2))

def show_workflow():
    """Show the complete workflow"""
    
    print("\n🔄 Complete Workflow Example")
    print("=" * 30)
    
    print("User Query: 'Get my emails'")
    print()
    
    print("Step 1: MCP Client calls get_mails() without parameters")
    print("Result: Prerequisite required - need account_id")
    print()
    
    print("Step 2: MCP Client calls get_accounts() to get available accounts")
    print("Result: Returns list of accounts with IDs")
    print()
    
    print("Step 3: MCP Client calls get_mails(account_id='acc_1')")
    print("Result: Returns emails for the specified account")
    print()
    
    print("Alternative: MCP Client calls get_mails_smart(user_identifier='user_1')")
    print("Result: Smart tool resolves dependency and returns emails")
    print()
    
    print("🎯 Key Benefits:")
    print("- Tools understand their dependencies")
    print("- MCP Client gets clear guidance on prerequisites")
    print("- Smart tools can resolve dependencies automatically")
    print("- No more 'missing parameter' errors")

if __name__ == "__main__":
    demo_flow()
    show_workflow()