"""
Health check endpoints
"""
import logging
import time
import psutil
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..models.health import (
    HealthResponse, SimpleHealthResponse, HealthStatus, ComponentHealth, 
    ComponentStatus, SystemMetrics, ModelHealth, TaskQueueHealth
)
from ..models.error import ErrorResponse
from ..core.model_manager import model_manager
from ..core.task_queue import task_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Health Check"])

# Application start time for uptime calculation
_app_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
    summary="Comprehensive health check",
    description="Get detailed health information about the OCRFlux API service"
)
async def get_health():
    """
    Get comprehensive health information about the OCRFlux API service.
    
    This endpoint provides detailed information about:
    - Overall service health status
    - Individual component health (model, task queue, etc.)
    - System resource metrics (CPU, memory, disk)
    - Model loading status and performance metrics
    - Task queue statistics and performance
    
    **Health Status Values:**
    - `healthy`: All components are functioning normally
    - `degraded`: Some components have issues but service is still functional
    - `unhealthy`: Critical components are failing, service may not function properly
    
    **HTTP Status Codes:**
    - 200: Service is healthy or degraded but functional
    - 503: Service is unhealthy and may not function properly
    """
    try:
        logger.debug("Performing comprehensive health check")
        
        # Calculate uptime
        uptime = time.time() - _app_start_time
        
        # Check individual components
        components = []
        overall_status = HealthStatus.HEALTHY
        
        # 1. Model Health Check
        model_health, model_component = await _check_model_health()
        components.append(model_component)
        
        if model_component.status == ComponentStatus.DOWN:
            overall_status = HealthStatus.UNHEALTHY
        elif model_component.status == ComponentStatus.DEGRADED:
            overall_status = HealthStatus.DEGRADED
        
        # 2. Task Queue Health Check
        task_queue_health, queue_component = await _check_task_queue_health()
        components.append(queue_component)
        
        if queue_component.status == ComponentStatus.DOWN and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        elif queue_component.status == ComponentStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # 3. System Resources Health Check
        system_metrics, system_component = await _check_system_health()
        components.append(system_component)
        
        if system_component.status == ComponentStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # Create comprehensive health response
        health_response = HealthResponse(
            status=overall_status,
            version="1.0.0",  # TODO: Get from config or package
            uptime=uptime,
            components=components,
            system=system_metrics,
            model=model_health,
            task_queue=task_queue_health,
            metadata={
                "service_name": "OCRFlux API Service",
                "environment": "development",  # TODO: Get from config
                "build_info": {
                    "version": "1.0.0",
                    "build_time": "2024-01-01T00:00:00Z"  # TODO: Get actual build info
                }
            }
        )
        
        # Return appropriate HTTP status code
        status_code = 200 if overall_status != HealthStatus.UNHEALTHY else 503
        
        logger.info(f"Health check completed: {overall_status.value}")
        return JSONResponse(
            status_code=status_code,
            content=health_response.model_dump(mode='json')
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        
        # Return unhealthy status on error
        error_response = HealthResponse(
            status=HealthStatus.UNHEALTHY,
            version="1.0.0",
            uptime=time.time() - _app_start_time,
            components=[
                ComponentHealth(
                    name="health_check",
                    status=ComponentStatus.DOWN,
                    message=f"Health check failed: {str(e)}"
                )
            ],
            system=SystemMetrics(
                memory={"error": "Unable to retrieve memory info"},
                cpu={"error": "Unable to retrieve CPU info"},
                disk={"error": "Unable to retrieve disk info"}
            ),
            model=ModelHealth(
                loaded=False,
                model_path="unknown"
            ),
            metadata={"error": "Health check system failure"}
        )
        
        return JSONResponse(
            status_code=503,
            content=error_response.model_dump(mode='json')
        )


@router.get(
    "/health/simple",
    response_model=SimpleHealthResponse,
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
    summary="Simple health check",
    description="Get basic health information for monitoring systems"
)
async def get_simple_health():
    """
    Get basic health information suitable for monitoring systems.
    
    This endpoint provides essential health information in a simplified format:
    - Overall health status
    - Model loading status
    - Active task count
    - Memory usage percentage
    
    This endpoint is optimized for frequent polling by monitoring systems
    and load balancers.
    """
    try:
        logger.debug("Performing simple health check")
        
        # Check model status
        model_loaded = model_manager.is_model_ready()
        
        # Get task queue stats
        queue_stats = task_queue.get_queue_stats()
        active_tasks = queue_stats.get("running_tasks", 0)
        
        # Get memory usage
        memory_info = psutil.virtual_memory()
        memory_usage_percent = memory_info.percent
        
        # Determine overall status
        if not model_loaded:
            status = HealthStatus.UNHEALTHY
        elif memory_usage_percent > 90:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        simple_response = SimpleHealthResponse(
            status=status,
            model_loaded=model_loaded,
            active_tasks=active_tasks,
            memory_usage_percent=memory_usage_percent
        )
        
        # Return appropriate HTTP status code
        status_code = 200 if status != HealthStatus.UNHEALTHY else 503
        
        return JSONResponse(
            status_code=status_code,
            content=simple_response.model_dump(mode='json')
        )
        
    except Exception as e:
        logger.error(f"Simple health check failed: {e}", exc_info=True)
        
        # Return unhealthy status on error
        error_response = SimpleHealthResponse(
            status=HealthStatus.UNHEALTHY,
            model_loaded=False,
            active_tasks=0,
            memory_usage_percent=0.0
        )
        
        return JSONResponse(
            status_code=503,
            content=error_response.model_dump(mode='json')
        )


@router.get(
    "/health/model",
    response_model=ModelHealth,
    summary="Model health check",
    description="Get detailed health information about the OCR model"
)
async def get_model_health():
    """
    Get detailed health information about the OCR model.
    
    Returns information about:
    - Model loading status
    - Model path and size
    - Load time and memory usage
    - Inference statistics and performance
    """
    try:
        model_health, _ = await _check_model_health()
        return model_health
        
    except Exception as e:
        logger.error(f"Model health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve model health information"
        )


@router.get(
    "/health/system",
    response_model=SystemMetrics,
    summary="System health check",
    description="Get system resource metrics"
)
async def get_system_health():
    """
    Get system resource metrics.
    
    Returns information about:
    - Memory usage (total, available, used, percentage)
    - CPU usage (percentage, core count)
    - Disk usage (total, free, used, percentage)
    - GPU usage (if available)
    """
    try:
        system_metrics, _ = await _check_system_health()
        return system_metrics
        
    except Exception as e:
        logger.error(f"System health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve system health information"
        )


async def _check_model_health() -> tuple[ModelHealth, ComponentHealth]:
    """Check model health and return both detailed and component status"""
    try:
        # Get model manager health
        model_health_status = await model_manager.health_check()
        
        # Create detailed model health
        model_health = ModelHealth(
            loaded=model_health_status.is_loaded,
            model_path=model_health_status.model_path,
            load_time=model_health_status.load_time,
            memory_usage=int(model_health_status.memory_usage_mb * 1024 * 1024) if model_health_status.memory_usage_mb else None,
            last_inference_time=model_health_status.last_check,
            inference_count=0,  # TODO: Track inference count
            average_inference_time=None  # TODO: Track average inference time
        )
        
        # Determine component status
        if model_health_status.is_loaded and not model_health_status.error_message:
            component_status = ComponentStatus.UP
            message = "Model is loaded and ready"
        elif model_health_status.is_loaded and model_health_status.error_message:
            component_status = ComponentStatus.DEGRADED
            message = f"Model loaded but has issues: {model_health_status.error_message}"
        else:
            component_status = ComponentStatus.DOWN
            message = model_health_status.error_message or "Model is not loaded"
        
        component_health = ComponentHealth(
            name="ocr_model",
            status=component_status,
            message=message,
            details={
                "model_path": model_health_status.model_path,
                "memory_usage_mb": model_health_status.memory_usage_mb,
                "gpu_memory_usage_mb": model_health_status.gpu_memory_usage_mb,
                "load_time": model_health_status.load_time
            }
        )
        
        return model_health, component_health
        
    except Exception as e:
        logger.error(f"Model health check failed: {e}")
        
        model_health = ModelHealth(
            loaded=False,
            model_path="unknown"
        )
        
        component_health = ComponentHealth(
            name="ocr_model",
            status=ComponentStatus.DOWN,
            message=f"Model health check failed: {str(e)}"
        )
        
        return model_health, component_health


async def _check_task_queue_health() -> tuple[TaskQueueHealth, ComponentHealth]:
    """Check task queue health and return both detailed and component status"""
    try:
        # Get task queue stats
        queue_stats = task_queue.get_queue_stats()
        
        # Create detailed task queue health
        task_queue_health = TaskQueueHealth(
            active_tasks=queue_stats.get("running_tasks", 0),
            pending_tasks=queue_stats.get("pending_tasks", 0),
            completed_tasks=queue_stats.get("status_counts", {}).get("completed", 0),
            failed_tasks=queue_stats.get("status_counts", {}).get("failed", 0),
            queue_size=queue_stats.get("pending_tasks", 0) + queue_stats.get("running_tasks", 0),
            max_queue_size=queue_stats.get("max_concurrent_tasks", 0) * 10,  # Estimate
            average_processing_time=None  # TODO: Track average processing time
        )
        
        # Determine component status
        active_tasks = queue_stats.get("running_tasks", 0)
        max_concurrent = queue_stats.get("max_concurrent_tasks", 1)
        
        if active_tasks < max_concurrent:
            component_status = ComponentStatus.UP
            message = f"Task queue is healthy ({active_tasks}/{max_concurrent} slots used)"
        elif active_tasks == max_concurrent:
            component_status = ComponentStatus.DEGRADED
            message = f"Task queue is at capacity ({active_tasks}/{max_concurrent} slots used)"
        else:
            component_status = ComponentStatus.DOWN
            message = f"Task queue is overloaded ({active_tasks}/{max_concurrent} slots used)"
        
        component_health = ComponentHealth(
            name="task_queue",
            status=component_status,
            message=message,
            details=queue_stats
        )
        
        return task_queue_health, component_health
        
    except Exception as e:
        logger.error(f"Task queue health check failed: {e}")
        
        task_queue_health = TaskQueueHealth(
            active_tasks=0,
            pending_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            queue_size=0,
            max_queue_size=0
        )
        
        component_health = ComponentHealth(
            name="task_queue",
            status=ComponentStatus.DOWN,
            message=f"Task queue health check failed: {str(e)}"
        )
        
        return task_queue_health, component_health


async def _check_system_health() -> tuple[SystemMetrics, ComponentHealth]:
    """Check system health and return both detailed metrics and component status"""
    try:
        # Memory information
        memory_info = psutil.virtual_memory()
        memory_data = {
            "total": memory_info.total,
            "available": memory_info.available,
            "used": memory_info.used,
            "percentage": memory_info.percent,
            "free": memory_info.free
        }
        
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_data = {
            "percentage": cpu_percent,
            "count": psutil.cpu_count(),
            "count_logical": psutil.cpu_count(logical=True)
        }
        
        # Disk information
        disk_info = psutil.disk_usage('/')
        disk_data = {
            "total": disk_info.total,
            "used": disk_info.used,
            "free": disk_info.free,
            "percentage": (disk_info.used / disk_info.total) * 100
        }
        
        # GPU information (if available)
        gpu_data = None
        try:
            import torch
            if torch.cuda.is_available():
                gpu_data = {
                    "available": True,
                    "device_count": torch.cuda.device_count(),
                    "current_device": torch.cuda.current_device(),
                    "memory_allocated": torch.cuda.memory_allocated(),
                    "memory_reserved": torch.cuda.memory_reserved()
                }
        except ImportError:
            gpu_data = {"available": False, "reason": "PyTorch not available"}
        except Exception as e:
            gpu_data = {"available": False, "reason": str(e)}
        
        system_metrics = SystemMetrics(
            memory=memory_data,
            cpu=cpu_data,
            disk=disk_data,
            gpu=gpu_data
        )
        
        # Determine component status based on resource usage
        if memory_info.percent > 95 or cpu_percent > 95 or disk_data["percentage"] > 95:
            component_status = ComponentStatus.DOWN
            message = "System resources critically low"
        elif memory_info.percent > 80 or cpu_percent > 80 or disk_data["percentage"] > 80:
            component_status = ComponentStatus.DEGRADED
            message = "System resources running high"
        else:
            component_status = ComponentStatus.UP
            message = "System resources are healthy"
        
        component_health = ComponentHealth(
            name="system_resources",
            status=component_status,
            message=message,
            details={
                "memory_percent": memory_info.percent,
                "cpu_percent": cpu_percent,
                "disk_percent": disk_data["percentage"]
            }
        )
        
        return system_metrics, component_health
        
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        
        system_metrics = SystemMetrics(
            memory={"error": str(e)},
            cpu={"error": str(e)},
            disk={"error": str(e)}
        )
        
        component_health = ComponentHealth(
            name="system_resources",
            status=ComponentStatus.DOWN,
            message=f"System health check failed: {str(e)}"
        )
        
        return system_metrics, component_health