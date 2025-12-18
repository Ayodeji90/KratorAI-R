from fastapi import APIRouter, UploadFile, File, HTTPException
from src.services.gemini_client import get_gemini_client
from src.api.schemas.describe import DescribeResponse
import base64

router = APIRouter()

@router.post("/describe", response_model=DescribeResponse)
async def describe_design(file: UploadFile = File(...)):
    """
    Generate a brief description for an uploaded design/work.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        content = await file.read()
        # Create a temporary file-like object or pass base64 if client supports it.
        # The GeminiClient._load_images handles http, gs, and local paths.
        # We need to adapt it or use a lower-level method if we want to pass bytes directly,
        # OR we can save to a temp file.
        # Looking at GeminiClient._load_images, it uses PIL.Image.open().
        # We can modify GeminiClient to accept bytes or PIL Images directly, 
        # but for now let's see if we can use the existing generate_with_images method.
        # It takes URIs.
        
        # Actually, let's look at GeminiClient again.
        # It has a _load_images method that takes URIs.
        # But we have bytes here.
        # Let's modify GeminiClient to support direct PIL Image or bytes if possible, 
        # or we can just use the underlying genai model directly here for simplicity 
        # if we don't want to refactor the client right now.
        # However, it's better to use the client.
        
        # Let's check GeminiClient.generate_with_images again.
        # It calls _load_images.
        
        # I will implement a small helper here to handle the upload and use the client.
        # Wait, I can't easily pass bytes to generate_with_images because it expects URIs.
        # I should probably update GeminiClient to accept PIL images directly in a future refactor,
        # but for now, I'll just use the google.generativeai library directly in this route 
        # to avoid changing the shared client too much if not needed, 
        # OR I can save to a temp file.
        
        # Actually, looking at src/agent/krator_agent.py, it handles inline data.
        # The GeminiClient seems to be a wrapper that might be a bit restrictive for direct uploads
        # without saving to disk/cloud first.
        
        # Let's look at src/api/routes/agent.py. It uses agent.chat which handles inline data.
        # Maybe I should add a method to GeminiClient to generate from PIL images directly?
        # Yes, that would be cleaner.
        
        # For now, I will write the route to use the raw genai model for simplicity and speed,
        # similar to how the agent does it, but purely for description.
        
        import google.generativeai as genai
        from src.config import get_settings
        from PIL import Image
        import io

        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        image = Image.open(io.BytesIO(content))
        
        prompt = "Provide a brief, engaging description of this design or logo. Focus on the visual elements, style, and mood."
        
        response = model.generate_content([prompt, image])
        
        return DescribeResponse(description=response.text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
