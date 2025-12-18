"""
Pydantic schemas for the KratorAI agent API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatMessage(BaseModel):
    """A single message in the chat."""
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class ImageUpload(BaseModel):
    """Image data for upload."""
    data: str = Field(..., description="Base64 encoded image data")
    mime_type: str = Field(default="image/png", description="Image MIME type")
    filename: Optional[str] = Field(None, description="Original filename")


class ChatRequest(BaseModel):
    """Request schema for agent chat endpoint."""
    message: str = Field(..., description="User's message to the agent")
    session_id: Optional[str] = Field(None, description="Existing session ID to continue")
    images: Optional[list[ImageUpload]] = Field(None, description="Images to include with message")


class GeneratedImage(BaseModel):
    """Response schema for generated/edited images."""
    image_id: str = Field(..., description="Unique image identifier")
    uri: str = Field(..., description="Image storage URI")
    thumbnail_uri: Optional[str] = Field(None, description="Thumbnail URI")


class ToolCall(BaseModel):
    """Information about a tool call made by the agent."""
    name: str = Field(..., description="Tool name")
    args: dict = Field(default_factory=dict, description="Tool arguments")
    result: Optional[dict] = Field(None, description="Tool execution result")


class ChatResponse(BaseModel):
    """Response schema for agent chat endpoint."""
    session_id: str = Field(..., description="Session ID for continuing conversation")
    message: str = Field(..., description="Agent's response message")
    images: list[GeneratedImage] = Field(default_factory=list, description="Generated/edited images")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tools used in response")


class StreamChunk(BaseModel):
    """Schema for streaming response chunks."""
    type: str = Field(..., description="Chunk type: text_delta, image, tool_call, complete, error")
    content: Optional[str] = Field(None, description="Text content for text_delta")
    image: Optional[GeneratedImage] = Field(None, description="Image data if type is image")
    tool_call: Optional[ToolCall] = Field(None, description="Tool call if type is tool_call")
    error: Optional[str] = Field(None, description="Error message if type is error")


class SessionCreate(BaseModel):
    """Request to create a new session."""
    metadata: Optional[dict] = Field(None, description="Optional session metadata")


class SessionResponse(BaseModel):
    """Response with session information."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    image_count: int


class SessionHistory(BaseModel):
    """Full session history."""
    session_id: str
    messages: list[ChatMessage]
    images: list[GeneratedImage]
    created_at: datetime
    last_activity: datetime
