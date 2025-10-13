"""
Inference API endpoints for AI mastery scoring.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel, Field, validator
import logging

from app.master_score import get_mastery_scores, health_check, AIModelError

logger = logging.getLogger(__name__)

router = APIRouter()

class InteractionData(BaseModel):
    """Model for a single student interaction."""
    skill: str = Field(..., description="Name of the skill/concept")
    correct: bool = Field(..., description="Whether the interaction was correct")
    startTime: float = Field(..., description="Unix timestamp when interaction started")
    endTime: float = Field(..., description="Unix timestamp when interaction ended")
    
    @validator('endTime')
    def end_time_after_start_time(cls, v, values):
        if 'startTime' in values and v < values['startTime']:
            raise ValueError('endTime must be >= startTime')
        return v

class MasteryRequest(BaseModel):
    """Request model for mastery score calculation."""
    interactions: List[InteractionData] = Field(
        ..., 
        description="List of student interactions",
        min_items=2
    )

class MasteryResponse(BaseModel):
    """Response model for mastery scores."""
    student_id: str = Field(default="unknown", description="Student identifier")
    mastery_scores: Dict[str, float] = Field(..., description="Skill mastery probabilities")
    total_skills: int = Field(..., description="Total number of skills assessed")
    total_interactions: int = Field(..., description="Total number of interactions processed")

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Overall health status")
    checks: Dict[str, Any] = Field(..., description="Individual component checks")
    timestamp: str = Field(..., description="Timestamp of health check")

@router.post("/predict", response_model=MasteryResponse)
async def predict_mastery_scores(request: MasteryRequest) -> MasteryResponse:
    """
    Predict student mastery scores based on interaction history.
    
    This endpoint uses a Deep Knowledge Tracing (DKT) model to analyze
    student interactions and predict mastery probabilities for each skill.
    
    Args:
        request: MasteryRequest containing interaction data
        
    Returns:
        MasteryResponse with predicted mastery scores
        
    Raises:
        HTTPException: If there are issues with input data or model inference
    """
    try:
        logger.info(f"Processing mastery prediction for {len(request.interactions)} interactions")
        
        # Convert Pydantic models to dictionaries
        interaction_data = [interaction.dict() for interaction in request.interactions]
        
        # Get mastery scores
        mastery_scores = get_mastery_scores(interaction_data)
        
        response = MasteryResponse(
            mastery_scores=mastery_scores,
            total_skills=len(mastery_scores),
            total_interactions=len(request.interactions)
        )
        
        logger.info(f"Successfully predicted mastery for {response.total_skills} skills")
        return response
        
    except AIModelError as e:
        logger.error(f"AI model error: {e}")
        raise HTTPException(status_code=400, detail=f"AI model error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in mastery prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health", response_model=HealthResponse)
async def get_ai_health() -> HealthResponse:
    """
    Get health status of the AI model system.
    
    Returns:
        HealthResponse with system health information
    """
    try:
        health_data = health_check()
        return HealthResponse(**health_data)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/model/info")
async def get_model_information():
    """
    Get information about the AI model.
    
    Returns:
        Dictionary with model configuration and metadata
    """
    try:
        from app.master_score import get_model_info
        return get_model_info()
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")

# Sample data endpoint for testing
@router.get("/sample-data")
async def get_sample_data():
    """
    Get sample interaction data for testing the API.
    
    Returns:
        Sample interaction data that can be used with the predict endpoint
    """
    from app.master_score.main import create_sample_data
    
    sample_interactions = create_sample_data()
    
    return {
        "description": "Sample interaction data for testing",
        "interactions": sample_interactions,
        "usage": "POST this data to /inference/predict to test mastery prediction"
    }