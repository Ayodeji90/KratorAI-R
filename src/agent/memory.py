"""
Conversation memory management for KratorAI agent.

Handles session-based context storage, conversation history,
and image reference tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class ImageReference:
    """Reference to an image in the conversation."""
    image_id: str
    uri: str
    thumbnail_uri: Optional[str] = None
    source: str = "upload"  # upload, generated, edited
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    images: list[ImageReference] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)


class ConversationMemory:
    """
    Manages conversation history and context for a KratorAI session.
    
    Tracks:
    - Full conversation history
    - Images uploaded/generated during session
    - Edit history for undo/redo capabilities
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid4())
        self.messages: list[Message] = []
        self.images: dict[str, ImageReference] = {}
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
    
    def add_user_message(
        self,
        content: str,
        images: Optional[list[ImageReference]] = None,
    ) -> Message:
        """Add a user message to the conversation."""
        message = Message(
            role="user",
            content=content,
            images=images or [],
        )
        self.messages.append(message)
        self._update_activity()
        
        # Track any new images
        for img in message.images:
            self.images[img.image_id] = img
        
        return message
    
    def add_assistant_message(
        self,
        content: str,
        images: Optional[list[ImageReference]] = None,
        tool_calls: Optional[list[dict]] = None,
        tool_results: Optional[list[dict]] = None,
    ) -> Message:
        """Add an assistant response to the conversation."""
        message = Message(
            role="assistant",
            content=content,
            images=images or [],
            tool_calls=tool_calls or [],
            tool_results=tool_results or [],
        )
        self.messages.append(message)
        self._update_activity()
        
        # Track any generated images
        for img in message.images:
            self.images[img.image_id] = img
        
        return message
    
    def add_image(self, image: ImageReference) -> None:
        """Register an image in the session."""
        self.images[image.image_id] = image
        self._update_activity()
    
    def get_image(self, image_id: str) -> Optional[ImageReference]:
        """Retrieve an image by ID."""
        return self.images.get(image_id)
    
    def get_latest_image(self) -> Optional[ImageReference]:
        """Get the most recently added image."""
        if not self.images:
            return None
        return max(self.images.values(), key=lambda x: x.created_at)
    
    def get_images_by_source(self, source: str) -> list[ImageReference]:
        """Get all images from a specific source (upload, generated, edited)."""
        return [img for img in self.images.values() if img.source == source]
    
    def get_conversation_history(
        self,
        max_messages: Optional[int] = None,
        include_system: bool = False,
    ) -> list[dict]:
        """
        Get conversation history in Gemini-compatible format.
        
        Returns list of dicts with 'role' and 'parts' keys.
        """
        messages = self.messages
        if not include_system:
            messages = [m for m in messages if m.role != "system"]
        if max_messages:
            messages = messages[-max_messages:]
        
        history = []
        for msg in messages:
            parts = [msg.content]
            # Note: Image parts would be added here for multimodal
            history.append({
                "role": "user" if msg.role == "user" else "model",
                "parts": parts,
            })
        
        return history
    
    def get_context_summary(self) -> str:
        """Generate a summary of the current session context."""
        image_count = len(self.images)
        message_count = len(self.messages)
        
        summary = f"Session {self.session_id[:8]}... | "
        summary += f"{message_count} messages | "
        summary += f"{image_count} images tracked"
        
        if self.images:
            latest = self.get_latest_image()
            if latest:
                summary += f" | Latest: {latest.image_id[:8]}..."
        
        return summary
    
    def clear(self) -> None:
        """Clear all conversation history and images."""
        self.messages.clear()
        self.images.clear()
        self._update_activity()
    
    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Serialize memory to dictionary for persistence."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "images": [img.image_id for img in m.images],
                    "tool_calls": m.tool_calls,
                    "tool_results": m.tool_results,
                }
                for m in self.messages
            ],
            "images": {
                img_id: {
                    "image_id": img.image_id,
                    "uri": img.uri,
                    "thumbnail_uri": img.thumbnail_uri,
                    "source": img.source,
                    "created_at": img.created_at.isoformat(),
                    "metadata": img.metadata,
                }
                for img_id, img in self.images.items()
            },
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMemory":
        """Deserialize memory from dictionary."""
        memory = cls(session_id=data["session_id"])
        memory.created_at = datetime.fromisoformat(data["created_at"])
        memory.last_activity = datetime.fromisoformat(data["last_activity"])
        
        # Restore images first
        for img_id, img_data in data.get("images", {}).items():
            memory.images[img_id] = ImageReference(
                image_id=img_data["image_id"],
                uri=img_data["uri"],
                thumbnail_uri=img_data.get("thumbnail_uri"),
                source=img_data.get("source", "upload"),
                created_at=datetime.fromisoformat(img_data["created_at"]),
                metadata=img_data.get("metadata", {}),
            )
        
        # Restore messages
        for msg_data in data.get("messages", []):
            msg_images = [
                memory.images[img_id]
                for img_id in msg_data.get("images", [])
                if img_id in memory.images
            ]
            memory.messages.append(Message(
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                images=msg_images,
                tool_calls=msg_data.get("tool_calls", []),
                tool_results=msg_data.get("tool_results", []),
            ))
        
        return memory


class SessionManager:
    """
    Manages multiple conversation sessions.
    
    Provides session creation, retrieval, and cleanup.
    """
    
    def __init__(self, max_sessions: int = 100, session_timeout_hours: int = 24):
        self.sessions: dict[str, ConversationMemory] = {}
        self.max_sessions = max_sessions
        self.session_timeout_hours = session_timeout_hours
    
    def create_session(self) -> ConversationMemory:
        """Create a new conversation session."""
        self._cleanup_old_sessions()
        
        session = ConversationMemory()
        self.sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationMemory]:
        """Retrieve an existing session."""
        return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationMemory:
        """Get existing session or create new one."""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self.create_session()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def _cleanup_old_sessions(self) -> None:
        """Remove expired sessions and enforce max limit."""
        now = datetime.utcnow()
        
        # Remove expired sessions
        expired = [
            sid for sid, session in self.sessions.items()
            if (now - session.last_activity).total_seconds() > self.session_timeout_hours * 3600
        ]
        for sid in expired:
            del self.sessions[sid]
        
        # Enforce max sessions limit (remove oldest)
        if len(self.sessions) >= self.max_sessions:
            oldest = min(self.sessions.values(), key=lambda s: s.last_activity)
            del self.sessions[oldest.session_id]


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
