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

from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# HTTPBearer automatically handles the Authorization header parsing
# and returns 401 if the header is missing or malformed
security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify Bearer token against the configured backend token.
    
    This dependency automatically:
    - Returns 401 if Authorization header is missing
    - Returns 401 if Authorization header is malformed
    - Returns 403 if token is invalid
    
    Args:
        credentials: Automatically extracted from Authorization header
        
    Returns:
        The validated token string
        
    Raises:
        HTTPException: 403 if token is invalid
    """
    settings = get_settings()
    
    if credentials.credentials != settings.backend_token:
        logger.warning(f"Invalid token attempt from credential")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication token"
        )
    
    return credentials.credentials
