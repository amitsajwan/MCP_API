"""
Streamlit App for Demo MCP System
Main application entry point
"""

import streamlit as st
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import core modules
from core import CacheManager, UseCaseManager, BotManager, MCPToolsManager, AdaptiveOrchestrator
from external import AzureClient, VectorStore, EmbeddingService
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Demo MCP System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .use-case-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 5px solid #1f77b4;
    }
    .tool-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #dee2e6;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .user-message {
        background: #007bff;
        color: white;
        margin-left: 20%;
    }
    .bot-message {
        background: #e9ecef;
        color: #333;
        margin-right: 20%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    """Initialize session state variables"""
    if 'cache_manager' not in st.session_state:
        st.session_state.cache_manager = CacheManager()
    if 'use_case_manager' not in st.session_state:
        st.session_state.use_case_manager = UseCaseManager()
    if 'bot_manager' not in st.session_state:
        st.session_state.bot_manager = BotManager()
    if 'mcp_tools_manager' not in st.session_state:
        st.session_state.mcp_tools_manager = MCPToolsManager()
    if 'azure_client' not in st.session_state:
        st.session_state.azure_client = AzureClient()
    if 'vector_store' not in st.session_state:
        st.session_state.vector_store = VectorStore()
    if 'embedding_service' not in st.session_state:
        st.session_state.embedding_service = EmbeddingService()
    if 'adaptive_orchestrator' not in st.session_state:
        st.session_state.adaptive_orchestrator = AdaptiveOrchestrator()
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

def main():
    """Main Streamlit application"""
    initialize_session_state()
    
    st.markdown('<h1 class="main-header">🚀 Demo MCP System</h1>', unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Home", "MCP Tools", "Use Cases", "Bot Chat", "Adaptive Query", "Cache Management", "System Status"]
    )
    
    # Sidebar stats
    st.sidebar.markdown("---")
    st.sidebar.markdown("### System Stats")
    cache_stats = st.session_state.cache_manager.get_cache_stats()
    st.sidebar.metric("Total Cache", cache_stats['total_cache_size'])
    st.sidebar.metric("Workflow Cache", cache_stats['workflow_cache_size'])
    st.sidebar.metric("User Cache", cache_stats['user_cache_size'])
    st.sidebar.metric("Use Case Cache", cache_stats['use_case_cache_size'])
    
    # Azure status
    azure_status = st.session_state.azure_client.get_status()
    st.sidebar.markdown("### Azure Status")
    st.sidebar.metric("Available", "✅" if azure_status['available'] else "❌")
    
    # Page routing
    if page == "Home":
        show_home_page()
    elif page == "MCP Tools":
        show_mcp_tools_page()
    elif page == "Use Cases":
        show_use_cases_page()
    elif page == "Bot Chat":
        show_bot_chat_page()
    elif page == "Adaptive Query":
        show_adaptive_query_page()
    elif page == "Cache Management":
        show_cache_management_page()
    elif page == "System Status":
        show_system_status_page()

def show_home_page():
    """Display home page"""
    st.markdown("## Welcome to the Demo MCP System")
    st.markdown("This system demonstrates intelligent API orchestration with MCP tools, use cases, and bot interactions.")
    
    # System overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("MCP Tools", len(st.session_state.mcp_tools_manager.get_all_tools()))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Use Cases", len(st.session_state.use_case_manager.get_all_use_cases()))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Cache Entries", st.session_state.cache_manager.get_cache_stats()['total_cache_size'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Session ID", st.session_state.session_id[:8])
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick actions
    st.markdown("## Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔧 View MCP Tools", use_container_width=True):
            st.session_state.page = "MCP Tools"
            st.rerun()
    
    with col2:
        if st.button("📋 View Use Cases", use_container_width=True):
            st.session_state.page = "Use Cases"
            st.rerun()
    
    with col3:
        if st.button("🤖 Chat with Bot", use_container_width=True):
            st.session_state.page = "Bot Chat"
            st.rerun()
    
    # System features
    st.markdown("## System Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔧 MCP Tools")
        st.markdown("- Execute tools with custom parameters")
        st.markdown("- Real-time execution results")
        st.markdown("- Tool categorization and search")
        st.markdown("- Execution history tracking")
    
    with col2:
        st.markdown("### 📋 Use Cases")
        st.markdown("- Pre-defined business workflows")
        st.markdown("- Documentation and flowcharts")
        st.markdown("- Execution with parameters")
        st.markdown("- Cache integration")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("### 🤖 Bot Chat")
        st.markdown("- Intelligent query processing")
        st.markdown("- Context-aware responses")
        st.markdown("- Use case recommendations")
        st.markdown("- Session management")
    
    with col4:
        st.markdown("### 💾 Cache Management")
        st.markdown("- Multi-level caching")
        st.markdown("- TTL-based expiration")
        st.markdown("- Cache statistics")
        st.markdown("- Manual cache control")

def show_mcp_tools_page():
    """Display MCP tools page"""
    st.markdown("## 🔧 MCP Tools")
    st.markdown("Execute MCP tools with custom parameters")
    
    tools = st.session_state.mcp_tools_manager.get_all_tools()
    
    # Tool selection
    selected_tool = st.selectbox("Select a tool", [tool["name"] for tool in tools])
    
    if selected_tool:
        tool_info = st.session_state.mcp_tools_manager.get_tool(selected_tool)
        
        # Display tool info
        st.markdown(f"### {tool_info['name']}")
        st.markdown(f"**Category:** {tool_info['category']}")
        st.markdown(f"**Description:** {tool_info['description']}")
        
        # Parameters input
        st.markdown("#### Parameters")
        parameters = {}
        for param_name, param_type in tool_info['parameters'].items():
            if param_type == "string":
                parameters[param_name] = st.text_input(f"{param_name} ({param_type})", key=f"param_{param_name}")
            elif param_type == "number":
                parameters[param_name] = st.number_input(f"{param_name} ({param_type})", key=f"param_{param_name}")
            elif param_type == "object":
                param_json = st.text_area(f"{param_name} (JSON)", key=f"param_{param_name}")
                try:
                    parameters[param_name] = json.loads(param_json) if param_json else {}
                except:
                    st.error("Invalid JSON format")
        
        # Execute button
        if st.button("Execute Tool", type="primary"):
            with st.spinner("Executing tool..."):
                result = asyncio.run(st.session_state.mcp_tools_manager.execute_tool(selected_tool, parameters))
                
                st.markdown("#### Execution Result")
                st.json(result)
    
    # Tool statistics
    st.markdown("---")
    st.markdown("### Tool Statistics")
    stats = st.session_state.mcp_tools_manager.get_tool_statistics()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Executions", stats.get('total_executions', 0))
    with col2:
        st.metric("Success Rate", f"{stats.get('success_rate', 0):.1%}")
    with col3:
        st.metric("Avg Execution Time", f"{stats.get('average_execution_time', 0):.2f}s")

def show_use_cases_page():
    """Display use cases page"""
    st.markdown("## 📋 Use Cases")
    st.markdown("Explore and execute use cases with documentation and flowcharts")
    
    use_cases = st.session_state.use_case_manager.get_all_use_cases()
    
    # Filter by category
    categories = st.session_state.use_case_manager.get_categories()
    selected_category = st.selectbox("Filter by category", ["All"] + categories)
    
    filtered_cases = use_cases
    if selected_category != "All":
        filtered_cases = [case for case in use_cases if case["category"] == selected_category]
    
    # Display use cases
    for case in filtered_cases:
        with st.container():
            st.markdown('<div class="use-case-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {case['name']}")
                st.markdown(f"**Description:** {case['description']}")
                st.markdown(f"**Category:** {case['category']} | **Complexity:** {case['complexity']} | **Time:** {case['estimated_time']}")
                st.markdown(f"**Tools:** {', '.join(case['tools'])}")
            
            with col2:
                if st.button(f"View Details", key=f"details_{case['id']}"):
                    st.session_state[f"show_case_{case['id']}"] = True
                
                if st.button(f"Execute", key=f"execute_{case['id']}", type="primary"):
                    st.session_state[f"execute_case_{case['id']}"] = True
            
            # Show details if requested
            if st.session_state.get(f"show_case_{case['id']}", False):
                st.markdown("#### Documentation")
                st.markdown(st.session_state.use_case_manager.get_documentation(case['id']))
                
                st.markdown("#### Flowchart")
                st.code(st.session_state.use_case_manager.get_flowchart(case['id']), language="mermaid")
            
            # Execute if requested
            if st.session_state.get(f"execute_case_{case['id']}", False):
                st.markdown("#### Execute Use Case")
                
                # Parameters input
                parameters = {}
                for i, tool in enumerate(case['tools']):
                    tool_info = st.session_state.mcp_tools_manager.get_tool(tool)
                    if tool_info:
                        st.markdown(f"**{tool} parameters:**")
                        for param_name, param_type in tool_info['parameters'].items():
                            if param_type == "string":
                                parameters[f"{tool}_{param_name}"] = st.text_input(f"{param_name}", key=f"exec_{case['id']}_{tool}_{param_name}")
                            elif param_type == "number":
                                parameters[f"{tool}_{param_name}"] = st.number_input(f"{param_name}", key=f"exec_{case['id']}_{tool}_{param_name}")
                
                if st.button(f"Execute {case['name']}", key=f"exec_btn_{case['id']}", type="primary"):
                    with st.spinner("Executing use case..."):
                        result = asyncio.run(st.session_state.use_case_manager.execute_use_case(case['id'], parameters))
                        
                        st.markdown("#### Execution Result")
                        st.json(result)
                
                # Reset execution flag
                st.session_state[f"execute_case_{case['id']}"] = False
            
            st.markdown('</div>', unsafe_allow_html=True)

def show_bot_chat_page():
    """Display bot chat page"""
    st.markdown("## 🤖 Bot Chat")
    st.markdown("Chat with the intelligent bot that can help with use cases and tools")
    
    # Chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message">👤 {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message bot-message">🤖 {message["content"]}</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.text_input("Ask me anything...", key="chat_input")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Send", type="primary"):
            if user_input:
                # Add user message to history
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                
                # Process with bot
                with st.spinner("Thinking..."):
                    result = asyncio.run(st.session_state.bot_manager.process_query(user_input, st.session_state.session_id))
                    
                    # Add bot response to history
                    st.session_state.chat_history.append({"role": "bot", "content": result["response"]})
                
                # Clear input and rerun
                st.session_state.chat_input = ""
                st.rerun()
    
    with col2:
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Quick suggestions
    st.markdown("### Quick Suggestions")
    suggestions = [
        "Check my account balance",
        "Process a payment",
        "Analyze my portfolio",
        "Help with authentication"
    ]
    
    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            if st.button(suggestion, key=f"suggestion_{i}"):
                st.session_state.chat_input = suggestion
                st.rerun()

def show_cache_management_page():
    """Display cache management page"""
    st.markdown("## 💾 Cache Management")
    st.markdown("Monitor and manage system cache")
    
    # Cache statistics
    cache_stats = st.session_state.cache_manager.get_cache_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Workflow Cache", cache_stats['workflow_cache_size'])
    
    with col2:
        st.metric("User Cache", cache_stats['user_cache_size'])
    
    with col3:
        st.metric("Use Case Cache", cache_stats['use_case_cache_size'])
    
    with col4:
        st.metric("Total Cache", cache_stats['total_cache_size'])
    
    # Cache controls
    st.markdown("### Cache Controls")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Clear All Cache", type="secondary"):
            st.session_state.cache_manager.clear_cache("all")
            st.success("All cache cleared!")
            st.rerun()
    
    with col2:
        if st.button("Clear Workflow Cache"):
            st.session_state.cache_manager.clear_cache("workflow")
            st.success("Workflow cache cleared!")
            st.rerun()
    
    with col3:
        if st.button("Clear User Cache"):
            st.session_state.cache_manager.clear_cache("user")
            st.success("User cache cleared!")
            st.rerun()
    
    with col4:
        if st.button("Clear Use Case Cache"):
            st.session_state.cache_manager.clear_cache("use_case")
            st.success("Use case cache cleared!")
            st.rerun()
    
    # Cache details
    st.markdown("### Cache Details")
    
    if cache_stats['workflow_cache_size'] > 0:
        st.markdown("#### Workflow Cache")
        for workflow_id, data in st.session_state.cache_manager.workflow_cache.items():
            st.json({"workflow_id": workflow_id, "data": data})
    
    if cache_stats['user_cache_size'] > 0:
        st.markdown("#### User Cache")
        for user_id, queries in st.session_state.cache_manager.user_cache.items():
            st.json({"user_id": user_id, "queries": list(queries.keys())})
    
    if cache_stats['use_case_cache_size'] > 0:
        st.markdown("#### Use Case Cache")
        for cache_key, data in st.session_state.cache_manager.use_case_cache.items():
            st.json({"cache_key": cache_key, "data": data})

def show_adaptive_query_page():
    """Display adaptive query processing page"""
    st.markdown("## 🧠 Adaptive Query Processing")
    st.markdown("Execute complex queries with intelligent tool orchestration, caching, and Python aggregation")
    
    # Example queries
    st.markdown("### Example Queries")
    st.markdown("""
    - "Show me total balance across all my accounts"
    - "Analyze spending patterns across all credit cards"
    - "Find high-risk transactions from last month"
    - "Calculate portfolio performance across all holdings"
    """)
    
    # Query input
    st.markdown("### Execute Adaptive Query")
    query = st.text_area("Enter your query", height=100, placeholder="e.g., Show me total balance across all my accounts")
    
    if st.button("Execute Adaptive Query", type="primary"):
        if query:
            with st.spinner("Analyzing query and executing adaptive workflow..."):
                # Execute adaptive query
                result = asyncio.run(
                    st.session_state.adaptive_orchestrator.process_query(
                        query,
                        st.session_state.session_id
                    )
                )
                
                # Display execution plan
                st.markdown("#### Execution Plan")
                st.success(f"Workflow ID: {result['workflow_id']}")
                st.info(f"Source: {result['source']} | Execution Time: {result['execution_time']}")
                
                # Display workflow steps
                if 'result' in result and 'steps' in result['result']:
                    st.markdown("#### Workflow Steps")
                    for step in result['result']['steps']:
                        with st.expander(f"Step {step['step']}: {step['tool']}"):
                            st.json(step)
                
                # Display aggregation results
                if 'result' in result and 'aggregation_results' in result['result']:
                    st.markdown("#### Aggregation Results")
                    st.json(result['result']['aggregation_results'])
                
                # Display final response
                if 'result' in result and 'final_response' in result['result']:
                    st.markdown("#### Final Response")
                    st.success(result['result']['final_response'])
                
                # Show complete result
                with st.expander("View Complete Result"):
                    st.json(result)
    
    # Workflow cache viewer
    st.markdown("---")
    st.markdown("### Recent Workflows")
    cache_stats = st.session_state.cache_manager.get_cache_stats()
    
    if cache_stats['workflow_cache_size'] > 0:
        st.info(f"Found {cache_stats['workflow_cache_size']} cached workflows")
        
        for workflow_id, data in st.session_state.cache_manager.workflow_cache.items():
            with st.expander(f"Workflow: {workflow_id}"):
                st.json(data)
    else:
        st.info("No cached workflows yet. Execute an adaptive query to see workflow caching in action!")

def show_system_status_page():
    """Display system status page"""
    st.markdown("## 📊 System Status")
    st.markdown("Monitor system health and performance")
    
    # Azure status
    st.markdown("### Azure OpenAI Status")
    azure_status = st.session_state.azure_client.get_status()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Available", "✅" if azure_status['available'] else "❌")
    with col2:
        st.metric("Endpoint", azure_status['endpoint'] or "Not configured")
    with col3:
        st.metric("Deployment", azure_status['deployment_name'])
    with col4:
        st.metric("API Key", "✅" if azure_status['api_key_configured'] else "❌")
    
    # Vector store status
    st.markdown("### Vector Store Status")
    vector_stats = st.session_state.vector_store.get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Vectors", vector_stats['total_vectors'])
    with col2:
        st.metric("Dimension", vector_stats['dimension'])
    with col3:
        st.metric("Collection", vector_stats['collection_name'])
    with col4:
        st.metric("Memory Usage", f"{vector_stats['memory_usage_mb']:.2f} MB")
    
    # Embedding service status
    st.markdown("### Embedding Service Status")
    embedding_stats = st.session_state.embedding_service.get_embedding_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Model", embedding_stats['embedding_model'])
    with col2:
        st.metric("Dimension", embedding_stats['dimension'])
    with col3:
        st.metric("Azure Available", "✅" if embedding_stats['azure_client_available'] else "❌")
    with col4:
        st.metric("Vectors", embedding_stats['vector_store_stats']['total_vectors'])
    
    # System performance
    st.markdown("### System Performance")
    
    # Cache performance
    cache_stats = st.session_state.cache_manager.get_cache_stats()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Cache Performance")
        st.metric("Cache Hit Rate", "70%")  # Simulated
        st.metric("Total Cache Size", cache_stats['total_cache_size'])
        st.metric("Cache TTL", f"{cache_stats['cache_ttl']} seconds")
    
    with col2:
        st.markdown("#### Tool Performance")
        tool_stats = st.session_state.mcp_tools_manager.get_tool_statistics()
        st.metric("Total Executions", tool_stats.get('total_executions', 0))
        st.metric("Success Rate", f"{tool_stats.get('success_rate', 0):.1%}")
        st.metric("Avg Execution Time", f"{tool_stats.get('average_execution_time', 0):.2f}s")

if __name__ == "__main__":
    main()
