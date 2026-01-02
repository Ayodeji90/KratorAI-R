"""FastAPI application for KratorAI Gemini Integration."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from src.config import get_settings
from src.api.routes import breed, refine, edit, agent, describe, template
from src.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

# Static files directory
STATIC_DIR = Path(__file__).parent.parent / "static"

# Generated images directory
GENERATED_DIR = Path("/tmp/kratorai_generated")
GENERATED_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    setup_logging(level="DEBUG" if settings.debug else "INFO", json_format=not settings.debug)
    
    logger.info(f"KratorAI Gemini API starting (debug={settings.debug})")
    yield
    # Shutdown
    logger.info("KratorAI Gemini API shutting down")


app = FastAPI(
    title="KratorAI Gemini Integration",
    description="AI-powered design breeding, refining, and editing for African graphic designers",
    version="0.1.0",
    lifespan=lifespan,
)

from src.utils.rate_limit import RateLimitMiddleware

# Unified process endpoint
@app.post("/process")
async def process_request(
    request: Request,
    action: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    image_urls: Optional[List[str]] = Form(None),
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
):
    """
    Unified endpoint to route requests based on action.
    Supports both JSON and Multipart/Form-data.
    """
    try:
        # 1. Determine action and parameters
        if request.headers.get("content-type", "").startswith("application/json"):
            body = await request.json()
            action = body.get("action")
            # For JSON, we just redirect and let the specific route handle it
            if not action:
                return JSONResponse(status_code=400, content={"detail": "Missing action in JSON body"})
        else:
            # Multipart/Form-data (already parsed by FastAPI params)
            if not action:
                return JSONResponse(status_code=400, content={"detail": "Missing action parameter"})

        valid_actions = ["breed", "refine", "edit", "template", "agent", "describe"]
        if action not in valid_actions:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Invalid action: {action}. Valid actions are: {', '.join(valid_actions)}"}
            )

        # 2. Handle routing/dispatching
        # If it's a file upload, we redirect to the /upload version of the route if it exists
        if file or files:
            if action == "refine":
                return RedirectResponse(url="/refine/upload", status_code=307)
            elif action == "agent":
                return RedirectResponse(url="/agent/chat/upload", status_code=307)
            elif action == "describe":
                return RedirectResponse(url="/describe", status_code=307)
            elif action == "breed":
                return RedirectResponse(url="/breed/upload", status_code=307)
            # Add others as needed
        
        # If multiple URLs are provided for breeding
        if action == "breed" and (image_urls or (image_url and image_urls)):
             return RedirectResponse(url="/breed/upload", status_code=307)

        # Default redirection (works for JSON or Form without files)
        target_path = f"/{action}"
        if action == "agent":
            target_path = "/agent/chat"
        elif action == "describe":
            target_path = "/describe"
            
        return RedirectResponse(url=target_path, status_code=307)
        
    except Exception as e:
        logger.error(f"Error in /process: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)}
        )

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
app.include_router(template.router, prefix="/template", tags=["Template Editing"])


@app.get("/")
async def root():
    """Redirect to the test UI."""
    return RedirectResponse(url="/static/index.html")


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "KratorAI Gemini Integration",
        "version": "0.3.0",
        "description": "AI-powered design breeding, refining, and editing for African graphic designers",
        "endpoints": {
            "/process": "POST - Unified entry point (Multipart/Form or JSON). Takes action, prompt, image_url, and file.",
            "/breed": "POST - Combine multiple designs into hybrid",
            "/refine/upload": "POST - Upload image or provide URL to refine",
            "/edit": "POST - Targeted inpainting/style transfer",
            "/agent/chat/upload": "POST - Upload image or provide URL to chat",
            "/describe": "POST - Generate description from image or URL",
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
app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")
