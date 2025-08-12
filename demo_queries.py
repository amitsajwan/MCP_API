#!/usr/bin/env python3
"""
Demo Queries for the Financial API Chatbot

This file contains example queries that users can try in the web interface
to demonstrate the capabilities of the OpenAPI MCP Server.
"""

DEMO_QUERIES = {
    "Payment & Cash Management": [
        "Show me all pending payments that need approval",
        "What's my current cash balance?",
        "List all payments made this month",
        "Show me payments over $10,000",
        "Get cash summary for the last 7 days",
        "Which payments are pending approval?",
        "Show me rejected payments",
        "What's the total amount of pending payments?"
    ],
    
    "Securities & Portfolio": [
        "What's my current portfolio value?",
        "Show me my portfolio positions",
        "List recent securities trades",
        "What's my biggest holding?",
        "Show me securities summary",
        "Get my trading history",
        "What securities do I own?",
        "Show me portfolio performance"
    ],
    
    "CLS Settlements": [
        "Are there any CLS settlements pending?",
        "Show me CLS settlement status",
        "Get clearing status",
        "Check risk metrics",
        "List pending settlement instructions",
        "Show me CLS positions",
        "What's the CLS summary?",
        "Are there any settlement issues?"
    ],
    
    "Mailbox & Notifications": [
        "Do I have any unread messages?",
        "Show me recent notifications",
        "List active alerts",
        "Check mailbox summary",
        "Show me urgent messages",
        "What notifications do I have?",
        "Are there any alerts that need attention?",
        "Show me archived messages"
    ],
    
    "Financial Summaries": [
        "Give me a summary of all financial activities",
        "What's my overall financial position?",
        "Show me a comprehensive financial summary",
        "Get summary for this month",
        "What's my total financial exposure?",
        "Show me all pending approvals",
        "Give me an overview of all systems",
        "What needs my attention today?"
    ],
    
    "Cross-System Queries": [
        "What's my total financial position across all systems?",
        "Show me everything that needs approval",
        "What's my risk exposure across all portfolios?",
        "Give me a complete financial overview",
        "What are my biggest financial concerns?",
        "Show me all pending items across systems",
        "What's my total cash and securities value?",
        "Are there any issues across all systems?"
    ]
}

def print_demo_queries():
    """Print all demo queries in a formatted way"""
    print("🎯 Demo Queries for Financial API Chatbot")
    print("=" * 60)
    print("Try these queries in the web interface at http://localhost:8080")
    print()
    
    for category, queries in DEMO_QUERIES.items():
        print(f"📋 {category}")
        print("-" * 40)
        for i, query in enumerate(queries, 1):
            print(f"{i:2d}. {query}")
        print()
    
    print("💡 Tips:")
    print("- Use natural language - the system understands context")
    print("- Be specific for better results")
    print("- Try combining different aspects (payments + approvals)")
    print("- Ask for summaries to get overview information")

def get_random_queries(count=5):
    """Get a random selection of queries for testing"""
    import random
    all_queries = []
    for queries in DEMO_QUERIES.values():
        all_queries.extend(queries)
    
    return random.sample(all_queries, min(count, len(all_queries)))

def get_queries_by_category(category):
    """Get queries for a specific category"""
    return DEMO_QUERIES.get(category, [])

if __name__ == "__main__":
    print_demo_queries()
    
    print("\n🎲 Random Sample Queries:")
    print("-" * 30)
    for i, query in enumerate(get_random_queries(5), 1):
        print(f"{i}. {query}")
