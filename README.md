# OCRFlux API Service

**Fast, efficient, and high-quality OCR powered by open visual language models.**

Transform your PDF documents and images into structured Markdown text with advanced OCR capabilities. Built on state-of-the-art vision-language models, OCRFlux delivers superior text extraction with intelligent document structure recognition.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## 🚀 Key Features

### Core Processing Capabilities
- **📄 Single File Processing**: Upload PDF or image files for immediate OCR processing with real-time results
- **📚 Batch Processing**: Process multiple files simultaneously with intelligent resource management
- **⚡ Asynchronous Processing**: Submit large files for background processing with comprehensive status tracking
- **🔄 Smart Retry Logic**: Configurable retry mechanisms for robust processing of challenging documents

### File Format Support
- **PDF Documents**: Multi-page PDF files with complex layouts, tables, and mixed content
- **Image Files**: PNG, JPG, JPEG images containing text, documents, receipts, and forms
- **Quality Optimization**: Automatic image preprocessing for optimal text recognition

### Advanced Processing Options
- **🔗 Cross-page Merging**: Intelligently merge text elements that span across page boundaries
- **📐 Image Processing**: Adjustable resolution and rotation for optimal OCR accuracy  
- **🎯 Quality Control**: Fallback handling and quality assessment for each processed page
- **⚙️ Configurable Parameters**: Fine-tune processing behavior for different document types

### Enterprise Features
- **📊 Health Monitoring**: Comprehensive system health checks and performance metrics
- **📋 Task Management**: Full lifecycle management for asynchronous processing tasks
- **🔍 Detailed Logging**: Complete audit trail and debugging information
- **📈 Performance Analytics**: Processing statistics and optimization insights

## 📋 Supported File Types

| Format | Extensions | Max Size | Notes |
|--------|------------|----------|-------|
| **PDF** | `.pdf` | 100MB | Multi-page documents, forms, reports |
| **Images** | `.png`, `.jpg`, `.jpeg` | 100MB | Scanned documents, photos, screenshots |

## 🛠️ Quick Start

### Option 1: Docker (Recommended)

The fastest way to get started is using Docker:

```bash
# Clone the repository
git clone https://github.com/your-org/ocrflux-api.git
cd ocrflux-api

# Copy environment configuration
cp .env.example .env

# Start the service
./scripts/deploy.sh up

# Check service status
./scripts/deploy.sh health
```

The API will be available at `http://localhost:8000`

### Option 2: Local Development

For local development and testing:

```bash
# Clone the repository
git clone https://github.com/your-org/ocrflux-api.git
cd ocrflux-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env file with your configuration

# Run configuration check
python scripts/check_config.py

# Start the development server
python run_server.py --mode dev
```

## 📚 API Documentation

Once the service is running, you can access:

- **Interactive API Documentation**: http://localhost:8000/docs
- **Alternative Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Service Information**: http://localhost:8000/api-info

## 🔧 Configuration

### Environment Variables

Key configuration options (see `.env.example` for complete list):

```bash
# Application
APP_NAME=OCRFlux API Service
DEBUG=false
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8000

# Model
MODEL_PATH=/path/to/OCRFlux-3B
GPU_MEMORY_UTILIZATION=0.8

# Processing
MAX_FILE_SIZE=104857600  # 100MB
MAX_CONCURRENT_TASKS=4

# Security
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
ENABLE_RATE_LIMITING=true
```

### Model Setup

1. **Download OCRFlux Model**: Download the OCRFlux-3B model from the official repository
2. **Set Model Path**: Update `MODEL_PATH` in your `.env` file
3. **GPU Configuration**: Adjust `GPU_MEMORY_UTILIZATION` based on your hardware

## 🐳 Docker Deployment

### Basic Deployment

```bash
# Start basic service
./scripts/deploy.sh up

# Start with Redis caching
./scripts/deploy.sh -p with-redis up

# Start with Nginx reverse proxy
./scripts/deploy.sh -p with-nginx up

# Start with full monitoring stack
./scripts/deploy.sh -p with-monitoring up

# Start everything
./scripts/deploy.sh -p all up
```

### Production Deployment

```bash
# Production deployment with build
./scripts/deploy.sh -p with-nginx --build up

# Check service health
./scripts/deploy.sh health

# View logs
./scripts/deploy.sh logs

# Stop services
./scripts/deploy.sh down
```

### Docker Compose Profiles

- **default**: Basic OCRFlux API service
- **with-redis**: Adds Redis for result caching
- **with-nginx**: Adds Nginx reverse proxy with SSL support
- **with-monitoring**: Adds Prometheus and Grafana for monitoring
- **all**: Includes all optional services

## 📖 API Usage Examples

### Single File Processing

```bash
# Process a PDF file
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "skip_cross_page_merge=false"

# Process an image
curl -X POST "http://localhost:8000/api/v1/parse" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@image.png"
```

### Batch Processing

```bash
# Process multiple files
curl -X POST "http://localhost:8000/api/v1/batch" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf" \
  -F "files=@image.png"
```

### Asynchronous Processing

