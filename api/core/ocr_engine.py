"""
OCR Engine for OCRFlux API Service

This module provides the OCREngine class that encapsulates OCRFlux functionality
for processing PDF documents and images into Markdown format.
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    from vllm import SamplingParams
    VLLM_AVAILABLE = True
except ImportError:
    SamplingParams = None
    VLLM_AVAILABLE = False

# Import OCRFlux modules
try:
    from ocrflux.inference import parse as ocrflux_parse
    from pypdf import PdfReader
except ImportError as e:
    logging.warning(f"OCRFlux modules not available: {e}")
    # Mock for testing
    def ocrflux_parse(llm, file_path, skip_cross_page_merge=False, max_page_retries=0):
        return None
    
    class PdfReader:
        def __init__(self, file_path):
            pass
        def get_num_pages(self):
            return 1

from api.core.model_manager import model_manager


logger = logging.getLogger(__name__)


@dataclass
class ProcessOptions:
    """Options for OCR processing"""
    skip_cross_page_merge: bool = False
    max_page_retries: int = 1
    target_longest_image_dim: int = 1024
    image_rotation: int = 0


@dataclass
class ProcessResult:
    """Result of OCR processing"""
    success: bool
    file_name: str
    file_path: str
    num_pages: int
    document_text: str
    page_texts: Dict[str, str]
    fallback_pages: List[int]
    processing_time: float
    error_message: Optional[str] = None


@dataclass
class EngineStatus:
    """OCR Engine status information"""
    is_ready: bool
    model_loaded: bool
    processing_count: int
    last_processing_time: Optional[float] = None
    error_message: Optional[str] = None


class OCREngine:
    """
    OCR Engine that encapsulates OCRFlux functionality for processing
    PDF documents and images into Markdown format.
    """
    
    def __init__(self):
        """Initialize OCR Engine"""
        self._processing_count = 0
        self._last_processing_time: Optional[float] = None
        self._lock = asyncio.Lock()
        
        logger.info("OCREngine initialized")
    
    async def process_single_file(
        self, 
        file_path: str, 
        options: ProcessOptions = None
    ) -> ProcessResult:
        """
        Process a single file (PDF or image) and convert to Markdown.
        
        Args:
            file_path: Path to the file to process
            options: Processing options
            
        Returns:
            ProcessResult: Processing result with Markdown content
            
        Raises:
            RuntimeError: If model is not ready or processing fails
            FileNotFoundError: If file doesn't exist
        """
        if options is None:
            options = ProcessOptions()
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check if model is ready
        if not model_manager.is_model_ready():
            raise RuntimeError("Model not loaded. Please ensure model is initialized.")
        
        start_time = time.time()
        
        async with self._lock:
            self._processing_count += 1
        
        try:
            logger.info(f"Starting OCR processing for file: {file_path_obj.name}")
            
            # Get model instance
            model = await model_manager.get_model_instance()
            
            # Determine number of pages
            num_pages = await self._get_page_count(file_path)
            
            # Run OCRFlux processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._process_file_sync,
                model,
                file_path,
                options
            )
            
            processing_time = time.time() - start_time
            self._last_processing_time = processing_time
            
            if result is None:
                return ProcessResult(
                    success=False,
                    file_name=file_path_obj.name,
                    file_path=file_path,
                    num_pages=num_pages,
                    document_text="",
                    page_texts={},
                    fallback_pages=list(range(num_pages)),
                    processing_time=processing_time,
                    error_message="OCR processing failed - unable to parse document"
                )
            
            # Extract results
            document_text = result.get("document_text", "")
            page_texts = result.get("page_texts", {})
            fallback_pages = result.get("fallback_pages", [])
            
            logger.info(
                f"OCR processing completed for {file_path_obj.name} "
                f"in {processing_time:.2f}s - {num_pages} pages, "
                f"{len(fallback_pages)} fallback pages"
            )
            
            return ProcessResult(
                success=True,
                file_name=file_path_obj.name,
                file_path=file_path,
                num_pages=num_pages,
                document_text=document_text,
                page_texts=page_texts,
                fallback_pages=fallback_pages,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"OCR processing failed for {file_path_obj.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return ProcessResult(
                success=False,
                file_name=file_path_obj.name,
                file_path=file_path,
                num_pages=await self._get_page_count(file_path),
                document_text="",
                page_texts={},
                fallback_pages=[],
                processing_time=processing_time,
                error_message=error_msg
            )
        
        finally:
            async with self._lock:
                self._processing_count -= 1
    
    async def process_batch_files(
        self, 
        file_paths: List[str], 
        options: ProcessOptions = None
    ) -> List[ProcessResult]:
        """
        Process multiple files in batch.
        
        Args:
            file_paths: List of file paths to process
            options: Processing options
            
        Returns:
            List[ProcessResult]: List of processing results
        """
        if options is None:
            options = ProcessOptions()
        
        logger.info(f"Starting batch processing for {len(file_paths)} files")
        
        results = []
        for file_path in file_paths:
            try:
                result = await self.process_single_file(file_path, options)
                results.append(result)
            except Exception as e:
                # Create error result for failed file
                file_name = Path(file_path).name if Path(file_path).exists() else file_path
                error_result = ProcessResult(
                    success=False,
                    file_name=file_name,
                    file_path=file_path,
                    num_pages=0,
                    document_text="",
                    page_texts={},
                    fallback_pages=[],
                    processing_time=0.0,
                    error_message=f"Failed to process file: {str(e)}"
                )
                results.append(error_result)
                logger.error(f"Batch processing failed for {file_path}: {e}")
        
        successful_count = sum(1 for r in results if r.success)
        logger.info(
            f"Batch processing completed: {successful_count}/{len(file_paths)} files successful"
        )
        
        return results
    
    def _process_file_sync(
        self, 
        model, 
        file_path: str, 
        options: ProcessOptions
    ) -> Optional[Dict[str, Any]]:
        """
        Synchronous file processing using OCRFlux.
        
        Args:
            model: vLLM model instance
            file_path: Path to file to process
            options: Processing options
            
        Returns:
            Dict with processing results or None if failed
        """
        try:
            result = ocrflux_parse(
                llm=model,
                file_path=file_path,
                skip_cross_page_merge=options.skip_cross_page_merge,
                max_page_retries=options.max_page_retries
            )
            return result
            
        except Exception as e:
            logger.error(f"Synchronous OCR processing failed: {e}")
            return None
    
    async def _get_page_count(self, file_path: str) -> int:
        """
        Get the number of pages in a document.
        
        Args:
            file_path: Path to the document
            
        Returns:
            int: Number of pages (1 for images, actual count for PDFs)
        """
        try:
            file_path_lower = file_path.lower()
            
            if file_path_lower.endswith('.pdf'):
                # Run PDF page counting in thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    self._count_pdf_pages,
                    file_path
                )
            else:
                # Images are treated as single page
                return 1
                
        except Exception as e:
            logger.warning(f"Could not determine page count for {file_path}: {e}")
            return 1
    
    def _count_pdf_pages(self, file_path: str) -> int:
        """
        Count pages in a PDF file synchronously.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            int: Number of pages
        """
        try:
            reader = PdfReader(file_path)
            return reader.get_num_pages()
        except Exception as e:
            logger.warning(f"Could not read PDF {file_path}: {e}")
            return 1
    
    def get_engine_status(self) -> EngineStatus:
        """
        Get current engine status.
        
        Returns:
            EngineStatus: Current status information
        """
        try:
            model_loaded = model_manager.is_model_ready()
            is_ready = model_loaded and self._processing_count < 10  # Arbitrary limit
            
            return EngineStatus(
                is_ready=is_ready,
                model_loaded=model_loaded,
                processing_count=self._processing_count,
                last_processing_time=self._last_processing_time
            )
            
        except Exception as e:
            return EngineStatus(
                is_ready=False,
                model_loaded=False,
                processing_count=self._processing_count,
                last_processing_time=self._last_processing_time,
                error_message=str(e)
            )
    
    async def validate_file_format(self, file_path: str) -> bool:
        """
        Validate if file format is supported.
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            bool: True if format is supported
        """
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
        file_extension = Path(file_path).suffix.lower()
        return file_extension in supported_extensions
    
    async def estimate_processing_time(self, file_path: str) -> float:
        """
        Estimate processing time for a file based on page count and historical data.
        
        Args:
            file_path: Path to file
            
        Returns:
            float: Estimated processing time in seconds
        """
        try:
            num_pages = await self._get_page_count(file_path)
            
            # Base time per page (rough estimate)
            base_time_per_page = 2.0  # seconds
            
            # Adjust based on historical data if available
            if self._last_processing_time:
                # Use last processing time as reference
                estimated_time = num_pages * base_time_per_page
            else:
                estimated_time = num_pages * base_time_per_page
            
            return max(estimated_time, 1.0)  # Minimum 1 second
            
        except Exception:
            return 30.0  # Default estimate


# Global OCR engine instance
ocr_engine = OCREngine()