"""
Task management endpoints
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse

from ..models.process import TaskStatusResponse, ProcessResult
from ..models.error import ErrorResponse
from ..core.task_queue import task_queue, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Task Management"])


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get task status",
    description="Retrieve the current status and progress of an asynchronous task"
)
async def get_task_status(
    task_id: str = Path(..., description="Unique task identifier")
):
    """
    Get the current status of an asynchronous task.
    
    **Task Status Values:**
    - `pending`: Task is queued and waiting to be processed
    - `processing`: Task is currently being processed
    - `completed`: Task has completed successfully
    - `failed`: Task failed due to an error
    - `timeout`: Task was cancelled due to timeout
    - `cancelled`: Task was manually cancelled
    
    **Progress Values:**
    - 0.0: Task not started
    - 0.0-1.0: Task in progress
    - 1.0: Task completed
    
    Returns detailed information about task timing, progress, and any error messages.
    """
    try:
        logger.debug(f"Getting status for task: {task_id}")
        
        # Get task status from queue
        task_result = await task_queue.get_task_status(task_id)
        
        if task_result is None:
            logger.warning(f"Task not found: {task_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID '{task_id}' not found"
            )
        
        # Check if results are available
        result_available = (
            task_result.status == TaskStatus.COMPLETED and 
            task_result.result is not None
        )
        
        # Create response
        response = TaskStatusResponse(
            task_id=task_id,
            status=task_result.status.value,
            progress=task_result.progress,
            created_at=task_result.created_at,
            started_at=task_result.started_at,
            completed_at=task_result.completed_at,
            estimated_completion=task_result.estimated_completion,
            processing_time=task_result.processing_time,
            error_message=task_result.error_message,
            result_available=result_available
        )
        
        logger.debug(f"Task status retrieved: {task_id} -> {task_result.status.value}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while retrieving task status"
        )


@router.get(
    "/tasks/{task_id}/result",
    response_model=ProcessResult,
    responses={
        404: {"model": ErrorResponse, "description": "Task not found or result not available"},
        409: {"model": ErrorResponse, "description": "Task not completed yet"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get task result",
    description="Retrieve the result of a completed asynchronous task"
)
async def get_task_result(
    task_id: str = Path(..., description="Unique task identifier")
):
    """
    Get the result of a completed asynchronous task.
    
    This endpoint returns the processing result for tasks that have completed successfully.
    
    **Prerequisites:**
    - Task must exist
    - Task status must be 'completed'
    - Task must have completed successfully (success=true in result)
    
    **Returns:**
    The same ProcessResult format as the synchronous `/parse` endpoint, containing:
    - Extracted document text in Markdown format
    - Individual page texts
    - Processing statistics and metadata
    - Any error information
    """
    try:
        logger.debug(f"Getting result for task: {task_id}")
        
        # Get task status first
        task_result = await task_queue.get_task_status(task_id)
        
        if task_result is None:
            logger.warning(f"Task not found: {task_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID '{task_id}' not found"
            )
        
        # Check if task is completed
        if task_result.status != TaskStatus.COMPLETED:
            logger.info(f"Task not completed yet: {task_id} (status: {task_result.status.value})")
            raise HTTPException(
                status_code=409,
                detail=f"Task is not completed yet. Current status: {task_result.status.value}"
            )
        
        # Get the actual result
        result_data = await task_queue.get_task_result(task_id)
        
        if result_data is None:
            logger.warning(f"Task result not available: {task_id}")
            raise HTTPException(
                status_code=404,
                detail="Task result is not available"
            )
        
        # Convert result data to ProcessResult model
        try:
            process_result = ProcessResult(
                success=result_data["success"],
                file_name=result_data["file_name"],
                file_size=result_data.get("file_size"),
                num_pages=result_data["num_pages"],
                document_text=result_data["document_text"],
                page_texts=result_data["page_texts"],
                fallback_pages=result_data["fallback_pages"],
                processing_time=result_data["processing_time"],
                created_at=task_result.completed_at or task_result.created_at,
                error_message=result_data.get("error_message")
            )
            
            logger.info(f"Task result retrieved: {task_id}")
            return process_result
            
        except KeyError as e:
            logger.error(f"Invalid result data format for task {task_id}: missing {e}")
            raise HTTPException(
                status_code=500,
                detail="Task result data is in an invalid format"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error getting task result for {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while retrieving task result"
        )


@router.delete(
    "/tasks/{task_id}",
    responses={
        200: {"description": "Task cancelled successfully"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Task cannot be cancelled"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Cancel task",
    description="Cancel a pending or running asynchronous task"
)
async def cancel_task(
    task_id: str = Path(..., description="Unique task identifier")
):
    """
    Cancel an asynchronous task.
    
    This endpoint allows you to cancel tasks that are pending or currently running.
    Completed, failed, or already cancelled tasks cannot be cancelled.
    
    **Cancellable Task States:**
    - `pending`: Task is in queue but not started
    - `processing`: Task is currently running (will be interrupted)
    
    **Non-cancellable Task States:**
    - `completed`: Task already finished
    - `failed`: Task already failed
    - `timeout`: Task already timed out
    - `cancelled`: Task already cancelled
    
    Returns success message if cancellation was successful.
    """
    try:
        logger.info(f"Attempting to cancel task: {task_id}")
        
        # Check if task exists first
        task_result = await task_queue.get_task_status(task_id)
        
        if task_result is None:
            logger.warning(f"Task not found for cancellation: {task_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID '{task_id}' not found"
            )
        
        # Check if task can be cancelled
        if task_result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, 
                                  TaskStatus.TIMEOUT, TaskStatus.CANCELLED]:
            logger.info(f"Task cannot be cancelled (status: {task_result.status.value}): {task_id}")
            raise HTTPException(
                status_code=409,
                detail=f"Task cannot be cancelled. Current status: {task_result.status.value}"
            )
        
        # Attempt to cancel the task
        cancelled = await task_queue.cancel_task(task_id)
        
        if cancelled:
            logger.info(f"Task cancelled successfully: {task_id}")
            return {
                "success": True,
                "message": f"Task '{task_id}' has been cancelled",
                "task_id": task_id,
                "previous_status": task_result.status.value
            }
        else:
            logger.warning(f"Failed to cancel task: {task_id}")
            raise HTTPException(
                status_code=500,
                detail="Failed to cancel task"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while cancelling task"
        )


@router.get(
    "/tasks",
    responses={
        200: {"description": "Task queue statistics"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get task queue statistics",
    description="Retrieve statistics about the task queue and processing status"
)
async def get_task_queue_stats():
    """
    Get statistics about the task queue.
    
    Returns information about:
    - Total number of tasks
    - Tasks by status (pending, processing, completed, etc.)
    - Queue capacity and current load
    - Registered task handlers
    
    Useful for monitoring and debugging the task processing system.
    """
    try:
        logger.debug("Getting task queue statistics")
        
        stats = task_queue.get_queue_stats()
        
        # Add some additional computed statistics
        total_tasks = stats["total_tasks"]
        completed_tasks = stats["status_counts"].get("completed", 0)
        failed_tasks = stats["status_counts"].get("failed", 0)
        
        success_rate = 0.0
        if total_tasks > 0:
            success_rate = completed_tasks / total_tasks
        
        enhanced_stats = {
            **stats,
            "success_rate": success_rate,
            "failure_rate": (failed_tasks / total_tasks) if total_tasks > 0 else 0.0,
            "queue_utilization": len(stats.get("running_tasks", [])) / stats["max_concurrent_tasks"]
        }
        
        logger.debug("Task queue statistics retrieved")
        return {
            "success": True,
            "statistics": enhanced_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting task queue statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while retrieving statistics"
        )