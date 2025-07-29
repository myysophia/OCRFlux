"""
Global error handling middleware
"""
import logging
import traceback
import uuid
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from ..models.error import (
    ErrorResponse, ErrorDetail, ErrorType,
    ValidationErrorResponse, FileErrorResponse, ProcessingErrorResponse,
    ModelErrorResponse, SystemErrorResponse
)

logger = logging.getLogger(__name__)


class CustomException(Exception):
    """Base class for custom application exceptions"""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.SYSTEM_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class FileProcessingError(CustomException):
    """Exception for file processing errors"""
    
    def __init__(self, message: str, filename: Optional[str] = None, file_size: Optional[int] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.FILE_ERROR,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        self.filename = filename
        self.file_size = file_size


class ModelError(CustomException):
    """Exception for model-related errors"""
    
    def __init__(self, message: str, model_status: Optional[str] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.MODEL_ERROR,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
        self.model_status = model_status


class ProcessingError(CustomException):
    """Exception for processing errors"""
    
    def __init__(self, message: str, stage: Optional[str] = None, partial_result: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.PROCESSING_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        self.stage = stage
        self.partial_result = partial_result


class TimeoutError(CustomException):
    """Exception for timeout errors"""
    
    def __init__(self, message: str, timeout_duration: Optional[float] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.TIMEOUT_ERROR,
            status_code=status.HTTP_408_REQUEST_TIMEOUT
        )
        self.timeout_duration = timeout_duration


class RateLimitError(CustomException):
    """Exception for rate limit errors"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.RATE_LIMIT_ERROR,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )
        self.retry_after = retry_after


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle uncaught exceptions and provide standardized error responses"""
    
    def __init__(self, app, include_debug_info: bool = False):
        super().__init__(app)
        self.include_debug_info = include_debug_info
    
    async def dispatch(self, request: Request, call_next):
        # Get request ID from request state (set by RequestIDMiddleware)
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        try:
            response = await call_next(request)
            return response
            
        except RequestValidationError as exc:
            return await self._handle_validation_error(request, exc, request_id)
            
        except HTTPException as exc:
            return await self._handle_http_exception(request, exc, request_id)
            
        except StarletteHTTPException as exc:
            return await self._handle_starlette_http_exception(request, exc, request_id)
            
        except FileProcessingError as exc:
            return await self._handle_file_processing_error(request, exc, request_id)
            
        except ModelError as exc:
            return await self._handle_model_error(request, exc, request_id)
            
        except ProcessingError as exc:
            return await self._handle_processing_error(request, exc, request_id)
            
        except TimeoutError as exc:
            return await self._handle_timeout_error(request, exc, request_id)
            
        except RateLimitError as exc:
            return await self._handle_rate_limit_error(request, exc, request_id)
            
        except CustomException as exc:
            return await self._handle_custom_exception(request, exc, request_id)
            
        except Exception as exc:
            return await self._handle_unexpected_error(request, exc, request_id)
    
    async def _handle_validation_error(
        self, 
        request: Request, 
        exc: RequestValidationError, 
        request_id: str
    ) -> JSONResponse:
        """Handle Pydantic validation errors"""
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
            message="Validation failed",
            details=details,
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.model_dump(mode='json')
        )
    
    async def _handle_http_exception(
        self, 
        request: Request, 
        exc: HTTPException, 
        request_id: str
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        logger.warning(
            f"HTTP exception in {request.method} {request.url.path}: {exc.detail}",
            extra={"request_id": request_id, "status_code": exc.status_code}
        )
        
        error_type = self._get_error_type_from_status_code(exc.status_code)
        
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
    
    async def _handle_starlette_http_exception(
        self, 
        request: Request, 
        exc: StarletteHTTPException, 
        request_id: str
    ) -> JSONResponse:
        """Handle Starlette HTTP exceptions"""
        logger.warning(
            f"Starlette HTTP exception in {request.method} {request.url.path}: {exc.detail}",
            extra={"request_id": request_id, "status_code": exc.status_code}
        )
        
        error_type = self._get_error_type_from_status_code(exc.status_code)
        
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
    
    async def _handle_file_processing_error(
        self, 
        request: Request, 
        exc: FileProcessingError, 
        request_id: str
    ) -> JSONResponse:
        """Handle file processing errors"""
        logger.error(
            f"File processing error in {request.method} {request.url.path}: {exc.message}",
            extra={
                "request_id": request_id,
                "error_filename": exc.filename,
                "error_file_size": exc.file_size
            }
        )
        
        error_response = FileErrorResponse(
            message=exc.message,
            filename=exc.filename,
            file_size=exc.file_size,
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(mode='json')
        )
    
    async def _handle_model_error(
        self, 
        request: Request, 
        exc: ModelError, 
        request_id: str
    ) -> JSONResponse:
        """Handle model-related errors"""
        logger.error(
            f"Model error in {request.method} {request.url.path}: {exc.message}",
            extra={
                "request_id": request_id,
                "model_status": exc.model_status
            }
        )
        
        error_response = ModelErrorResponse(
            message=exc.message,
            model_status=exc.model_status,
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(mode='json')
        )
    
    async def _handle_processing_error(
        self, 
        request: Request, 
        exc: ProcessingError, 
        request_id: str
    ) -> JSONResponse:
        """Handle processing errors"""
        logger.error(
            f"Processing error in {request.method} {request.url.path}: {exc.message}",
            extra={
                "request_id": request_id,
                "stage": exc.stage,
                "partial_result": exc.partial_result
            }
        )
        
        error_response = ProcessingErrorResponse(
            message=exc.message,
            stage=exc.stage,
            partial_result=exc.partial_result,
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(mode='json')
        )
    
    async def _handle_timeout_error(
        self, 
        request: Request, 
        exc: TimeoutError, 
        request_id: str
    ) -> JSONResponse:
        """Handle timeout errors"""
        logger.error(
            f"Timeout error in {request.method} {request.url.path}: {exc.message}",
            extra={
                "request_id": request_id,
                "timeout_duration": exc.timeout_duration
            }
        )
        
        error_response = ErrorResponse(
            error_type=ErrorType.TIMEOUT_ERROR,
            message=exc.message,
            details=[ErrorDetail(
                message=f"Request timed out after {exc.timeout_duration} seconds" if exc.timeout_duration else "Request timed out",
                context={"timeout_duration": exc.timeout_duration}
            )],
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(mode='json')
        )
    
    async def _handle_rate_limit_error(
        self, 
        request: Request, 
        exc: RateLimitError, 
        request_id: str
    ) -> JSONResponse:
        """Handle rate limit errors"""
        logger.warning(
            f"Rate limit error in {request.method} {request.url.path}: {exc.message}",
            extra={
                "request_id": request_id,
                "retry_after": exc.retry_after
            }
        )
        
        error_response = ErrorResponse(
            error_type=ErrorType.RATE_LIMIT_ERROR,
            message=exc.message,
            details=[ErrorDetail(
                message=f"Rate limit exceeded. Retry after {exc.retry_after} seconds" if exc.retry_after else "Rate limit exceeded",
                context={"retry_after": exc.retry_after}
            )],
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        headers = {}
        if exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(mode='json'),
            headers=headers
        )
    
    async def _handle_custom_exception(
        self, 
        request: Request, 
        exc: CustomException, 
        request_id: str
    ) -> JSONResponse:
        """Handle custom application exceptions"""
        logger.error(
            f"Custom exception in {request.method} {request.url.path}: {exc.message}",
            extra={
                "request_id": request_id,
                "error_type": exc.error_type,
                "details": exc.details
            }
        )
        
        error_response = ErrorResponse(
            error_type=exc.error_type,
            message=exc.message,
            details=[ErrorDetail(
                message=exc.message,
                context=exc.details
            )],
            request_id=request_id,
            path=str(request.url.path),
            method=request.method
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(mode='json')
        )
    
    async def _handle_unexpected_error(
        self, 
        request: Request, 
        exc: Exception, 
        request_id: str
    ) -> JSONResponse:
        """Handle unexpected errors"""
        logger.exception(
            f"Unexpected error in {request.method} {request.url.path}: {str(exc)}",
            extra={"request_id": request_id}
        )
        
        details = []
        if self.include_debug_info:
            details.append(ErrorDetail(
                message="Debug information",
                context={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "traceback": traceback.format_exc()
                }
            ))
        
        error_response = SystemErrorResponse(
            message="An unexpected error occurred",
            details=details,
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            system_info={
                "error_type": type(exc).__name__
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(mode='json')
        )
    
    def _get_error_type_from_status_code(self, status_code: int) -> ErrorType:
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