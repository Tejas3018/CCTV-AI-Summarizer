from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os

from config.settings import settings
from models.database import Database
from api.routes import events, summary, query

# Setup logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting CCTV AI Summarizer API...")
    
    # Connect to database
    await Database.connect_db()
    
    logger.info("API startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")
    await Database.close_db()
    logger.info("API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="CCTV AI Summarizer API",
    description="AI-powered CCTV monitoring with event detection and natural language queries",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(summary.router, prefix="/api/summary", tags=["Summary"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])

# Serve static files (clips and thumbnails)
if os.path.exists(settings.CLIPS_STORAGE_PATH):
    app.mount("/clips", StaticFiles(directory=settings.CLIPS_STORAGE_PATH), name="clips")

if os.path.exists(settings.THUMBNAILS_PATH):
    app.mount("/thumbnails", StaticFiles(directory=settings.THUMBNAILS_PATH), name="thumbnails")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CCTV AI Summarizer API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db = Database.get_database()
        await db.command('ping')
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": str(datetime.utcnow())
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("CCTV AI Summarizer API")
    logger.info("=" * 60)
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
