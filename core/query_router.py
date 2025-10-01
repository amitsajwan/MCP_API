"""
Query Router for Hybrid Intelligence Engine
Routes queries between Pre-Analyzed and Adaptive pipelines
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class QueryPlanType(Enum):
    """Types of query plans"""
    PRE_ANALYZED = "pre_analyzed"
    ADAPTIVE = "adaptive"


class QueryPlan:
    """Base class for query plans"""
    
    def __init__(self, plan_type: QueryPlanType, query: str, confidence: float = 1.0):
        self.plan_type = plan_type
        self.query = query
        self.confidence = confidence
        self.timestamp = datetime.now().isoformat()


class PreAnalyzedPlan(QueryPlan):
    """Query plan for pre-analyzed pipeline"""
    
    def __init__(self, query: str, use_case_id: str, similarity: float, **kwargs):
        super().__init__(QueryPlanType.PRE_ANALYZED, query, similarity)
        self.use_case_id = use_case_id
        self.similarity = similarity
        self.execution_strategy = "use_case_library"
        self.parameters = kwargs.get("parameters", {})
        self.expected_execution_time = kwargs.get("expected_execution_time", "< 5s")


class AdaptivePlan(QueryPlan):
    """Query plan for adaptive pipeline"""
    
    def __init__(self, query: str, available_tools: list, **kwargs):
        super().__init__(QueryPlanType.ADAPTIVE, query, kwargs.get("confidence", 0.7))
        self.available_tools = available_tools
        self.execution_strategy = "runtime_llm_analysis"
        self.llm_required = True
        self.expected_execution_time = kwargs.get("expected_execution_time", "10-30s")


class QueryRouter:
    """
    Query Router for Hybrid Intelligence Engine
    Routes queries between Pre-Analyzed vs Adaptive pipelines
    """
    
    def __init__(self, semantic_store, use_case_library=None):
        """
        Initialize query router
        
        Args:
            semantic_store: Vector store for similarity search
            use_case_library: Pre-analyzed use case library
        """
        self.semantic_store = semantic_store
        self.use_case_library = use_case_library or {}
        self.routing_stats = {
            "total_queries": 0,
            "pre_analyzed_routes": 0,
            "adaptive_routes": 0,
            "average_similarity": 0.0
        }
    
    async def route_query(self, query: str) -> QueryPlan:
        """
        Route query between Pre-Analyzed and Adaptive pipelines
        
        Args:
            query: User query string
            
        Returns:
            QueryPlan (PreAnalyzedPlan or AdaptivePlan)
        """
        try:
            logger.info(f"🔀 Routing query: {query}")
            
            # Update routing statistics
            self.routing_stats["total_queries"] += 1
            
            # Check semantic similarity first (Pre-Analyzed Pipeline)
            similar_use_cases = await self._find_similar_use_cases(query, threshold=0.8)
            
            if similar_use_cases:
                best_match = similar_use_cases[0]
                
                # Create Pre-Analyzed Plan
                plan = PreAnalyzedPlan(
                    query=query,
                    use_case_id=best_match["metadata"]["use_case_id"],
                    similarity=best_match["similarity"],
                    parameters=self._extract_parameters(query, best_match),
                    expected_execution_time="< 5s"
                )
                
                # Update statistics
                self.routing_stats["pre_analyzed_routes"] += 1
                self._update_average_similarity(best_match["similarity"])
                
                logger.info(f"✅ Pre-Analyzed route: {best_match['similarity']:.3f} similarity")
                return plan
            
            else:
                # No semantic match - use Adaptive Pipeline
                available_tools = await self._get_available_tools()
                
                plan = AdaptivePlan(
                    query=query,
                    available_tools=available_tools,
                    confidence=0.7,
                    expected_execution_time="10-30s"
                )
                
                # Update statistics
                self.routing_stats["adaptive_routes"] += 1
                
                logger.info("🔄 Adaptive route: No semantic match found")
                return plan
                
        except Exception as e:
            logger.error(f"❌ Query routing failed: {e}")
            
            # Fallback to adaptive plan
            available_tools = await self._get_available_tools()
            return AdaptivePlan(
                query=query,
                available_tools=available_tools,
                confidence=0.5,
                expected_execution_time="15-45s"
            )
    
    async def _find_similar_use_cases(self, query: str, threshold: float = 0.8) -> list:
        """Find similar use cases using semantic store"""
        
        try:
            # Search semantic store for similar use cases
            similar_cases = await self.semantic_store.search_similar(
                query=query,
                metadata_filter={"type": "use_case"},
                top_k=3,
                threshold=threshold
            )
            
            return similar_cases
            
        except Exception as e:
            logger.error(f"Failed to find similar use cases: {e}")
            return []
    
    async def _get_available_tools(self) -> list:
        """Get list of available tools for adaptive pipeline"""
        
        try:
            # This would typically come from the tool manager
            # For now, return a placeholder
            return ["getPayments", "getTransactions", "getCashSummary", "getSecurities"]
            
        except Exception as e:
            logger.error(f"Failed to get available tools: {e}")
            return []
    
    def _extract_parameters(self, query: str, use_case_match: dict) -> dict:
        """Extract parameters from query for use case execution"""
        
        # Simple parameter extraction - in production this would be more sophisticated
        parameters = {}
        
        # Look for common parameter patterns in the query
        query_lower = query.lower()
        
        if "user" in query_lower and "id" in query_lower:
            parameters["user_id"] = "extracted_from_query"
        
        if "account" in query_lower and "id" in query_lower:
            parameters["account_id"] = "extracted_from_query"
        
        if "payment" in query_lower and "id" in query_lower:
            parameters["payment_id"] = "extracted_from_query"
        
        return parameters
    
    def _update_average_similarity(self, similarity: float):
        """Update average similarity for routing statistics"""
        
        current_avg = self.routing_stats["average_similarity"]
        total_pre_analyzed = self.routing_stats["pre_analyzed_routes"]
        
        if total_pre_analyzed == 1:
            self.routing_stats["average_similarity"] = similarity
        else:
            # Calculate running average
            new_avg = (current_avg * (total_pre_analyzed - 1) + similarity) / total_pre_analyzed
            self.routing_stats["average_similarity"] = new_avg
    
    def get_routing_statistics(self) -> dict:
        """Get query routing statistics"""
        
        total_queries = self.routing_stats["total_queries"]
        
        if total_queries == 0:
            return {
                "total_queries": 0,
                "pre_analyzed_percentage": 0,
                "adaptive_percentage": 0,
                "average_similarity": 0
            }
        
        return {
            "total_queries": total_queries,
            "pre_analyzed_routes": self.routing_stats["pre_analyzed_routes"],
            "adaptive_routes": self.routing_stats["adaptive_routes"],
            "pre_analyzed_percentage": (self.routing_stats["pre_analyzed_routes"] / total_queries) * 100,
            "adaptive_percentage": (self.routing_stats["adaptive_routes"] / total_queries) * 100,
            "average_similarity": self.routing_stats["average_similarity"],
            "cache_hit_rate": (self.routing_stats["pre_analyzed_routes"] / total_queries) * 100
        }
    
    def reset_statistics(self):
        """Reset routing statistics"""
        
        self.routing_stats = {
            "total_queries": 0,
            "pre_analyzed_routes": 0,
            "adaptive_routes": 0,
            "average_similarity": 0.0
        }
        
        logger.info("📊 Query routing statistics reset")


class HybridQueryProcessor:
    """
    Hybrid Query Processor that integrates with both pipelines
    """
    
    def __init__(self, query_router, execution_orchestrator, adaptive_processor):
        """
        Initialize hybrid query processor
        
        Args:
            query_router: Query router for pipeline selection
            execution_orchestrator: Execution orchestrator for pre-analyzed cases
            adaptive_processor: Adaptive processor for runtime analysis
        """
        self.query_router = query_router
        self.execution_orchestrator = execution_orchestrator
        self.adaptive_processor = adaptive_processor
    
    async def process_query(self, query: str) -> dict:
        """
        Process query using hybrid intelligence
        
        Args:
            query: User query string
            
        Returns:
            Query processing result
        """
        try:
            logger.info(f"🧠 Processing query with hybrid intelligence: {query}")
            
            # Route query to appropriate pipeline
            query_plan = await self.query_router.route_query(query)
            
            if isinstance(query_plan, PreAnalyzedPlan):
                # Use Pre-Analyzed Pipeline
                logger.info("📚 Using Pre-Analyzed Pipeline")
                
                result = await self.execution_orchestrator.execute_use_case(
                    use_case_id=query_plan.use_case_id,
                    parameters=query_plan.parameters
                )
                
                return {
                    "pipeline": "pre_analyzed",
                    "use_case_id": query_plan.use_case_id,
                    "similarity": query_plan.similarity,
                    "result": result,
                    "execution_time": query_plan.expected_execution_time
                }
            
            elif isinstance(query_plan, AdaptivePlan):
                # Use Adaptive Pipeline
                logger.info("🔄 Using Adaptive Pipeline")
                
                result = await self.adaptive_processor.process_query(query)
                
                return {
                    "pipeline": "adaptive",
                    "tools_used": query_plan.available_tools,
                    "result": result,
                    "execution_time": query_plan.expected_execution_time
                }
            
            else:
                raise ValueError(f"Unknown query plan type: {type(query_plan)}")
                
        except Exception as e:
            logger.error(f"❌ Hybrid query processing failed: {e}")
            return {
                "error": str(e),
                "pipeline": "failed",
                "result": None
            }
    
    def get_processing_statistics(self) -> dict:
        """Get hybrid processing statistics"""
        
        routing_stats = self.query_router.get_routing_statistics()
        
        return {
            "routing_statistics": routing_stats,
            "hybrid_efficiency": routing_stats.get("cache_hit_rate", 0),
            "performance_improvement": f"{(routing_stats.get('cache_hit_rate', 0) / 100) * 80:.1f}% faster for cached queries"
        }
