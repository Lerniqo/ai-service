import uvicorn
from app.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    # Run the FastAPI application with environment-specific settings
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD if settings.is_development else False,
    )
