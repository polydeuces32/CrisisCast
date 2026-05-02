"""
CrisisCast - Main FastAPI Application
API-first SaaS platform for trend forecasting and volatility insights
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
import asyncio
import logging

from app.core.config import settings
from app.core.database import init_db
from app.core.auth import require_api_key
from app.api.routes import forecasts, volatility, alerts, markets, admin
from app.services.data_ingestion import DataIngestionService
from app.services.ml_service import MLService
from app.services.alert_service import AlertService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("Starting CrisisCast API...")
    await init_db()
    
    # Initialize services
    app.state.data_ingestion = DataIngestionService()
    app.state.ml_service = MLService()
    app.state.alert_service = AlertService()
    
    # Start background tasks
    asyncio.create_task(app.state.data_ingestion.start_continuous_ingestion())
    asyncio.create_task(app.state.ml_service.start_model_updates())
    asyncio.create_task(app.state.alert_service.start_alert_monitoring())
    
    logger.info("CrisisCast API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CrisisCast API...")
    await app.state.data_ingestion.stop_continuous_ingestion()
    await app.state.ml_service.stop_model_updates()
    await app.state.alert_service.stop_alert_monitoring()
    logger.info("CrisisCast API shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="CrisisCast API",
    description="API-first SaaS platform delivering 6-month trend forecasts and real-time volatility insights across niche markets",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes — all protected by API key
_auth = [Depends(require_api_key)]
app.include_router(forecasts.router, prefix="/api/v1/forecasts", tags=["forecasts"], dependencies=_auth)
app.include_router(volatility.router, prefix="/api/v1/volatility", tags=["volatility"], dependencies=_auth)
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"], dependencies=_auth)
app.include_router(markets.router, prefix="/api/v1/markets", tags=["markets"], dependencies=_auth)
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"], dependencies=_auth)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "CrisisCast API",
        "version": "1.0.0",
        "description": "API-first SaaS platform for trend forecasting and volatility insights",
        "endpoints": {
            "forecasts": "/api/v1/forecasts",
            "volatility": "/api/v1/volatility", 
            "alerts": "/api/v1/alerts",
            "markets": "/api/v1/markets",
            "admin": "/api/v1/admin",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "data_ingestion": "running",
            "ml_service": "running", 
            "alert_service": "running"
        }
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
