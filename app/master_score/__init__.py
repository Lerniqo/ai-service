"""
AI Master Score Module

This module provides AI-powered student mastery assessment using Deep Knowledge Tracing.
"""

from .main import (
    get_mastery_scores,
    get_skill_difficulty_scores,
    get_model_info,
    health_check,
    AIModelError
)

__all__ = [
    'get_mastery_scores',
    'get_skill_difficulty_scores', 
    'get_model_info',
    'health_check',
    'AIModelError'
]