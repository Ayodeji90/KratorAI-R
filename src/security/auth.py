"""Bearer token authentication for KratorAI backend.

This module provides a simple, lightweight authentication mechanism using
Bearer tokens. The token is validated against an environment variable.

Usage:
    from fastapi import Depends
    from src.security.auth import verify_token
    
    @router.post("/protected", dependencies=[Depends(verify_token)])
    async def protected_endpoint():
        return {"message": "Access granted"}
"""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# HTTPBearer automatically handles the Authorization header parsing
# Set auto_error=False to handle missing headers manually (needed for dev bypass)
security = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> str:
    """
    Verify Bearer token against the configured backend token.
    
    This dependency automatically:
    - Bypasses check if environment is 'development'
    - Returns 401 if Authorization header is missing (in prod)
    - Returns 403 if token is invalid
    
    Args:
        credentials: Automatically extracted from Authorization header
        
    Returns:
        The validated token string (or dummy token in dev)
        
    Raises:
        HTTPException: 401/403 if authentication fails
    """
    settings = get_settings()
    
    # Bypass authentication in development
    if settings.environment == "development" or settings.debug:
        return settings.backend_token
        
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != settings.backend_token:
        logger.warning(f"Invalid token attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication token"
        )
    
    return credentials.credentials
