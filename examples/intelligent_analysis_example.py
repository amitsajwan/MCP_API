#!/usr/bin/env python3
"""
Example: Intelligent API Analysis
Demonstrates how to use IntelligentAPIAnalyzer with MCP protocol
"""

import asyncio
import json
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.intelligent_api_analyzer import IntelligentAPIAnalyzer
from core.mcp_client_connector import MCPClientConnector
from external.vector_store import VectorStore
from core.cache_manager import CacheManager
from external.embedding_service import EmbeddingService
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main example function"""
    
    logger.info("🚀 Starting Intelligent API Analysis Example")
    
    try:
        # 1. Initialize components
        logger.info("📋 Initializing components...")
        
        # MCP Client Connector
        mcp_client = MCPClientConnector(["python", "mcp_server_fastmcp.py"])
        
        # Vector Store
        vector_store = VectorStore()
        
        # Cache Manager
        cache_manager = CacheManager()
        
        # Embedding Service (optional)
        embedding_service = EmbeddingService() if settings.azure_openai_api_key else None
        
        # 2. Connect to MCP server
        logger.info("🔌 Connecting to MCP server...")
        connected = await mcp_client.connect()
        
        if not connected:
            logger.error("❌ Failed to connect to MCP server")
            return
        
        logger.info("✅ Connected to MCP server")
        
        # 3. Create Intelligent API Analyzer
        logger.info("🧠 Creating Intelligent API Analyzer...")
        
        analyzer = IntelligentAPIAnalyzer(
            mcp_client_connector=mcp_client,
            vector_store=vector_store,
            cache_manager=cache_manager,
            embedding_service=embedding_service
        )
        
        # 4. Analyze tools and generate use cases
        logger.info("🔍 Analyzing MCP tools and generating use cases...")
        
        analysis = await analyzer.analyze_and_generate_use_cases()
        
        if "error" in analysis:
            logger.error(f"❌ Analysis failed: {analysis['error']}")
            return
        
        # 5. Test Query Router (Hybrid Intelligence)
        logger.info("🔀 Testing Query Router...")
        
        # Create Query Router
        from core.query_router import QueryRouter, HybridQueryProcessor
        query_router = QueryRouter(vector_store, analyzer.use_case_library)
        
        # Test query routing
        test_queries = [
            "Show me payment analysis",
            "Create financial dashboard", 
            "Analyze cash flow",
            "Get portfolio summary"
        ]
        
        print("\n" + "="*80)
        print("🎯 HYBRID INTELLIGENCE ENGINE RESULTS")
        print("="*80)
        
        print(f"\n🔀 Query Routing Tests:")
        for query in test_queries:
            query_plan = await query_router.route_query(query)
            print(f"   Query: '{query}'")
            print(f"   Pipeline: {query_plan.plan_type.value}")
            print(f"   Confidence: {query_plan.confidence:.2f}")
            if hasattr(query_plan, 'use_case_id'):
                print(f"   Use Case ID: {query_plan.use_case_id}")
            if hasattr(query_plan, 'similarity'):
                print(f"   Similarity: {query_plan.similarity:.3f}")
            print()
        
        # Get routing statistics
        routing_stats = query_router.get_routing_statistics()
        print(f"📊 Query Routing Statistics:")
        print(f"   Total Queries: {routing_stats['total_queries']}")
        print(f"   Pre-Analyzed Routes: {routing_stats['pre_analyzed_routes']} ({routing_stats['pre_analyzed_percentage']:.1f}%)")
        print(f"   Adaptive Routes: {routing_stats['adaptive_routes']} ({routing_stats['adaptive_percentage']:.1f}%)")
        print(f"   Cache Hit Rate: {routing_stats['cache_hit_rate']:.1f}%")
        print(f"   Average Similarity: {routing_stats['average_similarity']:.3f}")
        
        # 6. Display Analysis Results
        logger.info("📊 Analysis Results:")
        print(f"\n📚 Use Case Library:")
        print(f"   Total Use Cases: {len(analyzer.use_case_library)}")
        library_stats = analyzer.get_use_case_library_stats()
        print(f"   Categories: {', '.join(library_stats['categories'])}")
        print(f"   Total Executions: {library_stats['execution_stats']['total_executions']}")
        print(f"   Average Success Rate: {library_stats['execution_stats']['average_success_rate']:.2%}")
        
        # Analysis Summary
        summary = analysis["analysis_summary"]
        print(f"\n📈 Analysis Summary:")
        print(f"   • Total Tools Analyzed: {summary['total_tools_analyzed']}")
        print(f"   • Categories: {list(summary['categories'].keys())}")
        print(f"   • Cache Coverage: {summary['cache_coverage']}")
        print(f"   • Generated Use Cases: {summary['generated_use_cases']}")
        
        # Tool Metadata
        print(f"\n🔧 Tool Metadata:")
        for tool_name, metadata in analysis["tool_metadata"].items():
            print(f"   • {tool_name}:")
            print(f"     - Purpose: {metadata['inferred_purpose']}")
            print(f"     - Category: {metadata['category']}")
            print(f"     - Cache Strategy: {metadata['cache_strategy']}")
            print(f"     - Business Value: {metadata['business_value']}")
            print(f"     - Complexity: {metadata['complexity_score']}/10")
        
        # Dependencies
        print(f"\n🔗 Tool Dependencies:")
        for tool_name, deps in analysis["dependencies"].items():
            if deps:
                print(f"   • {tool_name} depends on:")
                for dep in deps:
                    print(f"     - {dep['provider_tool']} (confidence: {dep['confidence']:.2f})")
        
        # Cache Opportunities
        print(f"\n💾 Cache Opportunities:")
        high_value_targets = analysis["cache_opportunities"]["high_value_cache_targets"]
        for target in high_value_targets:
            print(f"   • {target['tool']}: {target['reason']}")
            print(f"     - Strategy: {target['cache_strategy']}")
            print(f"     - Estimated Hit Rate: {target['estimated_hit_rate']:.1%}")
        
        # Generated Use Cases
        print(f"\n🎯 Generated Use Cases:")
        for use_case in analysis["generated_use_cases"]:
            print(f"   • {use_case['name']}:")
            print(f"     - Category: {use_case['category']}")
            print(f"     - Tools: {', '.join(use_case['tools'])}")
            print(f"     - Business Value: {use_case['business_value']}")
            print(f"     - Complexity: {use_case['complexity']}")
            print(f"     - Cache Benefits: {use_case['cache_benefits']}")
        
        # 6. Test query analysis
        logger.info("🔍 Testing query analysis...")
        
        test_queries = [
            "Show me payment analysis",
            "Create financial dashboard",
            "Analyze cash flow",
            "Get portfolio summary"
        ]
        
        print(f"\n🔍 Query Analysis Tests:")
        for query in test_queries:
            query_analysis = await analyzer.get_analysis_for_query(query)
            
            if "error" not in query_analysis:
                relevant_tools = query_analysis["relevant_tools"]
                relevant_use_cases = query_analysis["relevant_use_cases"]
                
                print(f"\n   Query: '{query}'")
                print(f"   Relevant Tools: {len(relevant_tools)} found")
                print(f"   Relevant Use Cases: {len(relevant_use_cases)} found")
                
                if relevant_tools:
                    print(f"   Top Tool: {relevant_tools[0]['metadata']['tool_name']}")
                if relevant_use_cases:
                    print(f"   Top Use Case: {relevant_use_cases[0]['metadata'].get('use_case_id', 'Unknown')}")
        
        # 7. Vector database statistics
        logger.info("📊 Vector database statistics...")
        
        vector_stats = vector_store.get_statistics()
        print(f"\n💾 Vector Database Statistics:")
        print(f"   • Total Vectors: {vector_stats['total_vectors']}")
        print(f"   • Memory Usage: {vector_stats['memory_usage_mb']:.2f} MB")
        print(f"   • Average Similarity: {vector_stats['average_similarity']:.3f}")
        
        # 8. Cleanup
        logger.info("🧹 Cleaning up...")
        await mcp_client.disconnect()
        
        print("\n" + "="*80)
        print("✅ INTELLIGENT API ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*80)
        
        logger.info("✅ Example completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")
        raise


async def demonstrate_use_case_execution():
    """Demonstrate how to use generated use cases"""
    
    logger.info("🎯 Demonstrating use case execution...")
    
    # This would be integrated with your adaptive orchestrator
    # For now, just show the concept
    
    example_use_case = {
        "name": "Payment Analysis",
        "tools": ["getPayments", "getTransactions"],
        "execution_plan": [
            {
                "step_number": 1,
                "tool": "getPayments",
                "cache_strategy": "cache_full_response"
            },
            {
                "step_number": 2,
                "tool": "python_manipulation",
                "code": """
def analyze_payments(cached_data):
    payments = cached_data.get('payments', [])
    return {
        "total_payments": len(payments),
        "total_amount": sum(p.get('amount', 0) for p in payments)
    }
                """
            }
        ]
    }
    
    print(f"\n🎯 Use Case Execution Example:")
    print(f"   Use Case: {example_use_case['name']}")
    print(f"   Tools: {', '.join(example_use_case['tools'])}")
    print(f"   Steps: {len(example_use_case['execution_plan'])}")
    
    for step in example_use_case['execution_plan']:
        print(f"   Step {step['step_number']}: {step['tool']}")
        if 'cache_strategy' in step:
            print(f"     Cache Strategy: {step['cache_strategy']}")


if __name__ == "__main__":
    print("🚀 Intelligent API Analysis Example")
    print("This example demonstrates the IntelligentAPIAnalyzer capabilities")
    print()
    
    # Run main example
    asyncio.run(main())
    
    # Run use case execution demo
    asyncio.run(demonstrate_use_case_execution())
