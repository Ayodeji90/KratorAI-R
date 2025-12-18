"""
Simple in-memory rate limiting for KratorAI API.
"""

import time
from collections import defaultdict
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests based on IP address.
    
    Uses a sliding window algorithm.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_limit: int = 10,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check and static files
        if request.url.path == "/health" or request.url.path.startswith("/static"):
            return await call_next(request)
            
        client_ip = request.client.host
        now = time.time()
        
        # Clean up old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < 60
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )
            
        # Add current request
        self.requests[client_ip].append(now)
        
        return await call_next(request)
