#!/usr/bin/env python3
"""
Conversation Manager - Modular Context Handling
==============================================
Manages conversation history, context, and state for multi-turn interactions.
Provides intelligent context management and conversation flow control.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Represents a single message in the conversation"""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    tool_calls: List[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary representation"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata"),
            tool_calls=data.get("tool_calls")
        )

@dataclass
class ConversationContext:
    """Represents the current conversation context"""
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = None
    last_activity: datetime = None
    message_count: int = 0
    tool_usage_count: int = 0
    context_summary: str = ""
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()

class ConversationManager:
    """Manages conversation state and context"""
    
    def __init__(self, max_history: int = 50, context_window: int = 10):
        self.max_history = max_history
        self.context_window = context_window
        self.conversations: Dict[str, List[Message]] = {}
        self.contexts: Dict[str, ConversationContext] = {}
        self.active_sessions: set = set()
    
    def start_conversation(self, session_id: str, user_id: str = None) -> ConversationContext:
        """Start a new conversation"""
        logger.info(f"🔄 [CONVERSATION] Starting conversation for session: {session_id}")
        
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id
        )
        
        self.contexts[session_id] = context
        self.conversations[session_id] = []
        self.active_sessions.add(session_id)
        
        logger.info(f"✅ [CONVERSATION] Conversation started for session: {session_id}")
        return context
    
    def end_conversation(self, session_id: str):
        """End a conversation"""
        logger.info(f"🔄 [CONVERSATION] Ending conversation for session: {session_id}")
        
        if session_id in self.active_sessions:
            self.active_sessions.remove(session_id)
        
        # Optionally save conversation to persistent storage
        self._save_conversation(session_id)
        
        logger.info(f"✅ [CONVERSATION] Conversation ended for session: {session_id}")
    
    def add_message(self, session_id: str, role: str, content: str, 
                   metadata: Dict[str, Any] = None, tool_calls: List[Dict[str, Any]] = None) -> Message:
        """Add a message to the conversation"""
        if session_id not in self.conversations:
            self.start_conversation(session_id)
        
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
            tool_calls=tool_calls
        )
        
        self.conversations[session_id].append(message)
        self._update_context(session_id, message)
        
        # Trim conversation if it exceeds max history
        if len(self.conversations[session_id]) > self.max_history:
            self.conversations[session_id] = self.conversations[session_id][-self.max_history:]
        
        logger.info(f"💬 [CONVERSATION] Added {role} message to session {session_id}")
        return message
    
    def get_conversation_history(self, session_id: str, 
                                include_metadata: bool = False) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        if session_id not in self.conversations:
            return []
        
        messages = self.conversations[session_id]
        
        if include_metadata:
            return [msg.to_dict() for msg in messages]
        else:
            return [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
    
    def get_context_window(self, session_id: str, 
                          window_size: int = None) -> List[Dict[str, Any]]:
        """Get recent conversation context within the specified window"""
        if session_id not in self.conversations:
            return []
        
        window_size = window_size or self.context_window
        messages = self.conversations[session_id]
        
        # Get the last window_size messages
        recent_messages = messages[-window_size:] if len(messages) > window_size else messages
        
        return [{"role": msg.role, "content": msg.content} for msg in recent_messages]
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation"""
        if session_id not in self.conversations:
            return {"error": "Conversation not found"}
        
        context = self.contexts.get(session_id)
        messages = self.conversations[session_id]
        
        # Count message types
        message_counts = {}
        for msg in messages:
            message_counts[msg.role] = message_counts.get(msg.role, 0) + 1
        
        # Count tool usage
        tool_usage = 0
        for msg in messages:
            if msg.tool_calls:
                tool_usage += len(msg.tool_calls)
        
        return {
            "session_id": session_id,
            "message_count": len(messages),
            "message_counts": message_counts,
            "tool_usage_count": tool_usage,
            "duration_minutes": (datetime.now() - context.created_at).total_seconds() / 60,
            "last_activity": context.last_activity.isoformat(),
            "context_summary": context.context_summary
        }
    
    def update_context_summary(self, session_id: str, summary: str):
        """Update the context summary for a conversation"""
        if session_id in self.contexts:
            self.contexts[session_id].context_summary = summary
            logger.info(f"📝 [CONVERSATION] Updated context summary for session {session_id}")
    
    def clear_conversation(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.conversations:
            self.conversations[session_id] = []
            if session_id in self.contexts:
                self.contexts[session_id].message_count = 0
                self.contexts[session_id].tool_usage_count = 0
                self.contexts[session_id].context_summary = ""
            
            logger.info(f"🧹 [CONVERSATION] Cleared conversation for session {session_id}")
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.active_sessions)
    
    def get_session_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get conversation context for a session"""
        return self.contexts.get(session_id)
    
    def _update_context(self, session_id: str, message: Message):
        """Update conversation context with new message"""
        if session_id not in self.contexts:
            return
        
        context = self.contexts[session_id]
        context.last_activity = datetime.now()
        context.message_count = len(self.conversations[session_id])
        
        if message.tool_calls:
            context.tool_usage_count += len(message.tool_calls)
    
    def _save_conversation(self, session_id: str):
        """Save conversation to persistent storage (placeholder)"""
        # This would implement actual persistence
        logger.info(f"💾 [CONVERSATION] Saving conversation for session {session_id}")
    
    def export_conversation(self, session_id: str, format: str = "json") -> Union[str, Dict[str, Any]]:
        """Export conversation in specified format"""
        if session_id not in self.conversations:
            return {"error": "Conversation not found"}
        
        conversation_data = {
            "session_id": session_id,
            "context": asdict(self.contexts.get(session_id)),
            "messages": [msg.to_dict() for msg in self.conversations[session_id]]
        }
        
        if format == "json":
            return json.dumps(conversation_data, indent=2)
        else:
            return conversation_data
    
    def import_conversation(self, session_id: str, conversation_data: Union[str, Dict[str, Any]]):
        """Import conversation from external source"""
        try:
            if isinstance(conversation_data, str):
                data = json.loads(conversation_data)
            else:
                data = conversation_data
            
            # Reconstruct context
            context_data = data.get("context", {})
            context = ConversationContext(
                session_id=session_id,
                user_id=context_data.get("user_id"),
                created_at=datetime.fromisoformat(context_data.get("created_at", datetime.now().isoformat())),
                last_activity=datetime.fromisoformat(context_data.get("last_activity", datetime.now().isoformat())),
                message_count=context_data.get("message_count", 0),
                tool_usage_count=context_data.get("tool_usage_count", 0),
                context_summary=context_data.get("context_summary", "")
            )
            
            # Reconstruct messages
            messages = []
            for msg_data in data.get("messages", []):
                message = Message.from_dict(msg_data)
                messages.append(message)
            
            self.contexts[session_id] = context
            self.conversations[session_id] = messages
            self.active_sessions.add(session_id)
            
            logger.info(f"📥 [CONVERSATION] Imported conversation for session {session_id}")
            
        except Exception as e:
            logger.error(f"❌ [CONVERSATION] Failed to import conversation: {e}")
            raise