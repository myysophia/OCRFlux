"""
FastAPI exception handlers for standardized error responses
"""
import logging
import uuid
from typing import Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..models.error import (
    ErrorResponse, ErrorDetail, ErrorType, ValidationErrorResponse
)

logger = logging.getLogger(__name__)


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    logger.warning(
        f"Validation error in {request.method} {request.url.path}: {exc}",
        extra={"request_id": request_id}
    )
    
    details = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        details.append(ErrorDetail(
            field=field_path,
            message=error["msg"],
            code=error["type"],
            context={"input": error.get("input")}
        ))
    
    error_response = ValidationErrorResponse(
        message="Request validation failed",
        details=details,
        request_id=request_id,
        path=str(request.url.path),
        method=request.method
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode='json')
    )


async def http_exception_handler(
    request: Request, 
    exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """Handle HTTP exceptions"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    logger.warning(
        f"HTTP exception in {request.method} {request.url.path}: {exc.detail}",
        extra={"request_id": request_id, "status_code": exc.status_code}
    )
    
    error_type = _get_error_type_from_status_code(exc.status_code)
    
    error_response = ErrorResponse(
        error_type=error_type,
        message=str(exc.detail),
        request_id=request_id,
        path=str(request.url.path),
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


async def general_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    """Handle general exceptions"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    logger.exception(
        f"Unhandled exception in {request.method} {request.url.path}: {str(exc)}",
        extra={"request_id": request_id}
    )
    
    error_response = ErrorResponse(
        error_type=ErrorType.SYSTEM_ERROR,
        message="An unexpected error occurred",
        details=[ErrorDetail(
            message="Internal server error",
            context={"error_type": type(exc).__name__}
        )],
        request_id=request_id,
        path=str(request.url.path),
        method=request.method
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode='json')
    )


def _get_error_type_from_status_code(status_code: int) -> ErrorType:
    """Map HTTP status codes to error types"""
    if status_code == 400:
        return ErrorType.VALIDATION_ERROR
    elif status_code == 401:
        return ErrorType.AUTHENTICATION_ERROR
    elif status_code == 403:
        return ErrorType.AUTHORIZATION_ERROR
    elif status_code == 404:
        return ErrorType.NOT_FOUND_ERROR
    elif status_code == 408:
        return ErrorType.TIMEOUT_ERROR
    elif status_code == 422:
        return ErrorType.VALIDATION_ERROR
    elif status_code == 429:
        return ErrorType.RATE_LIMIT_ERROR
    elif status_code >= 500:
        return ErrorType.SYSTEM_ERROR
    else:
        return ErrorType.SYSTEM_ERROR


def setup_exception_handlers(app):
    """Setup exception handlers for the FastAPI app"""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)