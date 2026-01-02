import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "gemini-integration"))

from src.agent.krator_agent import KratorAgent
from src.services.flux_client import FluxClient

async def test_flux_generation():
    print("Testing FLUX.1 Generation Integration...")
    
    # Mock the FluxClient to avoid real API calls during this initial check
    # We want to verify the agent calls the client correctly
    with patch("src.services.flux_client.FluxClient.generate_image") as mock_generate:
        # Setup mock response
        mock_generate.return_value = {
            "data": [{"url": "https://example.com/flux-generated-image.png"}]
        }
        
        agent = KratorAgent()
        
        # Test Generation
        print("1. Testing _handle_generate_image...")
        result = await agent._handle_generate_image(prompt="A futuristic African city", style="creative")
        
        if result["success"] and result["image"]["uri"] == "https://example.com/flux-generated-image.png":
            print("✅ Generation Test Passed")
        else:
            print(f"❌ Generation Test Failed: {result}")
            
        # Verify mock was called with expected args
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args[1]
        print(f"   Called with: {call_args}")

async def test_flux_edit():
    print("\nTesting FLUX.1 Edit Integration...")
    
    with patch("src.services.flux_client.FluxClient.edit_image") as mock_edit:
        mock_edit.return_value = {
            "data": [{"url": "https://example.com/flux-edited-image.png"}]
        }
        
        agent = KratorAgent()
        
        # Inject a fake image into memory so we can edit it
        from src.agent.memory import ImageReference
        agent.memory.add_image(ImageReference(
            image_id="test-img-1",
            uri="https://example.com/original.png",
            source="upload"
        ))
        
        # Test Edit
        print("2. Testing _handle_edit_image...")
        result = await agent._handle_edit_image(image_id="test-img-1", instruction="Make it night time")
        
        if result["success"] and result["image"]["uri"] == "https://example.com/flux-edited-image.png":
            print("✅ Edit Test Passed")
        else:
            print(f"❌ Edit Test Failed: {result}")

if __name__ == "__main__":
    asyncio.run(test_flux_generation())
    asyncio.run(test_flux_edit())
