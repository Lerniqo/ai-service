from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def health_check():
    """
    Health check endpoint for liveness and readiness probes.
    
    Returns:
        dict: Status information with service name
    """
    return {"status": "ok", "service": "ai-service"}