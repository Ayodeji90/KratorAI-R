"""
Agent API routes for KratorAI.

Provides endpoints for:
- Chat-based interactions with the agent
- Session management
- Streaming responses
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import base64
import logging

from src.api.schemas.agent import (
    ChatRequest,
    ChatResponse,
    GeneratedImage,
    ToolCall,
    SessionCreate,
    SessionResponse,
    SessionHistory,
    ChatMessage,
)
from src.agent.krator_agent import get_agent, KratorAgent
from src.agent.memory import get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Send a message to the KratorAI agent and receive a response.
    
    The agent can:
    - Answer questions about image editing
    - Generate new images from descriptions
    - Edit existing images based on instructions
    - Enhance image quality
    - Blend multiple designs together
    """
    try:
        # Get or create agent for session
        agent = get_agent(request.session_id)
        
        # Prepare images if provided
        image_data = None
        if request.images:
            image_data = [
                {
                    "data": img.data,
                    "mime_type": img.mime_type,
                }
                for img in request.images
            ]
        
        # Process the message
        result = await agent.chat(
            message=request.message,
            images=image_data,
        )
        
        # Build response
        response_images = []
        for img in result.get("images", []):
            response_images.append(GeneratedImage(
                image_id=img.get("id", ""),
                uri=img.get("uri", ""),
                thumbnail_uri=img.get("thumbnail_uri"),
            ))
        
        tool_calls = []
        for tc in result.get("tool_calls", []):
            tool_calls.append(ToolCall(
                name=tc.get("name", ""),
                args=tc.get("args", {}),
            ))
        
        return ChatResponse(
            session_id=agent.session_id,
            message=result.get("text", ""),
            images=response_images,
            tool_calls=tool_calls,
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/chat/upload", response_model=ChatResponse)
async def chat_with_upload(
    file: UploadFile = File(..., description="Image file to process"),
    message: str = Form(default="What can you do with this image?"),
    session_id: Optional[str] = Form(None, description="Session ID"),
):
    """
    Upload an image and chat about it with the agent.
    
    This endpoint accepts multipart form data for direct file uploads,
    making it easy to integrate with web UIs.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read and encode the image
        content = await file.read()
        base64_data = base64.b64encode(content).decode("utf-8")
        
        # Get or create agent
        agent = get_agent(session_id)
        
        # Process with the image
        result = await agent.chat(
            message=message,
            images=[{
                "data": base64_data,
                "mime_type": file.content_type,
                "id": file.filename or "uploaded_image",
            }],
        )
        
        # Build response
        response_images = []
        for img in result.get("images", []):
            response_images.append(GeneratedImage(
                image_id=img.get("id", ""),
                uri=img.get("uri", ""),
            ))
        
        return ChatResponse(
            session_id=agent.session_id,
            message=result.get("text", ""),
            images=response_images,
            tool_calls=[],
        )
        
    except Exception as e:
        logger.error(f"Upload chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream the agent's response in real-time.
    
    Returns a server-sent events (SSE) stream with response chunks.
    """
    agent = get_agent(request.session_id)
    
    # Prepare images if provided
    image_data = None
    if request.images:
        image_data = [
            {"data": img.data, "mime_type": img.mime_type}
            for img in request.images
        ]
    
    async def generate():
        try:
            async for chunk in agent.chat_stream(request.message, image_data):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# =============================================================================
# Session Management
# =============================================================================

@router.post("/session", response_model=SessionResponse)
async def create_session(request: SessionCreate = None):
    """
    Create a new conversation session.
    
    Returns a session ID that can be used for subsequent chat requests.
    """
    session_manager = get_session_manager()
    session = session_manager.create_session()
    
    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        last_activity=session.last_activity,
        message_count=len(session.messages),
        image_count=len(session.images),
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Get information about an existing session.
    """
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        last_activity=session.last_activity,
        message_count=len(session.messages),
        image_count=len(session.images),
    )


@router.get("/session/{session_id}/history", response_model=SessionHistory)
async def get_session_history(session_id: str):
    """
    Get the full conversation history for a session.
    """
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = [
        ChatMessage(
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
        )
        for msg in session.messages
    ]
    
    images = [
        GeneratedImage(
            image_id=img.image_id,
            uri=img.uri,
            thumbnail_uri=img.thumbnail_uri,
        )
        for img in session.images.values()
    ]
    
    return SessionHistory(
        session_id=session.session_id,
        messages=messages,
        images=images,
        created_at=session.created_at,
        last_activity=session.last_activity,
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and clear its history.
    """
    session_manager = get_session_manager()
    
    if not session_manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "deleted", "session_id": session_id}
