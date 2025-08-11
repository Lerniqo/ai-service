from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.health import router as health_router
from app.logging_config import configure_logging
from app.exception_handlers import http_exception_handler, general_exception_handler

settings = get_settings()

# Configure structured JSON logging
logger = configure_logging(
    service_name="ai-service",
    log_level="INFO" if settings.is_production else "DEBUG"
)

app = FastAPI(
    title=settings.APP_NAME, 
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION
)

# Store logger in app state for access in exception handlers
app.state.logger = logger

# Add exception handlers for structured logging
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include health router with correct prefix for /health endpoint
app.include_router(health_router, prefix="/health", tags=["health"])

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in {settings.ENV} environment"
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info(f"Shutting down {settings.APP_NAME}")

@app.get("/")
def read_root():
    """Root endpoint with welcome message."""
    logger.info("Root endpoint accessed")
    return {"message": f"Welcome to {settings.APP_NAME}!", "version": settings.APP_VERSION}