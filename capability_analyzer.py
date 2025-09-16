#!/usr/bin/env python3
"""
Capability Analyzer - Modular Tool Usage Analysis
===============================================
Analyzes tool usage patterns and capabilities demonstrated during interactions.
Provides insights into AI behavior and tool effectiveness.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

@dataclass
class CapabilityMetrics:
    """Metrics for a specific capability"""
    name: str
    count: int
    success_rate: float
    average_execution_time: float
    last_demonstrated: datetime
    examples: List[Dict[str, Any]]

@dataclass
class ToolUsageStats:
    """Statistics for tool usage"""
    tool_name: str
    usage_count: int
    success_count: int
    failure_count: int
    success_rate: float
    average_execution_time: float
    last_used: datetime
    common_args: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "tool_name": self.tool_name,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "average_execution_time": self.average_execution_time,
            "last_used": self.last_used.isoformat(),
            "common_args": self.common_args
        }

class CapabilityAnalyzer:
    """Analyzes capabilities demonstrated through tool usage"""
    
    def __init__(self):
        self.capability_definitions = {
            "intelligent_selection": {
                "description": "🧠 Intelligent Tool Selection",
                "indicators": ["tool_calls", "appropriate_tool_choice"],
                "weight": 1.0
            },
            "tool_chaining": {
                "description": "🔗 Complex Tool Chaining", 
                "indicators": ["multiple_tool_calls", "sequential_execution"],
                "weight": 1.5
            },
            "error_handling": {
                "description": "🛡️ Error Handling & Retry",
                "indicators": ["tool_failures", "error_recovery"],
                "weight": 1.2
            },
            "adaptive_usage": {
                "description": "🔄 Adaptive Tool Usage",
                "indicators": ["successful_execution", "parameter_adaptation"],
                "weight": 1.0
            },
            "reasoning": {
                "description": "🧩 Reasoning About Outputs",
                "indicators": ["result_processing", "context_awareness"],
                "weight": 1.3
            },
            "parallel_execution": {
                "description": "⚡ Parallel Tool Execution",
                "indicators": ["concurrent_tools", "efficiency"],
                "weight": 1.4
            },
            "context_awareness": {
                "description": "🎯 Context Awareness",
                "indicators": ["conversation_history", "state_tracking"],
                "weight": 1.1
            }
        }
        
        self.tool_usage_history: List[Dict[str, Any]] = []
        self.capability_history: List[Dict[str, Any]] = []
        self.session_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
    
    def analyze_tool_execution(self, tool_results: List[Dict[str, Any]], 
                             user_message: str, 
                             session_id: str = None) -> Dict[str, Any]:
        """Analyze tool execution and determine capabilities demonstrated"""
        logger.info(f"🔍 [CAPABILITY_ANALYZER] Analyzing {len(tool_results)} tool executions")
        
        # Record tool usage
        for result in tool_results:
            self._record_tool_usage(result, session_id)
        
        # Analyze capabilities
        capabilities = self._analyze_capabilities(tool_results, user_message)
        
        # Update session stats
        if session_id:
            self._update_session_stats(session_id, capabilities, tool_results)
        
        # Record capability demonstration
        capability_record = {
            "timestamp": datetime.now(),
            "session_id": session_id,
            "user_message": user_message,
            "tool_count": len(tool_results),
            "capabilities": capabilities,
            "tool_results": tool_results
        }
        self.capability_history.append(capability_record)
        
        logger.info(f"✨ [CAPABILITY_ANALYZER] Detected capabilities: {capabilities.get('descriptions', [])}")
        return capabilities
    
    def _analyze_capabilities(self, tool_results: List[Dict[str, Any]], 
                            user_message: str) -> Dict[str, Any]:
        """Analyze which capabilities were demonstrated"""
        capabilities = {}
        descriptions = []
        
        # Basic capability detection
        tool_count = len(tool_results)
        successful_tools = len([r for r in tool_results if r.get("success", False)])
        failed_tools = tool_count - successful_tools
        
        # Intelligent selection
        if tool_count > 0:
            capabilities["intelligent_selection"] = True
            descriptions.append("🧠 Intelligent Tool Selection")
        
        # Tool chaining
        if tool_count > 1:
            capabilities["tool_chaining"] = True
            descriptions.append("🔗 Complex Tool Chaining")
        
        # Error handling
        if failed_tools > 0:
            capabilities["error_handling"] = True
            descriptions.append("🛡️ Error Handling & Retry")
        
        # Adaptive usage
        if successful_tools > 0 and failed_tools == 0:
            capabilities["adaptive_usage"] = True
            descriptions.append("🔄 Adaptive Tool Usage")
        
        # Reasoning
        if tool_count > 0:
            capabilities["reasoning"] = True
            descriptions.append("🧩 Reasoning About Outputs")
        
        # Parallel execution (if tools were executed concurrently)
        if self._detect_parallel_execution(tool_results):
            capabilities["parallel_execution"] = True
            descriptions.append("⚡ Parallel Tool Execution")
        
        # Context awareness (based on message complexity)
        if self._detect_context_awareness(user_message, tool_results):
            capabilities["context_awareness"] = True
            descriptions.append("🎯 Context Awareness")
        
        # Calculate metrics
        success_rate = successful_tools / max(tool_count, 1)
        average_time = self._calculate_average_execution_time(tool_results)
        
        return {
            "capabilities": capabilities,
            "descriptions": descriptions,
            "tool_count": tool_count,
            "successful_tools": successful_tools,
            "failed_tools": failed_tools,
            "success_rate": success_rate,
            "average_execution_time": average_time,
            "capability_score": self._calculate_capability_score(capabilities)
        }
    
    def _detect_parallel_execution(self, tool_results: List[Dict[str, Any]]) -> bool:
        """Detect if tools were executed in parallel"""
        if len(tool_results) < 2:
            return False
        
        # Check if execution times overlap significantly
        execution_times = []
        for result in tool_results:
            if "execution_time" in result:
                execution_times.append(result["execution_time"])
        
        if len(execution_times) < 2:
            return False
        
        # Simple heuristic: if execution times are similar, likely parallel
        max_time = max(execution_times)
        min_time = min(execution_times)
        
        # If max time is close to min time, likely parallel
        return max_time - min_time < max_time * 0.5
    
    def _detect_context_awareness(self, user_message: str, tool_results: List[Dict[str, Any]]) -> bool:
        """Detect context awareness based on message and tool usage"""
        # Check for references to previous context
        context_indicators = [
            "previous", "earlier", "before", "last", "next", "then", "also",
            "additionally", "furthermore", "moreover", "however", "but"
        ]
        
        message_lower = user_message.lower()
        has_context_indicators = any(indicator in message_lower for indicator in context_indicators)
        
        # Check if tools are used in a contextually appropriate way
        contextual_tool_usage = len(tool_results) > 0 and any(
            self._is_contextual_tool_usage(result) for result in tool_results
        )
        
        return has_context_indicators or contextual_tool_usage
    
    def _is_contextual_tool_usage(self, tool_result: Dict[str, Any]) -> bool:
        """Check if tool usage appears contextual"""
        # This is a simplified heuristic
        # In practice, this would analyze tool arguments and results
        return tool_result.get("success", False) and "args" in tool_result
    
    def _calculate_average_execution_time(self, tool_results: List[Dict[str, Any]]) -> float:
        """Calculate average execution time for tools"""
        times = [r.get("execution_time", 0) for r in tool_results if "execution_time" in r]
        return sum(times) / len(times) if times else 0.0
    
    def _calculate_capability_score(self, capabilities: Dict[str, bool]) -> float:
        """Calculate overall capability score"""
        if not capabilities:
            return 0.0
        
        total_weight = 0.0
        achieved_weight = 0.0
        
        for cap_name, achieved in capabilities.items():
            if cap_name in self.capability_definitions:
                weight = self.capability_definitions[cap_name]["weight"]
                total_weight += weight
                if achieved:
                    achieved_weight += weight
        
        return achieved_weight / total_weight if total_weight > 0 else 0.0
    
    def _record_tool_usage(self, tool_result: Dict[str, Any], session_id: str = None):
        """Record tool usage for statistics"""
        usage_record = {
            "timestamp": datetime.now(),
            "session_id": session_id,
            "tool_name": tool_result.get("tool_name", "unknown"),
            "success": tool_result.get("success", False),
            "execution_time": tool_result.get("execution_time", 0.0),
            "args": tool_result.get("args", {}),
            "error": tool_result.get("error")
        }
        
        self.tool_usage_history.append(usage_record)
    
    def _update_session_stats(self, session_id: str, capabilities: Dict[str, Any], 
                            tool_results: List[Dict[str, Any]]):
        """Update session-specific statistics"""
        if session_id not in self.session_stats:
            self.session_stats[session_id] = {
                "total_interactions": 0,
                "total_tools": 0,
                "capability_demonstrations": defaultdict(int),
                "tool_usage": defaultdict(int),
                "success_rate": 0.0,
                "first_interaction": datetime.now(),
                "last_interaction": datetime.now()
            }
        
        stats = self.session_stats[session_id]
        stats["total_interactions"] += 1
        stats["total_tools"] += len(tool_results)
        stats["last_interaction"] = datetime.now()
        
        # Update capability demonstrations
        for cap_name in capabilities.get("capabilities", {}):
            if capabilities["capabilities"][cap_name]:
                stats["capability_demonstrations"][cap_name] += 1
        
        # Update tool usage
        for result in tool_results:
            tool_name = result.get("tool_name", "unknown")
            stats["tool_usage"][tool_name] += 1
        
        # Update success rate
        successful_tools = len([r for r in tool_results if r.get("success", False)])
        if stats["total_tools"] > 0:
            stats["success_rate"] = (stats["success_rate"] * (stats["total_tools"] - len(tool_results)) + 
                                   successful_tools) / stats["total_tools"]
    
    def get_capability_metrics(self, time_window: timedelta = None) -> Dict[str, CapabilityMetrics]:
        """Get capability metrics for the specified time window"""
        if time_window:
            cutoff_time = datetime.now() - time_window
            recent_records = [r for r in self.capability_history if r["timestamp"] > cutoff_time]
        else:
            recent_records = self.capability_history
        
        metrics = {}
        
        for cap_name, cap_def in self.capability_definitions.items():
            demonstrations = [r for r in recent_records 
                            if r["capabilities"].get("capabilities", {}).get(cap_name, False)]
            
            if demonstrations:
                count = len(demonstrations)
                success_rate = sum(1 for r in demonstrations 
                                 if r["capabilities"].get("success_rate", 0) > 0.5) / count
                
                avg_time = sum(r["capabilities"].get("average_execution_time", 0) 
                             for r in demonstrations) / count
                
                last_demo = max(r["timestamp"] for r in demonstrations)
                
                examples = [{
                    "timestamp": r["timestamp"].isoformat(),
                    "user_message": r["user_message"][:100] + "...",
                    "tool_count": r["tool_count"]
                } for r in demonstrations[-3:]]  # Last 3 examples
                
                metrics[cap_name] = CapabilityMetrics(
                    name=cap_name,
                    count=count,
                    success_rate=success_rate,
                    average_execution_time=avg_time,
                    last_demonstrated=last_demo,
                    examples=examples
                )
        
        return metrics
    
    def get_tool_usage_stats(self, time_window: timedelta = None) -> Dict[str, ToolUsageStats]:
        """Get tool usage statistics"""
        if time_window:
            cutoff_time = datetime.now() - time_window
            recent_usage = [r for r in self.tool_usage_history if r["timestamp"] > cutoff_time]
        else:
            recent_usage = self.tool_usage_history
        
        tool_stats = defaultdict(lambda: {
            "usage_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "execution_times": [],
            "last_used": None,
            "args_counter": Counter()
        })
        
        for usage in recent_usage:
            tool_name = usage["tool_name"]
            stats = tool_stats[tool_name]
            
            stats["usage_count"] += 1
            if usage["success"]:
                stats["success_count"] += 1
            else:
                stats["failure_count"] += 1
            
            if usage["execution_time"] > 0:
                stats["execution_times"].append(usage["execution_time"])
            
            if not stats["last_used"] or usage["timestamp"] > stats["last_used"]:
                stats["last_used"] = usage["timestamp"]
            
            # Count argument patterns
            for key, value in usage.get("args", {}).items():
                stats["args_counter"][f"{key}={value}"] += 1
        
        # Convert to ToolUsageStats objects
        result = {}
        for tool_name, stats in tool_stats.items():
            success_rate = stats["success_count"] / max(stats["usage_count"], 1)
            avg_time = sum(stats["execution_times"]) / max(len(stats["execution_times"]), 1)
            
            tool_stats_obj = ToolUsageStats(
                tool_name=tool_name,
                usage_count=stats["usage_count"],
                success_count=stats["success_count"],
                failure_count=stats["failure_count"],
                success_rate=success_rate,
                average_execution_time=avg_time,
                last_used=stats["last_used"],
                common_args=dict(stats["args_counter"].most_common(5))
            )
            
            result[tool_name] = tool_stats_obj.to_dict()
        
        return result
    
    def get_session_analysis(self, session_id: str) -> Dict[str, Any]:
        """Get detailed analysis for a specific session"""
        if session_id not in self.session_stats:
            return {"error": "Session not found"}
        
        stats = self.session_stats[session_id]
        
        # Get capability demonstrations for this session
        session_records = [r for r in self.capability_history if r.get("session_id") == session_id]
        
        return {
            "session_id": session_id,
            "total_interactions": stats["total_interactions"],
            "total_tools": stats["total_tools"],
            "success_rate": stats["success_rate"],
            "duration_minutes": (stats["last_interaction"] - stats["first_interaction"]).total_seconds() / 60,
            "capability_demonstrations": dict(stats["capability_demonstrations"]),
            "most_used_tools": dict(Counter(stats["tool_usage"]).most_common(5)),
            "recent_interactions": len(session_records)
        }
    
    def get_system_analysis(self) -> Dict[str, Any]:
        """Get overall system analysis"""
        total_sessions = len(self.session_stats)
        total_interactions = sum(stats["total_interactions"] for stats in self.session_stats.values())
        total_tools = sum(stats["total_tools"] for stats in self.session_stats.values())
        
        # Overall success rate
        overall_success_rate = sum(stats["success_rate"] * stats["total_tools"] 
                                 for stats in self.session_stats.values()) / max(total_tools, 1)
        
        # Capability demonstration across all sessions
        all_capabilities = defaultdict(int)
        for stats in self.session_stats.values():
            for cap_name, count in stats["capability_demonstrations"].items():
                all_capabilities[cap_name] += count
        
        return {
            "total_sessions": total_sessions,
            "total_interactions": total_interactions,
            "total_tools": total_tools,
            "overall_success_rate": overall_success_rate,
            "capability_demonstrations": dict(all_capabilities),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def clear_history(self):
        """Clear all analysis history"""
        self.tool_usage_history.clear()
        self.capability_history.clear()
        self.session_stats.clear()
        logger.info("🧹 [CAPABILITY_ANALYZER] Analysis history cleared")