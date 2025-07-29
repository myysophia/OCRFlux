"""
Configuration management for OCRFlux API Service
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # 服务配置
    app_name: str = Field(default="OCRFlux API Service", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    
    # 模型配置
    model_path: str = Field(default="/path/to/OCRFlux-3B", description="Path to OCRFlux model")
    model_max_context: int = Field(default=8192, description="Maximum context length for model")
    gpu_memory_utilization: float = Field(default=0.8, description="GPU memory utilization ratio")
    
    # 文件处理配置
    max_file_size: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes (100MB)")
    allowed_extensions: List[str] = Field(
        default=[".pdf", ".png", ".jpg", ".jpeg"], 
        description="Allowed file extensions"
    )
    temp_dir: str = Field(default="/tmp/ocrflux", description="Temporary directory for file processing")
    
    # 任务队列配置
    max_concurrent_tasks: int = Field(default=4, description="Maximum concurrent tasks")
    task_timeout: int = Field(default=300, description="Task timeout in seconds (5 minutes)")
    result_cache_ttl: int = Field(default=3600, description="Result cache TTL in seconds (1 hour)")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    # API配置
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    docs_url: str = Field(default="/docs", description="Swagger UI URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc URL")
    openapi_url: str = Field(default="/openapi.json", description="OpenAPI schema URL")
    
    # CORS配置
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_methods: List[str] = Field(default=["*"], description="CORS allowed methods")
    cors_headers: List[str] = Field(default=["*"], description="CORS allowed headers")
    
    # 中间件配置
    enable_rate_limiting: bool = Field(default=False, description="Enable rate limiting middleware")
    rate_limit_per_minute: int = Field(default=60, description="Requests per minute per IP")
    rate_limit_per_hour: int = Field(default=1000, description="Requests per hour per IP")
    rate_limit_strategy: str = Field(default="sliding_window", description="Rate limiting strategy")
    
    # 请求验证配置
    enable_request_id: bool = Field(default=True, description="Enable request ID generation")
    request_timeout: int = Field(default=300, description="Request timeout in seconds")
    
    # 安全配置
    trusted_proxies: List[str] = Field(default=[], description="List of trusted proxy IPs")
    max_request_headers: int = Field(default=100, description="Maximum number of request headers")
    max_header_size: int = Field(default=8192, description="Maximum header size in bytes")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }
        
    def create_temp_dir(self) -> None:
        """Create temporary directory if it doesn't exist"""
        os.makedirs(self.temp_dir, exist_ok=True)


# Global settings instance
settings = Settings()