from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as api_router

# Initialize the FastAPI application
app = FastAPI(
    title="CSIHACK05 Backend",
    description="Backend API for CSIHACK05 Government Schemes Discovery Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for the Next.js frontend
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/health")
async def health_check():
    """
    Basic health check endpoint to verify the server is running.
    Useful for container deployment or simple ping.
    """
    return {"status": "ok", "app": "CSIHACK05 Backend"}

# Include all API routes defined in app/api/routes.py
app.include_router(api_router, prefix="/api/v1")
