"""
Model Manager for OCRFlux API Service

This module provides a singleton ModelManager class that manages the vLLM instance
for OCRFlux model loading, initialization, and health checking.
"""
import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import psutil
except ImportError:
    psutil = None

try:
    from vllm import LLM
    VLLM_AVAILABLE = True
except ImportError:
    LLM = None
    VLLM_AVAILABLE = False

try:
    from api.core.config import settings
except ImportError:
    # Fallback settings for testing
    class MockSettings:
        model_path = "/path/to/OCRFlux-3B"
        model_max_context = 8192
        gpu_memory_utilization = 0.8
    settings = MockSettings()


logger = logging.getLogger(__name__)


@dataclass
class ModelHealth:
    """Model health status information"""
    is_loaded: bool
    model_path: str
    load_time: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    gpu_memory_usage_mb: Optional[float] = None
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None


class ModelManager:
    """
    Singleton ModelManager class for managing vLLM instances.
    
    This class ensures only one model instance is loaded at a time and provides
    thread-safe access to the model with health checking capabilities.
    """
    
    _instance: Optional['ModelManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'ModelManager':
        """Implement singleton pattern with thread safety"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize ModelManager (only called once due to singleton)"""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self._model: Optional[LLM] = None
        self._model_lock = threading.RLock()
        self._load_start_time: Optional[float] = None
        self._load_end_time: Optional[float] = None
        self._health_status = ModelHealth(
            is_loaded=False,
            model_path=settings.model_path
        )
        
        logger.info(f"ModelManager initialized with model path: {settings.model_path}")
    
    async def load_model(self) -> None:
        """
        Load the vLLM model asynchronously.
        
        Raises:
            RuntimeError: If model loading fails
            FileNotFoundError: If model path doesn't exist
        """
        with self._model_lock:
            if self._model is not None:
                logger.info("Model already loaded, skipping load operation")
                return
            
            logger.info(f"Starting model load from: {settings.model_path}")
            self._load_start_time = time.time()
            
            try:
                # Run model loading in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                self._model = await loop.run_in_executor(
                    None, 
                    self._load_model_sync
                )
                
                self._load_end_time = time.time()
                load_duration = self._load_end_time - self._load_start_time
                
                # Update health status
                self._health_status.is_loaded = True
                self._health_status.load_time = load_duration
                self._health_status.last_check = datetime.utcnow()
                self._health_status.error_message = None
                
                logger.info(f"Model loaded successfully in {load_duration:.2f} seconds")
                
            except Exception as e:
                self._load_end_time = time.time()
                error_msg = f"Failed to load model: {str(e)}"
                
                # Update health status with error
                self._health_status.is_loaded = False
                self._health_status.error_message = error_msg
                self._health_status.last_check = datetime.utcnow()
                
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg) from e
    
    def _load_model_sync(self):
        """
        Synchronous model loading function.
        
        Returns:
            LLM: Loaded vLLM instance or mock for testing
        """
        if not VLLM_AVAILABLE:
            logger.warning("vLLM not available, using mock model for testing")
            # Return a mock model for testing purposes
            class MockModel:
                def __init__(self):
                    self.model_path = settings.model_path
                    
                def generate(self, *args, **kwargs):
                    return [{"text": "Mock OCR result"}]
            
            return MockModel()
        
        try:
            model = LLM(
                model=settings.model_path,
                gpu_memory_utilization=settings.gpu_memory_utilization,
                max_model_len=settings.model_max_context,
                trust_remote_code=True,
                # Additional vLLM parameters for stability
                enforce_eager=False,
                disable_log_stats=True,
            )
            return model
            
        except Exception as e:
            logger.error(f"Error in synchronous model loading: {str(e)}")
            raise
    
    async def get_model_instance(self):
        """
        Get the loaded model instance.
        
        Returns:
            LLM: The loaded vLLM instance
            
        Raises:
            RuntimeError: If model is not loaded
        """
        with self._model_lock:
            if self._model is None:
                raise RuntimeError("Model not loaded. Call load_model() first.")
            return self._model
    
    def is_model_ready(self) -> bool:
        """
        Check if model is loaded and ready for inference.
        
        Returns:
            bool: True if model is ready, False otherwise
        """
        with self._model_lock:
            return self._model is not None and self._health_status.is_loaded
    
    async def health_check(self) -> ModelHealth:
        """
        Perform comprehensive health check of the model and system.
        
        Returns:
            ModelHealth: Current health status
        """
        try:
            # Update memory usage information
            process = psutil.Process()
            memory_info = process.memory_info()
            self._health_status.memory_usage_mb = memory_info.rss / 1024 / 1024
            
            # Try to get GPU memory usage if available
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.memory_allocated() / 1024 / 1024
                    self._health_status.gpu_memory_usage_mb = gpu_memory
            except ImportError:
                logger.debug("PyTorch not available for GPU memory monitoring")
            except Exception as e:
                logger.debug(f"Could not get GPU memory usage: {e}")
            
            # Update last check time
            self._health_status.last_check = datetime.utcnow()
            
            # Verify model is still accessible
            with self._model_lock:
                if self._model is None:
                    self._health_status.is_loaded = False
                    self._health_status.error_message = "Model instance is None"
                else:
                    # Model is loaded and accessible
                    self._health_status.is_loaded = True
                    if self._health_status.error_message == "Model instance is None":
                        self._health_status.error_message = None
            
            return self._health_status
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            self._health_status.error_message = error_msg
            self._health_status.last_check = datetime.utcnow()
            
            return self._health_status
    
    async def unload_model(self) -> None:
        """
        Unload the model and free resources.
        
        This method is useful for testing or when the model needs to be reloaded.
        """
        with self._model_lock:
            if self._model is not None:
                logger.info("Unloading model...")
                
                # Clean up model resources
                try:
                    # vLLM doesn't have explicit cleanup, but we can delete the reference
                    del self._model
                    self._model = None
                    
                    # Force garbage collection
                    import gc
                    gc.collect()
                    
                    # Clear CUDA cache if available
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except ImportError:
                        pass
                    
                except Exception as e:
                    logger.warning(f"Error during model cleanup: {e}")
                
                # Update health status
                self._health_status.is_loaded = False
                self._health_status.error_message = None
                self._health_status.last_check = datetime.utcnow()
                
                logger.info("Model unloaded successfully")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get basic model information.
        
        Returns:
            Dict[str, Any]: Model information including path, status, and timing
        """
        load_time = None
        if self._load_start_time and self._load_end_time:
            load_time = self._load_end_time - self._load_start_time
        
        return {
            "model_path": settings.model_path,
            "is_loaded": self.is_model_ready(),
            "load_time_seconds": load_time,
            "max_context_length": settings.model_max_context,
            "gpu_memory_utilization": settings.gpu_memory_utilization,
            "health_status": {
                "is_loaded": self._health_status.is_loaded,
                "memory_usage_mb": self._health_status.memory_usage_mb,
                "gpu_memory_usage_mb": self._health_status.gpu_memory_usage_mb,
                "last_check": self._health_status.last_check.isoformat() if self._health_status.last_check else None,
                "error_message": self._health_status.error_message
            }
        }


# Global model manager instance
model_manager = ModelManager()