"""
Bot Manager for Demo MCP System
Manages bot interactions and query processing
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BotManager:
    """Manages bot interactions and query processing"""
    
    def __init__(self):
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.session_timeout = 1800  # 30 minutes
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired conversation sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, history in self.conversation_history.items():
            if history:
                last_message_time = datetime.fromisoformat(history[-1]["timestamp"])
                if (current_time - last_message_time).seconds > self.session_timeout:
                    expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.conversation_history[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
    
    def _add_to_history(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add message to conversation history"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.conversation_history[session_id].append(message)
        
        # Keep only last 50 messages per session
        if len(self.conversation_history[session_id]) > 50:
            self.conversation_history[session_id] = self.conversation_history[session_id][-50:]
    
    def _get_conversation_context(self, session_id: str, max_messages: int = 10) -> str:
        """Get recent conversation context"""
        if session_id not in self.conversation_history:
            return ""
        
        recent_messages = self.conversation_history[session_id][-max_messages:]
        context = "Recent conversation:\n"
        
        for message in recent_messages:
            role = "User" if message["role"] == "user" else "Bot"
            context += f"{role}: {message['content']}\n"
        
        return context
    
    async def process_query(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process user query with bot"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Cleanup expired sessions
        self._cleanup_expired_sessions()
        
        # Add user message to history
        self._add_to_history(session_id, "user", query)
        
        # Check cache first (if cache manager is available)
        try:
            from .cache_manager import CacheManager
            cache_manager = CacheManager()
            cached_response = cache_manager.get_user_cache(session_id, query)
            if cached_response:
                self._add_to_history(session_id, "bot", cached_response, {"source": "cache"})
                return {
                    "response": cached_response,
                    "source": "cache",
                    "session_id": session_id
                }
        except ImportError:
            pass
        
        # Generate response
        response = await self._generate_response(query, session_id)
        
        # Add bot response to history
        self._add_to_history(session_id, "bot", response, {"source": "llm"})
        
        # Cache response (if cache manager is available)
        try:
            cache_manager.set_user_cache(session_id, query, response)
        except:
            pass
        
        return {
            "response": response,
            "source": "llm",
            "session_id": session_id
        }
    
    async def _generate_response(self, query: str, session_id: str) -> str:
        """Generate response using simulated LLM"""
        query_lower = query.lower()
        
        # Get conversation context
        context = self._get_conversation_context(session_id)
        
        # Simple keyword-based responses for demo
        if "balance" in query_lower or "account" in query_lower:
            return "I can help you check your account balance. Would you like me to execute the 'Account Balance Inquiry' use case? This will retrieve your current balance and recent transactions."
        elif "payment" in query_lower or "transfer" in query_lower or "send money" in query_lower:
            return "I can assist with payment processing. Would you like me to execute the 'Payment Processing' use case? This includes validation, fraud checking, and confirmation."
        elif "portfolio" in query_lower or "investment" in query_lower or "stocks" in query_lower:
            return "I can analyze your portfolio. Would you like me to execute the 'Portfolio Analysis' use case? This will provide performance insights and recommendations."
        elif "login" in query_lower or "authenticate" in query_lower or "sign in" in query_lower:
            return "I can help with authentication. Would you like me to execute the 'User Authentication Flow' use case? This includes login, verification, and session management."
        elif "risk" in query_lower or "assessment" in query_lower:
            return "I can perform risk assessment. Would you like me to execute the 'Risk Assessment' use case? This will analyze your investment risk and provide recommendations."
        elif "support" in query_lower or "help" in query_lower or "ticket" in query_lower:
            return "I can help with customer support. Would you like me to execute the 'Customer Support Ticket' use case? This will create and manage support tickets."
        elif "hello" in query_lower or "hi" in query_lower or "hey" in query_lower:
            return "Hello! I'm your intelligent assistant. I can help you with account balance, payments, portfolio analysis, authentication, risk assessment, or customer support. What would you like to do today?"
        elif "help" in query_lower or "what can you do" in query_lower:
            return """I can help you with several financial operations:

🔐 **Authentication**: Login and session management
💰 **Account Balance**: Check balances and transactions  
💳 **Payments**: Process payments and transfers
📊 **Portfolio Analysis**: Analyze investment performance
⚠️ **Risk Assessment**: Evaluate investment risks
🎫 **Support**: Create and manage support tickets

Which service would you like to use?"""
        elif "thank" in query_lower or "thanks" in query_lower:
            return "You're welcome! I'm here to help with any financial operations you need. Just let me know what you'd like to do next."
        else:
            return f"""I understand you're asking about: "{query}"

I can help you with:
- **Account Balance**: Check your account balance and transactions
- **Payments**: Process payments and transfers  
- **Portfolio Analysis**: Analyze your investment portfolio
- **Authentication**: Help with login and security
- **Risk Assessment**: Evaluate investment risks
- **Customer Support**: Create support tickets

Which of these would you like to explore?"""
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for session"""
        return self.conversation_history.get(session_id, [])
    
    def clear_conversation(self, session_id: str) -> None:
        """Clear conversation history for session"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
            logger.info(f"Cleared conversation history for session: {session_id}")
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.conversation_history.keys())
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        if session_id not in self.conversation_history:
            return {"error": "Session not found"}
        
        history = self.conversation_history[session_id]
        
        user_messages = [msg for msg in history if msg["role"] == "user"]
        bot_messages = [msg for msg in history if msg["role"] == "bot"]
        
        return {
            "session_id": session_id,
            "total_messages": len(history),
            "user_messages": len(user_messages),
            "bot_messages": len(bot_messages),
            "first_message": history[0]["timestamp"] if history else None,
            "last_message": history[-1]["timestamp"] if history else None,
            "session_duration": self._calculate_session_duration(history)
        }
    
    def _calculate_session_duration(self, history: List[Dict[str, Any]]) -> str:
        """Calculate session duration"""
        if len(history) < 2:
            return "0 minutes"
        
        first_time = datetime.fromisoformat(history[0]["timestamp"])
        last_time = datetime.fromisoformat(history[-1]["timestamp"])
        duration = last_time - first_time
        
        if duration.days > 0:
            return f"{duration.days} days, {duration.seconds // 3600} hours"
        elif duration.seconds > 3600:
            return f"{duration.seconds // 3600} hours, {(duration.seconds % 3600) // 60} minutes"
        else:
            return f"{duration.seconds // 60} minutes"
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """Get overall bot statistics"""
        total_sessions = len(self.conversation_history)
        total_messages = sum(len(history) for history in self.conversation_history.values())
        
        user_messages = 0
        bot_messages = 0
        
        for history in self.conversation_history.values():
            for message in history:
                if message["role"] == "user":
                    user_messages += 1
                else:
                    bot_messages += 1
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "bot_messages": bot_messages,
            "average_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
            "active_sessions": len(self.conversation_history)
        }
