"""FastAPI application for KratorAI Gemini Integration."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from src.config import get_settings
from src.api.routes import breed, refine, edit, agent, describe
from src.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

# Static files directory
STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    setup_logging(level="DEBUG" if settings.debug else "INFO", json_format=not settings.debug)
    
    logger.info(f"🚀 KratorAI Gemini API starting (debug={settings.debug})")
    yield
    # Shutdown
    logger.info("👋 KratorAI Gemini API shutting down")


app = FastAPI(
    title="KratorAI Gemini Integration",
    description="AI-powered design breeding, refining, and editing for African graphic designers",
    version="0.1.0",
    lifespan=lifespan,
)

from src.utils.rate_limit import RateLimitMiddleware

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

@app.middleware("http")
async def error_handling_middleware(request, call_next):
    """Global error handling middleware."""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."}
        )

# Include routers
app.include_router(breed.router, prefix="/breed", tags=["Design Breeding"])
app.include_router(refine.router, prefix="/refine", tags=["Design Refining"])
app.include_router(edit.router, prefix="/edit", tags=["Design Editing"])
app.include_router(agent.router, prefix="/agent", tags=["AI Agent"])
app.include_router(describe.router, prefix="", tags=["Design Description"])


@app.get("/")
async def root():
    """Redirect to the test UI."""
    return RedirectResponse(url="/static/index.html")


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "KratorAI Gemini Integration",
        "version": "0.2.0",
        "description": "AI-powered design breeding, refining, and editing for African graphic designers",
        "endpoints": {
            "/breed": "POST - Combine multiple designs into hybrid",
            "/refine": "POST - Generate variations with prompts",
            "/refine/upload": "POST - Upload image and refine with prompt",
            "/edit": "POST - Targeted inpainting/style transfer",
            "/agent/chat": "POST - Chat with KratorAI agent",
            "/agent/chat/upload": "POST - Upload image and chat",
            "/agent/chat/stream": "POST - Streaming chat responses",
            "/agent/session": "POST/GET/DELETE - Session management",
            "/health": "GET - Health check",
        },
        "docs": "/docs",
        "test_ui": "/static/index.html",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "kratorai-gemini"}


# Mount static files (must be after all other routes)
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")
