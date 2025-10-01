"""
Intelligent API Analyzer for Demo MCP System
Analyzes MCP tools discovered via MCP protocol and generates intelligent use cases
Combines API calls + cache operations + Python manipulation for optimal performance
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class IntelligentAPIAnalyzer:
    """
    Hybrid Intelligence Engine - Analyzes MCP tools and generates intelligent use cases
    Implements dual pipeline architecture: Pre-Analyzed + Adaptive
    Only uses MCP protocol - no direct OpenAPI spec access
    """
    
    def __init__(self, mcp_client_connector, vector_store, cache_manager, embedding_service=None, llm_service=None):
        """
        Initialize hybrid intelligence analyzer
        
        Args:
            mcp_client_connector: MCP client that communicates via stdio protocol
            vector_store: Semantic store for vector storage and similarity search
            cache_manager: Multi-tier cache manager
            embedding_service: Embedding service for vector creation (optional)
            llm_service: LLM service for runtime analysis (optional)
        """
        self.mcp_client = mcp_client_connector
        self.vector_store = vector_store  # Semantic Store
        self.cache_manager = cache_manager  # Multi-Tier Cache
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        
        self.analyzed_tools = {}
        self.generated_use_cases = {}
        self.dependency_graph = {}
        self.use_case_library = {}  # Pre-Analyzed Use Case Library
        
    async def analyze_and_generate_use_cases(self) -> Dict[str, Any]:
        """
        Main method: analyze MCP tools and generate intelligent use cases
        
        Returns:
            Complete analysis with metadata, dependencies, and use cases
        """
        try:
            logger.info("Starting intelligent API analysis...")
            
            # 1. Get tools from MCP server via protocol
            tools = await self.mcp_client.list_tools()
            logger.info(f"Discovered {len(tools)} MCP tools for analysis")
            
            # 2. Extract tool metadata
            tool_metadata = self._extract_tool_metadata(tools)
            logger.info(f"Extracted metadata for {len(tool_metadata)} tools")
            
            # 3. Map dependencies between tools
            dependencies = self._map_tool_dependencies(tools, tool_metadata)
            logger.info(f"Mapped dependencies for {len(dependencies)} tools")
            
            # 4. Identify cache opportunities
            cache_opportunities = self._identify_cache_opportunities(tools, tool_metadata)
            logger.info(f"Identified {len(cache_opportunities)} cache opportunities")
            
            # 5. Generate intelligent use cases
            use_cases = await self._generate_intelligent_use_cases(
                tools, tool_metadata, dependencies, cache_opportunities
            )
            logger.info(f"Generated {len(use_cases)} intelligent use cases")
            
            # 6. Store analysis in vector database
            await self._store_analysis_in_vector_db(
                tool_metadata, dependencies, cache_opportunities, use_cases
            )
            
            # 7. Populate Use Case Library (Pre-Analyzed Pipeline)
            self._populate_use_case_library(use_cases)
            
            # 8. Compile complete analysis
            analysis = {
                "analysis_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "total_tools": len(tools),
                "tool_metadata": tool_metadata,
                "dependencies": dependencies,
                "cache_opportunities": cache_opportunities,
                "generated_use_cases": use_cases,
                "use_case_library_size": len(self.use_case_library),
                "analysis_summary": self._generate_analysis_summary(
                    tool_metadata, dependencies, cache_opportunities, use_cases
                )
            }
            
            logger.info("✅ Intelligent API analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Intelligent API analysis failed: {e}")
            return {
                "error": str(e),
                "analysis_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_tool_metadata(self, tools: List[Dict]) -> Dict[str, Dict]:
        """Extract comprehensive metadata from MCP tools"""
        
        tool_metadata = {}
        
        for tool in tools:
            tool_name = tool["name"]
            description = tool["description"]
            parameters = tool.get("parameters", {})
            category = tool.get("category", "Unknown")
            source = tool.get("source", "Unknown")
            
            # Analyze tool characteristics
            metadata = {
                "name": tool_name,
                "description": description,
                "category": category,
                "source_api": source,
                "parameter_count": len(parameters),
                "parameter_names": list(parameters.keys()),
                "parameter_types": {name: info.get("type", "unknown") for name, info in parameters.items()},
                "inferred_purpose": self._infer_purpose_from_description(description),
                "inferred_data_type": self._infer_data_type_from_description(description),
                "cache_strategy": self._determine_cache_strategy_from_tool(tool),
                "manipulation_potential": self._assess_manipulation_potential_from_tool(tool),
                "complexity_score": self._calculate_complexity_score(tool),
                "business_value": self._assess_business_value(tool),
                "execution_frequency": self._estimate_execution_frequency(tool)
            }
            
            tool_metadata[tool_name] = metadata
        
        return tool_metadata
    
    def _infer_purpose_from_description(self, description: str) -> str:
        """Infer tool purpose from MCP tool description"""
        
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['get', 'retrieve', 'fetch', 'list']):
            return "data_retrieval"
        elif any(word in description_lower for word in ['create', 'add', 'post']):
            return "data_creation"
        elif any(word in description_lower for word in ['update', 'modify', 'put', 'patch']):
            return "data_modification"
        elif any(word in description_lower for word in ['delete', 'remove']):
            return "data_deletion"
        elif any(word in description_lower for word in ['approve', 'process', 'execute']):
            return "workflow_action"
        elif any(word in description_lower for word in ['calculate', 'compute', 'analyze']):
            return "data_processing"
        elif any(word in description_lower for word in ['send', 'notify', 'message']):
            return "communication"
        elif any(word in description_lower for word in ['check', 'validate', 'verify']):
            return "validation"
        else:
            return "unknown"
    
    def _infer_data_type_from_description(self, description: str) -> str:
        """Infer expected data type from description"""
        
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['list', 'all', 'multiple', 'array']):
            return "list"
        elif any(word in description_lower for word in ['summary', 'total', 'count', 'statistics']):
            return "summary"
        elif any(word in description_lower for word in ['detail', 'specific', 'single', 'by id']):
            return "object"
        elif any(word in description_lower for word in ['status', 'state', 'result']):
            return "status"
        else:
            return "mixed"
    
    def _determine_cache_strategy_from_tool(self, tool: Dict) -> str:
        """Determine optimal cache strategy based on tool characteristics"""
        
        description = tool["description"].lower()
        parameters = tool.get("parameters", {})
        purpose = self._infer_purpose_from_description(tool["description"])
        
        # Data retrieval tools are good candidates for caching
        if purpose == "data_retrieval":
            if len(parameters) == 0:
                return "cache_full_response"  # No parameters = cache everything
            elif len(parameters) == 1:
                return "cache_by_parameter"   # Single parameter = cache by that param
            else:
                return "cache_selective"      # Multiple params = selective caching
        
        # Lists are good for pagination caching
        elif "list" in description:
            return "cache_paginated"
        
        # Summaries change frequently but are expensive
        elif "summary" in description:
            return "cache_with_short_ttl"
        
        # Workflow actions shouldn't be cached
        elif purpose in ["workflow_action", "data_creation", "data_modification"]:
            return "no_cache"
        
        # Default caching strategy
        else:
            return "cache_with_ttl"
    
    def _assess_manipulation_potential_from_tool(self, tool: Dict) -> str:
        """Assess potential for Python manipulation of tool results"""
        
        description = tool["description"].lower()
        data_type = self._infer_data_type_from_description(tool["description"])
        
        if data_type == "list":
            return "high"  # Lists are great for aggregation, filtering, sorting
        elif data_type == "summary":
            return "medium"  # Summaries can be enhanced with additional calculations
        elif "calculate" in description or "compute" in description:
            return "low"  # Already processed
        elif "get" in description or "retrieve" in description:
            return "high"  # Raw data is good for manipulation
        else:
            return "medium"
    
    def _calculate_complexity_score(self, tool: Dict) -> int:
        """Calculate complexity score (1-10) for tool"""
        
        score = 1
        
        # Add points for parameters
        score += len(tool.get("parameters", {})) * 0.5
        
        # Add points for complex descriptions
        description = tool["description"]
        if len(description.split()) > 10:
            score += 1
        
        # Add points for specific patterns
        if any(word in description.lower() for word in ['complex', 'multiple', 'batch', 'aggregate']):
            score += 2
        
        # Cap at 10
        return min(int(score), 10)
    
    def _assess_business_value(self, tool: Dict) -> str:
        """Assess business value of tool"""
        
        description = tool["description"].lower()
        category = tool.get("category", "").lower()
        
        # High value indicators
        if any(word in description for word in ['critical', 'essential', 'core', 'main', 'primary']):
            return "high"
        
        # Category-based assessment
        if category in ['account', 'payment', 'security', 'authentication']:
            return "high"
        elif category in ['support', 'notification', 'message']:
            return "medium"
        else:
            return "medium"
    
    def _estimate_execution_frequency(self, tool: Dict) -> str:
        """Estimate how frequently this tool might be executed"""
        
        purpose = self._infer_purpose_from_description(tool["description"])
        category = tool.get("category", "").lower()
        
        if purpose == "data_retrieval":
            return "high"  # Frequently accessed
        elif purpose == "workflow_action":
            return "medium"  # Occasional use
        elif category in ['account', 'payment']:
            return "high"  # Core business functions
        else:
            return "medium"
    
    def _map_tool_dependencies(self, tools: List[Dict], tool_metadata: Dict) -> Dict:
        """Map dependencies between MCP tools based on parameter relationships"""
        
        dependencies = {}
        
        for tool in tools:
            tool_name = tool["name"]
            parameters = tool.get("parameters", {})
            
            # Find tools that might provide parameters for this tool
            potential_dependencies = []
            
            for other_tool in tools:
                if other_tool["name"] != tool_name:
                    dependency_info = self._check_tool_dependency(
                        other_tool, tool_name, parameters, tool_metadata
                    )
                    if dependency_info:
                        potential_dependencies.append(dependency_info)
            
            if potential_dependencies:
                dependencies[tool_name] = potential_dependencies
        
        return dependencies
    
    def _check_tool_dependency(self, provider_tool: Dict, consumer_tool_name: str, 
                              consumer_parameters: Dict, tool_metadata: Dict) -> Optional[Dict]:
        """Check if provider tool can provide parameters for consumer tool"""
        
        provider_name = provider_tool["name"]
        provider_desc = provider_tool["description"].lower()
        provider_metadata = tool_metadata.get(provider_name, {})
        
        dependency_info = {
            "provider_tool": provider_name,
            "confidence": 0,
            "parameter_mappings": [],
            "dependency_type": "unknown"
        }
        
        # Check each consumer parameter
        for param_name, param_info in consumer_parameters.items():
            param_name_lower = param_name.lower()
            
            # Direct name matching
            if param_name_lower in provider_name.lower():
                dependency_info["parameter_mappings"].append({
                    "consumer_parameter": param_name,
                    "provider_output": "id",
                    "confidence": 0.8
                })
                dependency_info["confidence"] += 0.8
                dependency_info["dependency_type"] = "direct_name_match"
            
            # Description-based matching
            elif param_name_lower in provider_desc:
                dependency_info["parameter_mappings"].append({
                    "consumer_parameter": param_name,
                    "provider_output": param_name,
                    "confidence": 0.6
                })
                dependency_info["confidence"] += 0.6
                dependency_info["dependency_type"] = "description_match"
            
            # Common patterns
            elif self._check_common_dependency_patterns(
                param_name_lower, provider_name, provider_desc, provider_metadata
            ):
                dependency_info["parameter_mappings"].append({
                    "consumer_parameter": param_name,
                    "provider_output": "id",
                    "confidence": 0.7
                })
                dependency_info["confidence"] += 0.7
                dependency_info["dependency_type"] = "pattern_match"
        
        # Only return if confidence is above threshold
        if dependency_info["confidence"] > 0.5:
            dependency_info["confidence"] = min(dependency_info["confidence"], 1.0)
            return dependency_info
        
        return None
    
    def _check_common_dependency_patterns(self, param_name: str, provider_name: str, 
                                         provider_desc: str, provider_metadata: Dict) -> bool:
        """Check for common dependency patterns"""
        
        # ID parameter patterns
        if param_name in ["id", "user_id", "account_id", "payment_id", "transaction_id"]:
            if provider_metadata.get("inferred_purpose") == "data_retrieval":
                return True
        
        # Category-based patterns
        if param_name in ["portfolio_id", "security_id"]:
            if "securities" in provider_desc or "portfolio" in provider_desc:
                return True
        
        # Generic patterns
        if param_name.endswith("_id") and "get" in provider_desc:
            return True
        
        return False
    
    def _identify_cache_opportunities(self, tools: List[Dict], tool_metadata: Dict) -> Dict:
        """Identify cache optimization opportunities"""
        
        cache_opportunities = {
            "high_value_cache_targets": [],
            "cache_combinations": [],
            "cache_strategies": {},
            "estimated_savings": {}
        }
        
        for tool in tools:
            tool_name = tool["name"]
            metadata = tool_metadata.get(tool_name, {})
            
            # High-value cache targets
            if (metadata.get("inferred_purpose") == "data_retrieval" and 
                metadata.get("execution_frequency") == "high"):
                cache_opportunities["high_value_cache_targets"].append({
                    "tool": tool_name,
                    "reason": "High-frequency data retrieval",
                    "cache_strategy": metadata.get("cache_strategy"),
                    "estimated_hit_rate": self._estimate_cache_hit_rate(tool, metadata)
                })
            
            # Cache strategies
            cache_opportunities["cache_strategies"][tool_name] = {
                "strategy": metadata.get("cache_strategy"),
                "ttl_recommendation": self._recommend_cache_ttl(metadata),
                "size_estimate": self._estimate_cache_size(tool, metadata)
            }
        
        # Find cache combinations
        cache_opportunities["cache_combinations"] = self._find_cache_combinations(
            tools, tool_metadata
        )
        
        return cache_opportunities
    
    def _estimate_cache_hit_rate(self, tool: Dict, metadata: Dict) -> float:
        """Estimate cache hit rate for tool"""
        
        frequency = metadata.get("execution_frequency", "medium")
        strategy = metadata.get("cache_strategy", "no_cache")
        
        if strategy == "no_cache":
            return 0.0
        elif frequency == "high" and strategy in ["cache_full_response", "cache_by_parameter"]:
            return 0.8
        elif frequency == "medium":
            return 0.6
        else:
            return 0.4
    
    def _recommend_cache_ttl(self, metadata: Dict) -> int:
        """Recommend cache TTL in seconds"""
        
        purpose = metadata.get("inferred_purpose", "unknown")
        frequency = metadata.get("execution_frequency", "medium")
        
        if purpose == "data_retrieval" and frequency == "high":
            return 3600  # 1 hour
        elif purpose == "data_retrieval":
            return 1800  # 30 minutes
        elif "summary" in metadata.get("description", "").lower():
            return 300   # 5 minutes
        else:
            return 600   # 10 minutes
    
    def _estimate_cache_size(self, tool: Dict, metadata: Dict) -> str:
        """Estimate cache size for tool"""
        
        data_type = metadata.get("inferred_data_type", "mixed")
        
        if data_type == "list":
            return "large"  # Lists can be big
        elif data_type == "summary":
            return "small"  # Summaries are compact
        elif data_type == "object":
            return "medium"  # Single objects
        else:
            return "medium"
    
    def _find_cache_combinations(self, tools: List[Dict], tool_metadata: Dict) -> List[Dict]:
        """Find tools that can benefit from combined caching"""
        
        combinations = []
        
        # Group tools by category
        tools_by_category = {}
        for tool in tools:
            category = tool.get("category", "Unknown")
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool)
        
        # Find combinations within categories
        for category, category_tools in tools_by_category.items():
            if len(category_tools) >= 2:
                combination = {
                    "category": category,
                    "tools": [t["name"] for t in category_tools],
                    "cache_strategy": "category_cache",
                    "benefit": f"Cache {category} data together for cross-tool queries"
                }
                combinations.append(combination)
        
        return combinations
    
    async def _generate_intelligent_use_cases(
        self, 
        tools: List[Dict], 
        tool_metadata: Dict, 
        dependencies: Dict, 
        cache_opportunities: Dict
    ) -> List[Dict]:
        """Generate intelligent use cases combining API calls + cache + Python manipulation"""
        
        use_cases = []
        
        # Group tools by category for category-specific use cases
        tools_by_category = {}
        for tool in tools:
            category = tool.get("category", "Unknown")
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool)
        
        # Generate category-specific use cases
        for category, category_tools in tools_by_category.items():
            category_use_cases = await self._generate_category_use_cases(
                category, category_tools, tool_metadata, dependencies
            )
            use_cases.extend(category_use_cases)
        
        # Generate cross-category use cases
        cross_category_use_cases = await self._generate_cross_category_use_cases(
            tools_by_category, tool_metadata, dependencies
        )
        use_cases.extend(cross_category_use_cases)
        
        # Generate cache-optimized use cases
        cache_use_cases = await self._generate_cache_optimized_use_cases(
            cache_opportunities, tool_metadata
        )
        use_cases.extend(cache_use_cases)
        
        return use_cases
    
    async def _generate_category_use_cases(
        self, 
        category: str, 
        tools: List[Dict], 
        tool_metadata: Dict, 
        dependencies: Dict
    ) -> List[Dict]:
        """Generate use cases within a category"""
        
        use_cases = []
        
        if len(tools) >= 2:
            # Create comprehensive category analysis use case
            use_case = {
                "id": f"category_analysis_{category.lower()}_{uuid.uuid4().hex[:8]}",
                "name": f"Complete {category} Analysis",
                "description": f"Comprehensive analysis and processing using all {category} tools",
                "category": category,
                "tools": [tool["name"] for tool in tools],
                "business_value": "High",
                "complexity": "Medium",
                "execution_plan": self._create_execution_plan(tools, dependencies, tool_metadata),
                "cache_strategy": self._determine_cache_strategy_for_use_case(tools, tool_metadata),
                "python_manipulation": self._generate_python_code_for_use_case(tools, tool_metadata),
                "estimated_execution_time": self._estimate_execution_time(tools),
                "cache_benefits": self._calculate_cache_benefits(tools, tool_metadata)
            }
            use_cases.append(use_case)
        
        return use_cases
    
    async def _generate_cross_category_use_cases(
        self, 
        tools_by_category: Dict, 
        tool_metadata: Dict, 
        dependencies: Dict
    ) -> List[Dict]:
        """Generate use cases that span multiple categories"""
        
        use_cases = []
        categories = list(tools_by_category.keys())
        
        # Generate cross-category combinations
        if len(categories) >= 2:
            # Create a comprehensive cross-system use case
            all_tools = []
            for category_tools in tools_by_category.values():
                all_tools.extend(category_tools)
            
            use_case = {
                "id": f"cross_system_analysis_{uuid.uuid4().hex[:8]}",
                "name": "Cross-System Comprehensive Analysis",
                "description": "Integrate data across all systems for complete business view",
                "category": "Cross-System",
                "tools": [tool["name"] for tool in all_tools],
                "business_value": "Critical",
                "complexity": "High",
                "execution_plan": self._create_cross_system_execution_plan(all_tools, dependencies),
                "cache_strategy": "multi_level_caching",
                "python_manipulation": self._generate_cross_system_python_code(all_tools),
                "estimated_execution_time": self._estimate_cross_system_execution_time(all_tools),
                "cache_benefits": "Massive cache benefits across all systems"
            }
            use_cases.append(use_case)
        
        return use_cases
    
    async def _generate_cache_optimized_use_cases(
        self, 
        cache_opportunities: Dict, 
        tool_metadata: Dict
    ) -> List[Dict]:
        """Generate use cases optimized for caching"""
        
        use_cases = []
        
        # Create cache-optimized use case for high-value targets
        high_value_targets = cache_opportunities.get("high_value_cache_targets", [])
        
        if high_value_targets:
            use_case = {
                "id": f"cache_optimized_{uuid.uuid4().hex[:8]}",
                "name": "Cache-Optimized Data Processing",
                "description": "Optimize performance through intelligent caching strategies",
                "category": "Performance",
                "tools": [target["tool"] for target in high_value_targets],
                "business_value": "High",
                "complexity": "Medium",
                "execution_plan": self._create_cache_optimized_execution_plan(high_value_targets),
                "cache_strategy": "intelligent_caching",
                "python_manipulation": self._generate_cache_optimization_code(high_value_targets),
                "estimated_execution_time": "Sub-second after initial cache",
                "cache_benefits": "90% reduction in API calls"
            }
            use_cases.append(use_case)
        
        return use_cases
    
    def _create_execution_plan(self, tools: List[Dict], dependencies: Dict, tool_metadata: Dict) -> List[Dict]:
        """Create execution plan for use case"""
        
        plan = []
        
        # Sort tools by dependencies
        sorted_tools = self._sort_tools_by_dependencies(tools, dependencies)
        
        for i, tool in enumerate(sorted_tools):
            tool_name = tool["name"]
            metadata = tool_metadata.get(tool_name, {})
            
            step = {
                "step_number": i + 1,
                "tool": tool_name,
                "purpose": metadata.get("inferred_purpose", "unknown"),
                "cache_strategy": metadata.get("cache_strategy", "no_cache"),
                "depends_on": self._find_step_dependencies(tool_name, dependencies),
                "parallel_with": [],
                "estimated_time": "1-3 seconds"
            }
            
            plan.append(step)
        
        return plan
    
    def _sort_tools_by_dependencies(self, tools: List[Dict], dependencies: Dict) -> List[Dict]:
        """Sort tools by dependency order"""
        
        # Simple topological sort based on dependencies
        sorted_tools = []
        remaining_tools = tools.copy()
        
        while remaining_tools:
            # Find tools with no dependencies or satisfied dependencies
            ready_tools = []
            for tool in remaining_tools:
                tool_name = tool["name"]
                tool_deps = dependencies.get(tool_name, [])
                
                # Check if all dependencies are satisfied
                satisfied = True
                for dep in tool_deps:
                    if not any(t["name"] == dep["provider_tool"] for t in sorted_tools):
                        satisfied = False
                        break
                
                if satisfied:
                    ready_tools.append(tool)
            
            # Add ready tools to sorted list
            for tool in ready_tools:
                sorted_tools.append(tool)
                remaining_tools.remove(tool)
        
        return sorted_tools
    
    def _find_step_dependencies(self, tool_name: str, dependencies: Dict) -> List[int]:
        """Find step numbers that this tool depends on"""
        
        tool_deps = dependencies.get(tool_name, [])
        return [dep["provider_tool"] for dep in tool_deps]
    
    def _determine_cache_strategy_for_use_case(self, tools: List[Dict], tool_metadata: Dict) -> str:
        """Determine overall cache strategy for use case"""
        
        cache_strategies = []
        for tool in tools:
            metadata = tool_metadata.get(tool["name"], {})
            strategy = metadata.get("cache_strategy", "no_cache")
            cache_strategies.append(strategy)
        
        if "cache_full_response" in cache_strategies:
            return "aggressive_caching"
        elif "cache_by_parameter" in cache_strategies:
            return "selective_caching"
        elif "no_cache" in cache_strategies:
            return "minimal_caching"
        else:
            return "standard_caching"
    
    def _generate_python_code_for_use_case(self, tools: List[Dict], tool_metadata: Dict) -> str:
        """Generate Python code for use case manipulation"""
        
        # Create a generic aggregation function
        tool_names = [tool["name"] for tool in tools]
        
        code = f'''
def process_use_case_data(cache_manager):
    """
    Process data from multiple tools: {', '.join(tool_names)}
    """
    results = {{}}
    
    # Get cached data from each tool
'''
        
        for tool in tools:
            tool_name = tool["name"]
            metadata = tool_metadata.get(tool_name, {})
            data_type = metadata.get("inferred_data_type", "mixed")
            
            code += f'''
    # Get data from {tool_name}
    {tool_name}_data = cache_manager.get_workflow_cache("{tool_name}_cache_key")
    if {tool_name}_data:
        results["{tool_name}"] = {tool_name}_data
'''
        
        code += '''
    # Process and aggregate data
    processed_results = {
        "total_items": sum(len(data) if isinstance(data, list) else 1 for data in results.values()),
        "categories": list(results.keys()),
        "summary": {
            key: len(data) if isinstance(data, list) else "single_item"
            for key, data in results.items()
        }
    }
    
    return processed_results
'''
        
        return code
    
    def _estimate_execution_time(self, tools: List[Dict]) -> str:
        """Estimate execution time for use case"""
        
        base_time = len(tools) * 2  # 2 seconds per tool
        return f"{base_time}-{base_time + 5} seconds"
    
    def _calculate_cache_benefits(self, tools: List[Dict], tool_metadata: Dict) -> str:
        """Calculate cache benefits for use case"""
        
        cacheable_tools = 0
        for tool in tools:
            metadata = tool_metadata.get(tool["name"], {})
            if metadata.get("cache_strategy") != "no_cache":
                cacheable_tools += 1
        
        if cacheable_tools == len(tools):
            return "High cache benefits - all tools cacheable"
        elif cacheable_tools > len(tools) // 2:
            return "Medium cache benefits - most tools cacheable"
        else:
            return "Low cache benefits - limited caching opportunities"
    
    def _create_cross_system_execution_plan(self, tools: List[Dict], dependencies: Dict) -> List[Dict]:
        """Create execution plan for cross-system use case"""
        
        # Group tools by category for parallel execution
        tools_by_category = {}
        for tool in tools:
            category = tool.get("category", "Unknown")
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool)
        
        plan = []
        step_number = 1
        
        # Add parallel execution steps for each category
        for category, category_tools in tools_by_category.items():
            for tool in category_tools:
                plan.append({
                    "step_number": step_number,
                    "tool": tool["name"],
                    "purpose": f"Get {category} data",
                    "cache_strategy": "cache_full_response",
                    "parallel_with": [t["name"] for t in category_tools if t != tool],
                    "estimated_time": "2-5 seconds"
                })
                step_number += 1
        
        # Add aggregation step
        plan.append({
            "step_number": step_number,
            "tool": "python_aggregation",
            "purpose": "Aggregate data from all systems",
            "cache_strategy": "cache_aggregated_results",
            "depends_on": list(range(1, step_number)),
            "estimated_time": "1-2 seconds"
        })
        
        return plan
    
    def _generate_cross_system_python_code(self, tools: List[Dict]) -> str:
        """Generate Python code for cross-system use case"""
        
        tool_names = [tool["name"] for tool in tools]
        
        code = f'''
def aggregate_cross_system_data(cache_manager):
    """
    Aggregate data from all systems: {', '.join(tool_names)}
    """
    system_data = {{}}
    
    # Collect data from all systems
'''
        
        for tool in tools:
            tool_name = tool["name"]
            code += f'''
    {tool_name}_data = cache_manager.get_workflow_cache("{tool_name}_cache_key")
    if {tool_name}_data:
        system_data["{tool_name}"] = {tool_name}_data
'''
        
        code += '''
    # Create comprehensive cross-system analysis
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "systems_analyzed": list(system_data.keys()),
        "total_data_points": sum(
            len(data) if isinstance(data, list) else 1 
            for data in system_data.values()
        ),
        "system_summary": {
            system: {
                "data_type": type(data).__name__,
                "size": len(data) if isinstance(data, (list, dict)) else 1
            }
            for system, data in system_data.items()
        },
        "cross_system_insights": generate_cross_system_insights(system_data)
    }
    
    return analysis

def generate_cross_system_insights(data):
    """Generate insights across systems"""
    insights = []
    
    # Add cross-system analysis logic here
    insights.append("Cross-system data correlation analysis")
    insights.append("Performance metrics across systems")
    insights.append("Business intelligence insights")
    
    return insights
'''
        
        return code
    
    def _estimate_cross_system_execution_time(self, tools: List[Dict]) -> str:
        """Estimate execution time for cross-system use case"""
        
        # Cross-system use cases are typically longer
        base_time = len(tools) * 3
        return f"{base_time}-{base_time + 10} seconds"
    
    def _create_cache_optimized_execution_plan(self, high_value_targets: List[Dict]) -> List[Dict]:
        """Create execution plan optimized for caching"""
        
        plan = []
        
        for i, target in enumerate(high_value_targets):
            plan.append({
                "step_number": i + 1,
                "tool": target["tool"],
                "purpose": f"Cache {target['tool']} data",
                "cache_strategy": target["cache_strategy"],
                "cache_hit_rate": target["estimated_hit_rate"],
                "estimated_time": "0.1 seconds (cached)"
            })
        
        # Add processing step
        plan.append({
            "step_number": len(high_value_targets) + 1,
            "tool": "python_processing",
            "purpose": "Process cached data",
            "cache_strategy": "no_cache",
            "depends_on": list(range(1, len(high_value_targets) + 1)),
            "estimated_time": "0.5 seconds"
        })
        
        return plan
    
    def _generate_cache_optimization_code(self, high_value_targets: List[Dict]) -> str:
        """Generate Python code for cache optimization"""
        
        target_tools = [target["tool"] for target in high_value_targets]
        
        code = f'''
def optimize_with_caching(cache_manager):
    """
    Optimize processing using cached data from: {', '.join(target_tools)}
    """
    cached_data = {{}}
    
    # Retrieve all cached data
'''
        
        for target in high_value_targets:
            tool_name = target["tool"]
            code += f'''
    {tool_name}_data = cache_manager.get_workflow_cache("{tool_name}_cache_key")
    if {tool_name}_data:
        cached_data["{tool_name}"] = {tool_name}_data
        logger.info(f"✓ Retrieved cached data for {{tool_name}}")
    else:
        logger.warning(f"⚠ No cached data for {{tool_name}}")
'''
        
        code += '''
    # Process cached data efficiently
    if cached_data:
        # All data is cached - process quickly
        processed_results = {
            "cache_hit_rate": len(cached_data) / len(target_tools),
            "processing_time": "sub_second",
            "data_summary": {
                tool: len(data) if isinstance(data, list) else "single_item"
                for tool, data in cached_data.items()
            },
            "optimization_benefits": "90% reduction in API calls"
        }
        
        return processed_results
    else:
        return {"error": "No cached data available for optimization"}
'''
        
        return code
    
    async def _store_analysis_in_vector_db(
        self, 
        tool_metadata: Dict, 
        dependencies: Dict, 
        cache_opportunities: Dict, 
        use_cases: List[Dict]
    ):
        """Store analysis results in vector database"""
        
        try:
            # Store tool metadata
            for tool_name, metadata in tool_metadata.items():
                description = f"""
                Tool: {tool_name}
                Purpose: {metadata['inferred_purpose']}
                Category: {metadata['category']}
                Cache Strategy: {metadata['cache_strategy']}
                Business Value: {metadata['business_value']}
                """
                
                if self.embedding_service:
                    embedding = await self.embedding_service.create_embedding(description)
                else:
                    # Fallback: use simple hash-based embedding
                    embedding = self._create_simple_embedding(description)
                
                self.vector_store.add_vector(
                    content=description,
                    vector=embedding,
                    metadata={
                        "type": "tool_metadata",
                        "tool_name": tool_name,
                        "category": metadata["category"],
                        "source_api": metadata["source_api"],
                        "purpose": metadata["inferred_purpose"],
                        "cache_strategy": metadata["cache_strategy"]
                    }
                )
            
            # Store use cases
            for use_case in use_cases:
                description = f"""
                Use Case: {use_case['name']}
                Description: {use_case['description']}
                Tools: {', '.join(use_case['tools'])}
                Category: {use_case['category']}
                Business Value: {use_case['business_value']}
                """
                
                if self.embedding_service:
                    embedding = await self.embedding_service.create_embedding(description)
                else:
                    embedding = self._create_simple_embedding(description)
                
                self.vector_store.add_vector(
                    content=description,
                    vector=embedding,
                    metadata={
                        "type": "use_case",
                        "use_case_id": use_case["id"],
                        "tools": use_case["tools"],
                        "category": use_case["category"],
                        "business_value": use_case["business_value"],
                        "complexity": use_case["complexity"]
                    }
                )
            
            logger.info(f"✅ Stored {len(tool_metadata)} tool metadata and {len(use_cases)} use cases in vector database")
            
        except Exception as e:
            logger.error(f"❌ Failed to store analysis in vector database: {e}")
    
    def _create_simple_embedding(self, text: str) -> List[float]:
        """Create simple embedding as fallback"""
        
        # Simple hash-based embedding for demo purposes
        import hashlib
        
        # Create a simple hash-based vector
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Convert to float vector
        vector = []
        for i in range(0, len(hash_hex), 2):
            hex_pair = hash_hex[i:i+2]
            value = int(hex_pair, 16) / 255.0  # Normalize to 0-1
            vector.append(value)
        
        # Pad or truncate to standard dimension
        target_dim = 1536  # Standard embedding dimension
        if len(vector) < target_dim:
            vector.extend([0.0] * (target_dim - len(vector)))
        else:
            vector = vector[:target_dim]
        
        return vector
    
    def _generate_analysis_summary(
        self, 
        tool_metadata: Dict, 
        dependencies: Dict, 
        cache_opportunities: Dict, 
        use_cases: List[Dict]
    ) -> Dict:
        """Generate summary of analysis"""
        
        # Count tools by category
        categories = {}
        for metadata in tool_metadata.values():
            category = metadata["category"]
            categories[category] = categories.get(category, 0) + 1
        
        # Count tools by purpose
        purposes = {}
        for metadata in tool_metadata.values():
            purpose = metadata["inferred_purpose"]
            purposes[purpose] = purposes.get(purpose, 0) + 1
        
        # Calculate cache statistics
        cacheable_tools = sum(
            1 for metadata in tool_metadata.values()
            if metadata["cache_strategy"] != "no_cache"
        )
        
        return {
            "total_tools_analyzed": len(tool_metadata),
            "categories": categories,
            "purposes": purposes,
            "dependency_relationships": len(dependencies),
            "cacheable_tools": cacheable_tools,
            "cache_coverage": f"{(cacheable_tools / len(tool_metadata) * 100):.1f}%",
            "generated_use_cases": len(use_cases),
            "use_case_categories": list(set(uc["category"] for uc in use_cases)),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    async def route_query(self, query: str) -> Dict:
        """
        Query Router - Route between Pre-Analyzed vs Adaptive pipeline
        Implements hybrid intelligence routing as per architecture
        """
        try:
            logger.info(f"🔀 Routing query: {query}")
            
            # Check semantic similarity first (Pre-Analyzed Pipeline)
            similar_use_cases = await self.vector_store.search_similar(
                query=query,
                metadata_filter={"type": "use_case"},
                top_k=3,
                threshold=0.8  # High confidence threshold
            )
            
            if similar_use_cases and similar_use_cases[0]['similarity'] >= 0.8:
                # Pre-Analyzed Pipeline: Use existing use case
                logger.info("✅ Semantic match found - using Pre-Analyzed Pipeline")
                
                best_match = similar_use_cases[0]
                use_case_id = best_match['metadata']['use_case_id']
                
                return {
                    "pipeline": "pre_analyzed",
                    "use_case": self.use_case_library.get(use_case_id),
                    "similarity": best_match['similarity'],
                    "confidence": "high",
                    "execution_strategy": "use_case_library"
                }
            
            else:
                # Adaptive Pipeline: Runtime LLM analysis
                logger.info("🔄 No semantic match - using Adaptive Pipeline")
                
                return {
                    "pipeline": "adaptive",
                    "query": query,
                    "confidence": "medium",
                    "execution_strategy": "runtime_llm_analysis"
                }
                
        except Exception as e:
            logger.error(f"❌ Query routing failed: {e}")
            return {
                "pipeline": "adaptive",
                "query": query,
                "error": str(e),
                "confidence": "low"
            }
    
    async def get_analysis_for_query(self, query: str) -> Dict:
        """Get relevant analysis for a specific query (legacy method)"""
        
        try:
            # Search vector database for relevant tools and use cases
            similar_tools = await self.vector_store.search_similar(
                query=query,
                metadata_filter={"type": "tool_metadata"},
                top_k=5
            )
            
            similar_use_cases = await self.vector_store.search_similar(
                query=query,
                metadata_filter={"type": "use_case"},
                top_k=3
            )
            
            return {
                "query": query,
                "relevant_tools": similar_tools,
                "relevant_use_cases": similar_use_cases,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis for query: {e}")
            return {"error": str(e)}
    
    def _populate_use_case_library(self, use_cases: List[Dict]):
        """Populate Use Case Library for Pre-Analyzed Pipeline"""
        
        logger.info(f"📚 Populating Use Case Library with {len(use_cases)} use cases")
        
        for use_case in use_cases:
            use_case_id = use_case["id"]
            self.use_case_library[use_case_id] = {
                **use_case,
                "library_timestamp": datetime.now().isoformat(),
                "execution_count": 0,
                "success_rate": 0.0
            }
        
        logger.info(f"✅ Use Case Library populated with {len(self.use_case_library)} entries")
    
    async def execute_use_case(self, use_case_id: str, parameters: Dict[str, Any] = None) -> Dict:
        """
        Execution Orchestrator - Execute use case with multi-tier caching
        Implements execution orchestration as per architecture
        """
        try:
            logger.info(f"🎯 Executing use case: {use_case_id}")
            
            if use_case_id not in self.use_case_library:
                return {"error": f"Use case {use_case_id} not found in library"}
            
            use_case = self.use_case_library[use_case_id]
            execution_plan = use_case.get("execution_plan", [])
            
            # Check multi-tier cache first
            cache_key = f"use_case_{use_case_id}_{hash(str(parameters))}"
            cached_result = self.cache_manager.get_workflow_cache(cache_key)
            
            if cached_result:
                logger.info("✅ Cache hit - returning cached result")
                return {
                    "success": True,
                    "result": cached_result,
                    "source": "cache",
                    "execution_time": "< 1s"
                }
            
            # Execute use case
            execution_results = []
            start_time = datetime.now()
            
            for step in execution_plan:
                step_result = await self._execute_use_case_step(step, parameters)
                execution_results.append(step_result)
                
                # Cache intermediate results if specified
                if step.get("cache_strategy") != "no_cache":
                    step_cache_key = f"step_{use_case_id}_{step['step_number']}"
                    self.cache_manager.set_workflow_cache(step_cache_key, step_result)
            
            # Generate final result
            final_result = self._aggregate_execution_results(execution_results, use_case)
            
            # Cache final result
            self.cache_manager.set_workflow_cache(cache_key, final_result)
            
            # Update use case statistics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_use_case_statistics(use_case_id, execution_time, True)
            
            logger.info(f"✅ Use case {use_case_id} executed successfully in {execution_time:.2f}s")
            
            return {
                "success": True,
                "result": final_result,
                "source": "execution",
                "execution_time": f"{execution_time:.2f}s",
                "steps_executed": len(execution_results)
            }
            
        except Exception as e:
            logger.error(f"❌ Use case execution failed: {e}")
            self._update_use_case_statistics(use_case_id, 0, False)
            return {"error": str(e), "success": False}
    
    async def _execute_use_case_step(self, step: Dict, parameters: Dict) -> Dict:
        """Execute a single step in the use case execution plan"""
        
        step_type = step.get("tool", "unknown")
        
        if step_type.startswith("python_"):
            # Python manipulation step
            return await self._execute_python_step(step, parameters)
        else:
            # MCP tool execution step
            return await self._execute_mcp_tool_step(step, parameters)
    
    async def _execute_mcp_tool_step(self, step: Dict, parameters: Dict) -> Dict:
        """Execute MCP tool step"""
        
        tool_name = step["tool"]
        tool_parameters = self._resolve_step_parameters(step, parameters)
        
        try:
            result = await self.mcp_client.execute_tool(tool_name, tool_parameters)
            
            return {
                "step_number": step["step_number"],
                "tool": tool_name,
                "success": result.get("success", False),
                "result": result.get("result"),
                "execution_time": result.get("execution_time", "0s")
            }
            
        except Exception as e:
            return {
                "step_number": step["step_number"],
                "tool": tool_name,
                "success": False,
                "error": str(e)
            }
    
    async def _execute_python_step(self, step: Dict, parameters: Dict) -> Dict:
        """Execute Python manipulation step"""
        
        python_code = step.get("code", "")
        
        try:
            # This would integrate with SafePythonExecutor from the architecture
            # For now, return a placeholder
            return {
                "step_number": step["step_number"],
                "tool": "python_manipulation",
                "success": True,
                "result": "Python manipulation executed (placeholder)",
                "execution_time": "0.1s"
            }
            
        except Exception as e:
            return {
                "step_number": step["step_number"],
                "tool": "python_manipulation",
                "success": False,
                "error": str(e)
            }
    
    def _resolve_step_parameters(self, step: Dict, global_parameters: Dict) -> Dict:
        """Resolve step parameters from global parameters and dependencies"""
        
        # Simple parameter resolution - in production this would be more sophisticated
        return global_parameters or {}
    
    def _aggregate_execution_results(self, execution_results: List[Dict], use_case: Dict) -> Dict:
        """Aggregate results from all execution steps"""
        
        successful_steps = [r for r in execution_results if r.get("success", False)]
        failed_steps = [r for r in execution_results if not r.get("success", False)]
        
        return {
            "use_case_id": use_case["id"],
            "use_case_name": use_case["name"],
            "total_steps": len(execution_results),
            "successful_steps": len(successful_steps),
            "failed_steps": len(failed_steps),
            "step_results": execution_results,
            "aggregated_data": "Placeholder for aggregated data",
            "execution_summary": f"Executed {len(successful_steps)}/{len(execution_results)} steps successfully"
        }
    
    def _update_use_case_statistics(self, use_case_id: str, execution_time: float, success: bool):
        """Update use case execution statistics"""
        
        if use_case_id in self.use_case_library:
            use_case = self.use_case_library[use_case_id]
            use_case["execution_count"] += 1
            
            # Simple success rate calculation
            if success:
                current_rate = use_case["success_rate"]
                new_rate = (current_rate * (use_case["execution_count"] - 1) + 1.0) / use_case["execution_count"]
                use_case["success_rate"] = new_rate
            else:
                current_rate = use_case["success_rate"]
                new_rate = (current_rate * (use_case["execution_count"] - 1) + 0.0) / use_case["execution_count"]
                use_case["success_rate"] = new_rate
    
    def get_use_case_library_stats(self) -> Dict:
        """Get statistics about the Use Case Library"""
        
        return {
            "total_use_cases": len(self.use_case_library),
            "categories": list(set(uc.get("category", "Unknown") for uc in self.use_case_library.values())),
            "execution_stats": {
                "total_executions": sum(uc.get("execution_count", 0) for uc in self.use_case_library.values()),
                "average_success_rate": sum(uc.get("success_rate", 0) for uc in self.use_case_library.values()) / len(self.use_case_library) if self.use_case_library else 0
            },
            "library_timestamp": datetime.now().isoformat()
        }
    
    def get_analysis_summary(self) -> Dict:
        """Get summary of stored analysis"""
        
        try:
            # Get statistics from vector store
            vector_stats = self.vector_store.get_statistics()
            
            return {
                "vector_store_stats": vector_stats,
                "use_case_library_stats": self.get_use_case_library_stats(),
                "analysis_status": "completed" if vector_stats["total_vectors"] > 0 else "pending",
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis summary: {e}")
            return {"error": str(e)}
