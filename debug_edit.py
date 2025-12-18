import asyncio
import base64
from src.services.gemini_client import get_gemini_client
import os

async def main():
    # Create a dummy image
    img_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    with open("test_image.png", "wb") as f:
        f.write(img_data)
    
    client = get_gemini_client()
    
    try:
        print("Sending edit request...")
        # We use a simple prompt that shouldn't be blocked
        result = await client.edit_image(
            image_uri="test_image.png",
            prompt="Make it blue",
            edit_type="color_swap"
        )
        
        print("Response keys:", result.keys())
        if "candidates" in result:
            candidates = result["candidates"]
            if candidates:
                print("Candidate 0 parts:", len(candidates[0].content.parts))
                part = candidates[0].content.parts[0]
                if hasattr(part, "inline_data"):
                    print("Has inline_data:", True)
                    print("Mime type:", part.inline_data.mime_type)
                    print("Data length:", len(part.inline_data.data))
                else:
                    print("Has inline_data:", False)
                    if hasattr(part, "text"):
                        print("Text:", part.text)
            else:
                print("No candidates")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists("test_image.png"):
            os.remove("test_image.png")

if __name__ == "__main__":
    asyncio.run(main())