```bash
# Submit async task
TASK_ID=$(curl -X POST "http://localhost:8000/api/v1/parse-async" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@large_document.pdf" | jq -r '.task_id')

# Check task status
curl "http://localhost:8000/api/v1/tasks/$TASK_ID"

# Get results when complete
curl "http://localhost:8000/api/v1/tasks/$TASK_ID/result"
```

### Health Check

```bash
# Basic health check
curl "http://localhost:8000/api/v1/health"

# Detailed health information
curl "http://localhost:8000/api/v1/health/detailed"
```

## 🔍 Monitoring and Observability

### Health Checks

The service provides multiple health check endpoints:

- `/api/v1/health` - Basic health status
- `/api/v1/health/detailed` - Comprehensive system information
- `/api/v1/health/model` - Model-specific health status

### Logging

Structured logging with configurable levels:

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Log to file
export LOG_FILE=/app/logs/ocrflux.log

# View logs in Docker
docker logs ocrflux-api -f
```

### Metrics (with Monitoring Profile)

When using the monitoring profile:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## 🚀 Performance Optimization

### Hardware Requirements

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 20GB
- GPU: Optional (CUDA-compatible for better performance)

**Recommended for Production:**
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 50GB+ SSD
- GPU: 8GB+ VRAM (RTX 3080 or better)

### Tuning Parameters

```bash
# Increase concurrent tasks for more CPU cores
MAX_CONCURRENT_TASKS=8

# Adjust GPU memory usage
GPU_MEMORY_UTILIZATION=0.9

# Increase file size limit for large documents
MAX_FILE_SIZE=209715200  # 200MB

# Optimize for your use case
TASK_TIMEOUT=600  # 10 minutes for very large files
```

## 🔒 Security Considerations

### Production Security Checklist

- [ ] **Environment Variables**: Never commit `.env` files with secrets
- [ ] **CORS Configuration**: Restrict origins to your domains only
- [ ] **Rate Limiting**: Enable rate limiting in production
- [ ] **HTTPS**: Use SSL/TLS certificates (configure in Nginx)
- [ ] **File Validation**: Ensure proper file type validation
- [ ] **Resource Limits**: Set appropriate Docker resource limits
- [ ] **Network Security**: Use Docker networks for service isolation
- [ ] **Regular Updates**: Keep dependencies and base images updated

### Security Configuration

```bash
# Restrict CORS origins
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Enable rate limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60

# Set resource limits in docker-compose.yml
MEMORY_LIMIT=4G
CPU_LIMIT=2.0
```

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run unit tests
pytest tests/test_*.py -v

# Run integration tests
pytest tests/test_*_integration.py -v

# Run all tests with coverage
pytest --cov=api tests/ -v
```

### Configuration Validation

```bash
# Check configuration
python scripts/check_config.py

# Check specific components
python scripts/check_config.py --check deps
python scripts/check_config.py --check config
python scripts/check_config.py --check security
```

## 🛠️ Development

### Development Setup

```bash
# Clone and setup
git clone https://github.com/your-org/ocrflux-api.git
cd ocrflux-api

# Development environment
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Pre-commit hooks
pre-commit install

# Run development server
python run_server.py --mode dev --reload
```

### Project Structure

```
ocrflux-api/
├── api/                    # Main application code
│   ├── core/              # Core components
│   ├── models/            # Pydantic models
│   ├── routes/            # API routes
│   ├── middleware/        # Custom middleware
│   └── services/          # Business logic
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── nginx/                 # Nginx configuration
├── monitoring/            # Monitoring configs
├── docs/                  # Additional documentation
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
├── pyproject.toml         # Python project config
└── README.md              # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📋 Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check configuration
python scripts/check_config.py

# Check Docker status
docker ps
docker logs ocrflux-api

# Check resource usage
docker stats
```

#### Model Loading Issues

```bash
# Verify model path
ls -la $MODEL_PATH

# Check GPU availability
nvidia-smi  # For NVIDIA GPUs

# Check memory usage
free -h
```

#### Performance Issues

```bash
# Monitor resource usage
htop
nvidia-smi -l 1

# Check service metrics
curl http://localhost:8000/api/v1/health/detailed

# Review logs for bottlenecks
docker logs ocrflux-api | grep -i "slow\|timeout\|error"
```

#### Network Issues

```bash
# Check port availability
netstat -tlnp | grep 8000

# Test connectivity
curl -v http://localhost:8000/api/v1/health

# Check Docker networks
docker network ls
docker network inspect ocrflux-network
```

### Getting Help

- **Documentation**: Check `/docs` endpoint for API documentation
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Join community discussions
- **Support**: Contact support@ocrflux.example.com

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OCRFlux](https://github.com/chatdoc-com/OCRFlux) - The underlying OCR engine
- [FastAPI](https://fastapi.tiangolo.com/) - The web framework
- [vLLM](https://github.com/vllm-project/vllm) - High-performance LLM inference
- [Docker](https://www.docker.com/) - Containerization platform

## 📞 Support

For support and questions:

- **Email**: support@ocrflux.example.com
- **Documentation**: http://localhost:8000/docs
- **GitHub Issues**: https://github.com/your-org/ocrflux-api/issues
- **Community**: https://github.com/your-org/ocrflux-api/discussions

---

**Made with ❤️ by the OCRFlux Team**