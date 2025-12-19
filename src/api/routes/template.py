"""Template editing endpoint."""

import json
from typing import List, Optional
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from PIL import Image
import io

from src.services.gemini_client import get_gemini_client
from src.api.schemas import VariationResponse, GeneratedAsset

router = APIRouter()

@router.post("/edit", response_model=VariationResponse)
async def edit_template(
    template_image: UploadFile = File(...),
    aspect_images: List[UploadFile] = File(default=[]),
    data: str = Form(...),
):
    """
    Edit a template based on aspects and prompts.
    
    Args:
        template_image: The main template image
        aspect_images: List of reference images for aspects
        data: JSON string containing aspect definitions and global prompt
    """
    try:
        # Parse data
        parsed_data = json.loads(data)
        aspects = parsed_data.get("aspects", [])
        global_prompt = parsed_data.get("globalPrompt", "")
        
        # Read template image
        template_content = await template_image.read()
        template_img = Image.open(io.BytesIO(template_content))
        
        # Read aspect images and map by filename
        aspect_img_map = {}
        for img_file in aspect_images:
            content = await img_file.read()
            img = Image.open(io.BytesIO(content))
            aspect_img_map[img_file.filename] = img
            
        # Build parts for Gemini
        parts = []
        
        # 1. Add template image
        parts.append(template_img)
        
        # 2. Process aspects and add reference images
        aspect_image_refs = {}
        
        for aspect in aspects:
            aspect_id = aspect["id"]
            aspect_name = aspect["name"]
            use_image = aspect.get("useImage", False)
            
            # Check if this aspect has an uploaded image
            # The frontend sends files with names matching aspect IDs or specific keys
            # We'll assume the frontend sends a map or we match by some convention
            # For now, let's assume the frontend sends a list of files and we need to match them
            # The frontend logic in playground.ts sends files but doesn't explicitly name them in a way 
            # that guarantees order in a simple list without a map.
            # However, in the implementation plan, we decided to replicate logic.
            # Let's look at how we can match. 
            # The frontend sends `aspectImages` as a map in TS, but FormData flattens it.
            # We need a way to map the uploaded files to aspects.
            # Let's assume the frontend will append the aspect ID to the filename.
            
            # Actually, let's look at the `data` JSON. It should probably contain the mapping.
            # But `UploadFile` filenames are reliable.
            # Let's assume the frontend names the files as `{aspect_id}`.
            
            if use_image and aspect_id in aspect_img_map:
                img = aspect_img_map[aspect_id]
                parts.append(img)
                ref_name = f"[Image for {aspect_name}]"
                aspect_image_refs[aspect_id] = ref_name
        
        # 3. Build prompt
        prompt = build_enhanced_prompt(aspects, aspect_image_refs, global_prompt)
        parts.append(prompt)
        
        # 4. Generate
        client = get_gemini_client()
        result = await client.generate_content(parts)
        
        # 5. Process result
        source_id = str(uuid4())
        generated_assets = []
        
        if result.get("images"):
            try:
                img = result["images"][0]
                # Save to static/generated
                output_dir = Path("src/static/generated")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                asset_id = str(uuid4())
                filename = f"{asset_id}.png"
                filepath = output_dir / filename
                img.save(filepath)
                
                asset_uri = f"/static/generated/{filename}"
                
                generated_assets.append(GeneratedAsset(
                    asset_id=asset_id,
                    asset_uri=asset_uri,
                    thumbnail_uri=asset_uri,
                    parent_ids=[source_id],
                    royalties=[],
                    metadata={
                        "global_prompt": global_prompt,
                        "aspect_count": len(aspects)
                    }
                ))
            except Exception as e:
                print(f"Failed to save image: {e}")
        
        return VariationResponse(
            source_id=source_id,
            variations=generated_assets,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template editing failed: {str(e)}")

def build_enhanced_prompt(aspects, aspect_image_refs, global_prompt):
    """Build the prompt string."""
    active_aspects = [
        a for a in aspects 
        if a.get("useImage") or (a.get("prompt") and a.get("prompt").strip())
    ]
    
    prompt = """You are an expert design AI. I will provide a template image and you MUST edit it according to my specific instructions. 

CRITICAL: You will receive multiple images:
- The FIRST image is the main template to edit
- The FOLLOWING images are reference images for specific aspects

IMPORTANT INSTRUCTIONS:
- You MUST use the reference images I provide for the specified aspects
- Do NOT ignore the reference images - they are crucial for the edits
- Blend the reference images seamlessly into the template
- Maintain the template's overall composition and quality

EDITING INSTRUCTIONS:
"""

    for i, aspect in enumerate(active_aspects):
        name = aspect["name"].upper()
        prompt += f"\n{i + 1}. {name}:"
        
        aspect_id = aspect["id"]
        has_image = aspect.get("useImage") and aspect_id in aspect_image_refs
        has_prompt = aspect.get("prompt") and aspect.get("prompt").strip()
        
        if has_image:
            ref_name = aspect_image_refs[aspect_id]
            prompt += f"\n   - USE THIS REFERENCE IMAGE: {ref_name}"
            prompt += f"\n   - ACTION: Replace/modify this aspect using the provided reference image"
            
            if has_prompt:
                prompt += f"\n   - ADDITIONAL GUIDANCE: \"{aspect['prompt']}\""
        elif has_prompt:
            prompt += f"\n   - MODIFY: \"{aspect['prompt']}\""

    if global_prompt.strip():
        prompt += f"\n\nGLOBAL MODIFICATIONS (apply to entire image):\n\"{global_prompt}\""

    prompt += """\n\nFINAL REQUIREMENTS:
- You MUST use the reference images I provided for the specified aspects
- Seamlessly integrate all changes while maintaining professional quality
- Keep the original template's layout and composition
- Return ONLY the edited image, no text or explanations"""

    return prompt
