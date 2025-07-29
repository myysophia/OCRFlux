"""
Task Queue System for OCRFlux API Service

This module provides an async task queue system for handling long-running
OCR processing tasks with status tracking and result caching.
"""
import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
import json

try:
    from api.core.config import settings
except ImportError:
    # Fallback settings for testing
    class MockSettings:
        max_concurrent_tasks = 4
        task_timeout = 300  # 5 minutes
        result_cache_ttl = 3600  # 1 hour
    settings = MockSettings()


logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task definition"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0  # Higher number = higher priority


@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0
    estimated_completion: Optional[datetime] = None
    processing_time: Optional[float] = None


class TaskQueue:
    """
    Async task queue system for managing long-running OCR processing tasks.
    
    Features:
    - Task submission and status tracking
    - Result caching with TTL
    - Task timeout and cleanup
    - Concurrent task execution with limits
    - Progress tracking and completion estimation
    """
    
    def __init__(self, max_concurrent_tasks: int = None):
        """
        Initialize TaskQueue.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
        """
        self.max_concurrent_tasks = max_concurrent_tasks or settings.max_concurrent_tasks
        self.task_timeout = settings.task_timeout
        self.result_cache_ttl = settings.result_cache_ttl
        
        # Task storage
        self._tasks: Dict[str, Task] = {}
        self._task_results: Dict[str, TaskResult] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        # Queue management
        self._pending_queue: List[str] = []  # Task IDs in priority order
        self._semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._queue_processor_task: Optional[asyncio.Task] = None
        
        # Task handlers
        self._task_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {}
        
        logger.info(f"TaskQueue initialized with max_concurrent_tasks={self.max_concurrent_tasks}")
    
    async def start(self):
        """Start the task queue background processes"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        if self._queue_processor_task is None:
            self._queue_processor_task = asyncio.create_task(self._process_queue_loop())
        
        logger.info("TaskQueue background processes started")
    
    async def stop(self):
        """Stop the task queue and cleanup resources"""
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all running tasks
        for task_id, task in self._running_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                # Update task result to cancelled
                if task_id in self._task_results:
                    self._task_results[task_id].status = TaskStatus.CANCELLED
                    self._task_results[task_id].completed_at = datetime.utcnow()
        
        logger.info("TaskQueue stopped")
    
    def register_task_handler(
        self, 
        task_type: str, 
        handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ):
        """
        Register a task handler for a specific task type.
        
        Args:
            task_type: Type of task to handle
            handler: Async function that processes the task payload and returns result
        """
        self._task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    async def submit_task(
        self, 
        task_type: str, 
        payload: Dict[str, Any], 
        priority: int = 0
    ) -> str:
        """
        Submit a new task to the queue.
        
        Args:
            task_type: Type of task
            payload: Task payload data
            priority: Task priority (higher = more priority)
            
        Returns:
            str: Task ID
            
        Raises:
            ValueError: If task type is not registered
        """
        if task_type not in self._task_handlers:
            raise ValueError(f"No handler registered for task type: {task_type}")
        
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority
        )
        
        # Create initial task result
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING
        )
        
        # Store task and result
        self._tasks[task_id] = task
        self._task_results[task_id] = task_result
        
        # Add to pending queue (maintain priority order)
        self._add_to_pending_queue(task_id)
        
        logger.info(f"Task submitted: {task_id} (type: {task_type}, priority: {priority})")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """
        Get task status and result.
        
        Args:
            task_id: Task ID
            
        Returns:
            TaskResult or None if task not found
        """
        return self._task_results.get(task_id)
    
    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task result data.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task result data or None if not available
        """
        task_result = self._task_results.get(task_id)
        if task_result and task_result.status == TaskStatus.COMPLETED:
            return task_result.result
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if task was cancelled, False if not found or already completed
        """
        # Remove from pending queue
        if task_id in self._pending_queue:
            self._pending_queue.remove(task_id)
            if task_id in self._task_results:
                self._task_results[task_id].status = TaskStatus.CANCELLED
                self._task_results[task_id].completed_at = datetime.utcnow()
            logger.info(f"Cancelled pending task: {task_id}")
            return True
        
        # Cancel running task
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            if task_id in self._task_results:
                self._task_results[task_id].status = TaskStatus.CANCELLED
                self._task_results[task_id].completed_at = datetime.utcnow()
            logger.info(f"Cancelled running task: {task_id}")
            return True
        
        return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dict with queue statistics
        """
        status_counts = {}
        for result in self._task_results.values():
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_tasks": len(self._task_results),
            "pending_tasks": len(self._pending_queue),
            "running_tasks": len(self._running_tasks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "status_counts": status_counts,
            "registered_handlers": list(self._task_handlers.keys())
        }
    
    def _add_to_pending_queue(self, task_id: str):
        """Add task to pending queue maintaining priority order"""
        task = self._tasks[task_id]
        
        # Insert in priority order (higher priority first)
        inserted = False
        for i, existing_task_id in enumerate(self._pending_queue):
            existing_task = self._tasks[existing_task_id]
            if task.priority > existing_task.priority:
                self._pending_queue.insert(i, task_id)
                inserted = True
                break
        
        if not inserted:
            self._pending_queue.append(task_id)
    
    async def _process_queue_loop(self):
        """Background loop to process pending tasks"""
        while True:
            try:
                if self._pending_queue and len(self._running_tasks) < self.max_concurrent_tasks:
                    task_id = self._pending_queue.pop(0)
                    await self._start_task(task_id)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Wait before retrying
    
    async def _start_task(self, task_id: str):
        """Start processing a task"""
        if task_id not in self._tasks:
            return
        
        task = self._tasks[task_id]
        task_result = self._task_results[task_id]
        
        # Update status to processing
        task_result.status = TaskStatus.PROCESSING
        task_result.started_at = datetime.utcnow()
        
        # Estimate completion time (rough estimate)
        estimated_duration = 60  # Default 1 minute
        task_result.estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_duration)
        
        # Create and start the task
        async_task = asyncio.create_task(self._execute_task(task_id))
        self._running_tasks[task_id] = async_task
        
        logger.info(f"Started processing task: {task_id}")
    
    async def _execute_task(self, task_id: str):
        """Execute a task with timeout and error handling"""
        task = self._tasks[task_id]
        task_result = self._task_results[task_id]
        
        try:
            async with self._semaphore:
                # Get task handler
                handler = self._task_handlers[task.task_type]
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    handler(task.payload),
                    timeout=self.task_timeout
                )
                
                # Task completed successfully
                task_result.status = TaskStatus.COMPLETED
                task_result.result = result
                task_result.completed_at = datetime.utcnow()
                task_result.progress = 1.0
                
                if task_result.started_at:
                    task_result.processing_time = (
                        task_result.completed_at - task_result.started_at
                    ).total_seconds()
                
                logger.info(f"Task completed successfully: {task_id}")
        
        except asyncio.TimeoutError:
            task_result.status = TaskStatus.TIMEOUT
            task_result.error_message = f"Task timed out after {self.task_timeout} seconds"
            task_result.completed_at = datetime.utcnow()
            logger.warning(f"Task timed out: {task_id}")
        
        except asyncio.CancelledError:
            task_result.status = TaskStatus.CANCELLED
            task_result.completed_at = datetime.utcnow()
            logger.info(f"Task cancelled: {task_id}")
        
        except Exception as e:
            task_result.status = TaskStatus.FAILED
            task_result.error_message = str(e)
            task_result.completed_at = datetime.utcnow()
            logger.error(f"Task failed: {task_id} - {e}", exc_info=True)
        
        finally:
            # Remove from running tasks
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
    
    async def _cleanup_loop(self):
        """Background loop to cleanup old tasks and results"""
        while True:
            try:
                await self._cleanup_completed_tasks()
                await asyncio.sleep(300)  # Run cleanup every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cleanup_completed_tasks(self):
        """Remove old completed tasks from cache"""
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(seconds=self.result_cache_ttl)
        
        tasks_to_remove = []
        
        for task_id, task_result in self._task_results.items():
            if (task_result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT, TaskStatus.CANCELLED] 
                and task_result.completed_at 
                and task_result.completed_at < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            if task_id in self._tasks:
                del self._tasks[task_id]
            if task_id in self._task_results:
                del self._task_results[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")


# Global task queue instance
task_queue = TaskQueue()