"""
AI Model Main Module

This module provides the main interface for AI-powered mastery score inference.
It integrates the Deep Knowledge Tracing (DKT) model for student knowledge assessment.
"""

import logging
import json
import os
import sys
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from pathlib import Path

# Handle both relative and absolute imports
try:
    from .inference import infer_knowledge
except ImportError:
    # If running as standalone script, add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from master_score.inference import infer_knowledge

# Set up logging
logger = logging.getLogger(__name__)

# Configuration constants
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
CONFIG_FILE = ARTIFACTS_DIR / "config.json"
MODEL_FILE = ARTIFACTS_DIR / "improved_dkt_model.keras"
SKILL_DIFFICULTY_FILE = ARTIFACTS_DIR / "skill_difficulty.json"


class AIModelError(Exception):
    """Custom exception for AI model errors."""
    pass


def load_config() -> Dict[str, Any]:
    """
    Load configuration from the config file.
    
    Returns:
        Dict containing configuration parameters
        
    Raises:
        AIModelError: If config file cannot be loaded
    """
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        logger.info("Configuration loaded successfully")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {CONFIG_FILE}")
        raise AIModelError(f"Configuration file not found: {CONFIG_FILE}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise AIModelError(f"Invalid JSON in configuration file: {e}")


def validate_interaction_data(data: List[Dict[str, Any]]) -> None:
    """
    Validate the input interaction data format.
    
    Args:
        data: List of interaction dictionaries
        
    Raises:
        AIModelError: If data format is invalid
    """
    if not isinstance(data, list):
        raise AIModelError("Input data must be a list of interactions")
    
    if len(data) < 2:
        raise AIModelError("At least 2 interactions are required for inference")
    
    required_fields = ['skill', 'correct', 'startTime', 'endTime']
    
    for i, interaction in enumerate(data):
        if not isinstance(interaction, dict):
            raise AIModelError(f"Interaction {i} must be a dictionary")
        
        for field in required_fields:
            if field not in interaction:
                raise AIModelError(f"Missing required field '{field}' in interaction {i}")
        
        # Validate data types and ranges
        if not isinstance(interaction['skill'], str):
            raise AIModelError(f"Field 'skill' must be a string in interaction {i}")
        
        if not isinstance(interaction['correct'], (bool, int)):
            raise AIModelError(f"Field 'correct' must be a boolean or int in interaction {i}")
        
        if not isinstance(interaction['startTime'], (int, float)):
            raise AIModelError(f"Field 'startTime' must be a number in interaction {i}")
        
        if not isinstance(interaction['endTime'], (int, float)):
            raise AIModelError(f"Field 'endTime' must be a number in interaction {i}")
        
        if interaction['endTime'] < interaction['startTime']:
            raise AIModelError(f"endTime must be >= startTime in interaction {i}")


def preprocess_interaction_data(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert raw interaction data to pandas DataFrame for processing.
    
    Args:
        data: List of interaction dictionaries
        
    Returns:
        Preprocessed pandas DataFrame
        
    Raises:
        AIModelError: If preprocessing fails
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure correct data types
        df['correct'] = df['correct'].astype(int)
        df['startTime'] = pd.to_numeric(df['startTime'])
        df['endTime'] = pd.to_numeric(df['endTime'])
        df['skill'] = df['skill'].astype(str)
        
        # Sort by start time to ensure chronological order
        df = df.sort_values('startTime').reset_index(drop=True)
        
        logger.info(f"Preprocessed {len(df)} interactions for {df['skill'].nunique()} unique skills")
        return df
        
    except Exception as e:
        logger.error(f"Error preprocessing interaction data: {e}")
        raise AIModelError(f"Error preprocessing interaction data: {e}")


def get_mastery_scores(interaction_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate mastery scores for all skills based on student interaction history.
    
    This is the main function for getting AI-powered mastery predictions.
    Uses a Deep Knowledge Tracing (DKT) model to predict student knowledge states.
    
    Args:
        interaction_data: List of dictionaries containing interaction data.
                         Each dictionary should have:
                         - skill (str): Name of the skill/concept
                         - correct (bool/int): Whether the interaction was correct (1) or incorrect (0)
                         - startTime (int/float): Unix timestamp when interaction started
                         - endTime (int/float): Unix timestamp when interaction ended
    
    Returns:
        Dictionary mapping skill names to mastery probabilities (0.0 to 1.0)
        
    Raises:
        AIModelError: If there are issues with input data or model inference
        
    Example:
        >>> interaction_data = [
        ...     {"skill": "algebra", "correct": 1, "startTime": 1609459200, "endTime": 1609459260},
        ...     {"skill": "geometry", "correct": 0, "startTime": 1609459300, "endTime": 1609459360},
        ... ]
        >>> scores = get_mastery_scores(interaction_data)
        >>> print(scores)
        {"algebra": 0.85, "geometry": 0.42}
    """
    logger.info(f"Starting mastery score calculation for {len(interaction_data)} interactions")
    
    try:
        # Validate input data
        validate_interaction_data(interaction_data)
        
        # Preprocess data
        df = preprocess_interaction_data(interaction_data)
        
        # Perform inference using the DKT model
        predictions = infer_knowledge(df)
        
        # Ensure all predictions are valid probabilities
        validated_predictions = {}
        for skill, score in predictions.items():
            # Clip scores to valid probability range
            validated_score = max(0.0, min(1.0, float(score)))
            validated_predictions[skill] = validated_score
        
        logger.info(f"Successfully calculated mastery scores for {len(validated_predictions)} skills")
        return validated_predictions
        
    except Exception as e:
        logger.error(f"Error calculating mastery scores: {e}")
        raise AIModelError(f"Error calculating mastery scores: {e}")


def get_skill_difficulty_scores() -> Dict[str, float]:
    """
    Get pre-computed skill difficulty scores.
    
    Returns:
        Dictionary mapping skill names to difficulty scores (0.0 to 1.0)
        Higher values indicate more difficult skills.
        
    Raises:
        AIModelError: If skill difficulty file cannot be loaded
    """
    try:
        with open(SKILL_DIFFICULTY_FILE, 'r') as f:
            difficulty_scores = json.load(f)
        
        logger.info(f"Loaded difficulty scores for {len(difficulty_scores)} skills")
        return difficulty_scores
        
    except FileNotFoundError:
        logger.warning(f"Skill difficulty file not found: {SKILL_DIFFICULTY_FILE}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in skill difficulty file: {e}")
        raise AIModelError(f"Invalid JSON in skill difficulty file: {e}")


def get_model_info() -> Dict[str, Any]:
    """
    Get information about the loaded AI model.
    
    Returns:
        Dictionary containing model configuration and metadata
    """
    config = load_config()
    
    model_info = {
        "model_type": "Deep Knowledge Tracing (DKT)",
        "model_file": str(MODEL_FILE),
        "config": config,
        "description": "Transformer-based DKT model for student knowledge assessment",
        "features": [
            "Sequential interaction modeling",
            "Skill difficulty awareness",
            "Time-based features",
            "Student performance history",
            "Positional encoding"
        ]
    }
    
    return model_info


def health_check() -> Dict[str, Any]:
    """
    Perform a health check on the AI model system.
    
    Returns:
        Dictionary containing health status and system information
    """
    status = {
        "status": "healthy",
        "checks": {},
        "timestamp": pd.Timestamp.now().isoformat()
    }
    
    try:
        # Check if model file exists
        status["checks"]["model_file"] = {
            "status": "pass" if MODEL_FILE.exists() else "fail",
            "path": str(MODEL_FILE)
        }
        
        # Check if config file exists and is valid
        try:
            config = load_config()
            status["checks"]["config"] = {"status": "pass", "config_keys": list(config.keys())}
        except Exception as e:
            status["checks"]["config"] = {"status": "fail", "error": str(e)}
        
        # Check artifacts directory
        status["checks"]["artifacts_dir"] = {
            "status": "pass" if ARTIFACTS_DIR.exists() else "fail",
            "path": str(ARTIFACTS_DIR)
        }
        
        # Overall status
        failed_checks = [check for check in status["checks"].values() if check["status"] == "fail"]
        if failed_checks:
            status["status"] = "degraded"
            status["failed_checks"] = len(failed_checks)
        
    except Exception as e:
        status["status"] = "error"
        status["error"] = str(e)
        logger.error(f"Health check failed: {e}")
    
    return status

# Example usage and testing functions
def create_sample_data() -> List[Dict[str, Any]]:
    """
    Create sample interaction data for testing purposes.
    
    Returns:
        List of sample interaction dictionaries
    """
    import time
    
    current_time = int(time.time())
    
    sample_data = [
        {"skill": "addition", "correct": 1, "startTime": current_time - 1000, "endTime": current_time - 940},
        {"skill": "subtraction", "correct": 0, "startTime": current_time - 900, "endTime": current_time - 830},
        {"skill": "addition", "correct": 1, "startTime": current_time - 800, "endTime": current_time - 750},
        {"skill": "multiplication", "correct": 1, "startTime": current_time - 700, "endTime": current_time - 620},
        {"skill": "division", "correct": 0, "startTime": current_time - 600, "endTime": current_time - 540},
        {"skill": "multiplication", "correct": 1, "startTime": current_time - 500, "endTime": current_time - 430},
        {"skill": "addition", "correct": 1, "startTime": current_time - 400, "endTime": current_time - 350},
        {"skill": "subtraction", "correct": 1, "startTime": current_time - 300, "endTime": current_time - 240},
    ]
    
    return sample_data