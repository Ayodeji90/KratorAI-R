"""Azure OpenAI o3-mini client for reasoning and prompt refinement.

Uses Azure Chat Completions API:
- Endpoint: /openai/deployments/{deployment}/chat/completions
- API Version: 2025-01-01-preview or later
- Text-only (no images, o3-mini doesn't support vision)
- Messages format (not prompt)
"""

import json
from typing import Optional
from openai import AzureOpenAI
from src.config import get_settings


class O3MiniClient:
    """Client for Azure OpenAI o3-mini reasoning model (text-only)."""
    
    def __init__(self):
        """Initialize the Azure OpenAI o3-mini client."""
        settings = get_settings()
        
        if not settings.azure_openai_endpoint or not settings.azure_openai_key:
            self.client = None
            self.enabled = False
        else:
            # Azure OpenAI client with proper endpoint and API version
            self.client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_key,
                api_version=settings.azure_openai_api_version  # 2025-01-01-preview
            )
            self.deployment = settings.azure_openai_deployment  # o3-mini
            self.max_tokens = settings.openai_max_tokens
            self.temperature = settings.openai_temperature  # 0.0 for deterministic
            self.enabled = True
    
    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[dict] = None
    ) -> dict:
        """
        Generate a completion using Azure OpenAI o3-mini.
        
        Uses: /openai/deployments/o3-mini/chat/completions
        
        Args:
            system_prompt: System instruction
            user_prompt: User message (structured text/JSON, no images)
            response_format: Optional JSON schema for structured output
            
        Returns:
            Parsed JSON response or error dict
        """
        if not self.enabled:
            return {
                "error": "Azure OpenAI is not configured. Please add AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY to your .env file."
            }
        
        try:
            # Messages format (required for Chat Completions API)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}  # Text-only, no images
            ]
            
            # Prepare request kwargs (no sampling parameters for o3-mini)
            request_kwargs = {
                "model": self.deployment,  # Deployment name for Azure
                "messages": messages,
                "max_completion_tokens": self.max_tokens
            }
            
            # Add JSON mode if response format specified
            if response_format:
                request_kwargs["response_format"] = {"type": "json_object"}
            
            # Call Azure Chat Completions API
            # Endpoint: /openai/deployments/{deployment}/chat/completions
            # API Version: 2025-01-01-preview
            response = self.client.chat.completions.create(**request_kwargs)
            
            # Extract content
            content = response.choices[0].message.content
            
            # Parse JSON if requested
            if response_format:
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    return {
                        "error": f"Failed to parse JSON response: {e}",
                        "raw_content": content
                    }
            
            return {"content": content}
            
        except Exception as e:
            print(f"Azure OpenAI o3-mini error: {e}")
            return {"error": str(e)}


# Singleton
_o3_mini_client: Optional[O3MiniClient] = None

def get_o3_mini_client() -> O3MiniClient:
    """Get the singleton o3-mini client."""
    global _o3_mini_client
    if _o3_mini_client is None:
        _o3_mini_client = O3MiniClient()
    return _o3_mini_client
