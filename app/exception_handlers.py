"""
Custom exception handlers for structured logging and error handling.
"""

import traceback
from typing import Any, Dict

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.logging_config import log_with_extra


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException with structured logging.
    
    Args:
        request: The FastAPI request object
        exc: The HTTPException that was raised
        
    Returns:
        JSONResponse with error details
    """
    logger = request.app.state.logger
    
    log_with_extra(
        logger,
        "warning",
        f"HTTP Exception: {exc.detail}",
        status_code=exc.status_code,
        detail=exc.detail,
        path=str(request.url.path),
        method=request.method,
        client_ip=request.client.host if request.client else None
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all other unhandled exceptions with structured logging.
    
    Args:
        request: The FastAPI request object
        exc: The exception that was raised
        
    Returns:
        JSONResponse with generic error message
    """
    logger = request.app.state.logger
    
    # Get traceback information
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    
    log_with_extra(
        logger,
        "error",
        f"Unhandled exception: {str(exc)}",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        traceback=tb_str,
        path=str(request.url.path),
        method=request.method,
        client_ip=request.client.host if request.client else None
    )
    
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )
