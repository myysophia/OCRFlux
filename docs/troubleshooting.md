# OCRFlux API Service - Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the OCRFlux API service.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Service Startup Issues](#service-startup-issues)
- [Model Loading Problems](#model-loading-problems)
- [Performance Issues](#performance-issues)
- [File Processing Errors](#file-processing-errors)
- [Network and Connectivity](#network-and-connectivity)
- [Docker-Specific Issues](#docker-specific-issues)
- [Memory and Resource Issues](#memory-and-resource-issues)
- [Configuration Problems](#configuration-problems)
- [Logging and Debugging](#logging-and-debugging)

## Quick Diagnostics

### Health Check Commands

```bash
# Basic health check
curl http://localhost:8000/api/v1/health

# Detailed health information
curl http://localhost:8000/api/v1/health/detailed

# Model-specific health
curl http://localhost:8000/api/v1/health/model

# Configuration validation
python scripts/check_config.py

# Docker service status
./scripts/deploy.sh status
```

### System Resource Check

```bash
# CPU and memory usage
htop
# or
top

# Disk space
df -h

# GPU usage (if applicable)
nvidia-smi

# Docker resource usage
docker stats

# Network connections
netstat -tlnp | grep 8000
```

## Service Startup Issues

### Issue: Service Fails to Start

**Symptoms:**
- Service exits immediately after startup
- "Connection refused" errors
- Docker container keeps restarting

**Diagnosis:**
```bash
# Check service logs
docker logs ocrflux-api --tail 50

# Check configuration
python scripts/check_config.py

# Verify port availability
netstat -tlnp | grep 8000
```

**Solutions:**

1. **Port Already in Use**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   
   # Kill the process or change port
   export PORT=8001
   ./scripts/deploy.sh restart
   ```

2. **Configuration Errors**
   ```bash
   # Fix configuration file
   nano .env
   
   # Validate configuration
   python scripts/check_config.py
   ```

3. **Permission Issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   chmod +x scripts/deploy.sh
   ```

### Issue: Import Errors on Startup

**Symptoms:**
- "ModuleNotFoundError" in logs
- "No module named 'vllm'" errors

**Solutions:**

1. **Missing Dependencies**
   ```bash
   # Reinstall dependencies
   pip install -e .
   
   # Or rebuild Docker image
   ./scripts/deploy.sh --build up
   ```

2. **Python Version Issues**
   ```bash
   # Check Python version
   python --version
   
   # Should be 3.11+
   # Install correct version if needed
   ```

## Model Loading Problems

### Issue: Model Not Found

**Symptoms:**
- "Model path does not exist" errors
- Service starts but model health check fails

**Diagnosis:**
```bash
# Check model path
echo $MODEL_PATH
ls -la $MODEL_PATH

# Check model health
curl http://localhost:8000/api/v1/health/model
```

**Solutions:**

1. **Download Model**
   ```bash
   # Download OCRFlux model (example)
   mkdir -p models
   # Download from official repository
   # Update MODEL_PATH in .env
   ```

2. **Fix Model Path**
   ```bash
   # Update .env file
   nano .env
   # Set correct MODEL_PATH
   
   # Restart service
   ./scripts/deploy.sh restart
   ```

### Issue: Model Loading Timeout

**Symptoms:**
- Service takes very long to start
- "Model loading timeout" errors
- High memory usage during startup

**Solutions:**

1. **Increase Memory**
   ```bash
   # For Docker deployment
   export MEMORY_LIMIT=8G
   ./scripts/deploy.sh restart
   ```

2. **Adjust GPU Settings**
   ```bash
   # Reduce GPU memory utilization
   export GPU_MEMORY_UTILIZATION=0.6
   ```

3. **Use CPU-Only Mode**
   ```bash
   # Disable GPU if causing issues
   export CUDA_VISIBLE_DEVICES=""
   ```

### Issue: GPU Not Detected

**Symptoms:**
- Model loads on CPU instead of GPU
- Slow inference performance
- "CUDA not available" warnings

**Diagnosis:**
```bash
# Check GPU availability
nvidia-smi

# Check CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

**Solutions:**

1. **Install NVIDIA Drivers**
   ```bash
   # Ubuntu
   sudo apt install nvidia-driver-470
   
   # Reboot system
   sudo reboot
   ```

2. **Install NVIDIA Docker Runtime**
   ```bash
   # Install nvidia-docker2
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   
   sudo apt-get update
   sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

3. **Enable GPU in Docker Compose**
   ```yaml
   # Uncomment GPU section in docker-compose.yml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
   ```

## Performance Issues

### Issue: Slow Processing Speed

**Symptoms:**
- OCR processing takes much longer than expected
- High CPU usage
- Requests timing out

**Diagnosis:**
```bash
# Monitor resource usage
htop
nvidia-smi -l 1

# Check processing times in logs
docker logs ocrflux-api | grep "processing_time"

# Test with small file
curl -X POST "http://localhost:8000/api/v1/parse" \
  -F "file=@small_test.pdf"
```

**Solutions:**

1. **Optimize Resource Allocation**
   ```bash
   # Increase worker processes
   export WORKERS=4
   
   # Increase concurrent tasks
   export MAX_CONCURRENT_TASKS=8
   
   # Restart service
   ./scripts/deploy.sh restart
   ```

2. **GPU Optimization**
   ```bash
   # Increase GPU memory utilization
   export GPU_MEMORY_UTILIZATION=0.9
   
   # Use tensor parallelism for large models
   export TENSOR_PARALLEL_SIZE=2
   ```

3. **File Size Optimization**
   ```bash
   # Reduce image resolution for faster processing
   export TARGET_LONGEST_IMAGE_DIM=1024
   
   # Skip cross-page merge for speed
   curl -X POST "http://localhost:8000/api/v1/parse" \
     -F "file=@document.pdf" \
     -F "skip_cross_page_merge=true"
   ```

### Issue: High Memory Usage

**Symptoms:**
- System running out of memory
- OOM (Out of Memory) errors
- Service crashes randomly

**Diagnosis:**
```bash
# Check memory usage
free -h
docker stats

# Check for memory leaks
ps aux --sort=-%mem | head -10
```

**Solutions:**

1. **Increase System Memory**
   ```bash
   # Add swap space (temporary solution)
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

2. **Optimize Memory Settings**
   ```bash
   # Reduce GPU memory utilization
   export GPU_MEMORY_UTILIZATION=0.6
   
   # Reduce concurrent tasks
   export MAX_CONCURRENT_TASKS=2
   
   # Set memory limits in Docker
   export MEMORY_LIMIT=4G
   ```

3. **Enable Memory Cleanup**
   ```bash
   # Add to .env
   CLEANUP_INTERVAL_HOURS=1
   MAX_FILE_AGE_HOURS=2
   ```

## File Processing Errors

### Issue: File Upload Fails

**Symptoms:**
- "File too large" errors
- "Unsupported file type" errors
- Upload timeouts

**Solutions:**

1. **File Size Issues**
   ```bash
   # Increase file size limit
   export MAX_FILE_SIZE=209715200  # 200MB
   
   # For Nginx proxy, update client_max_body_size
   # in nginx/conf.d/ocrflux.conf
   ```

2. **File Type Issues**
   ```bash
   # Check supported formats
   curl http://localhost:8000/api-info
   
   # Convert unsupported files
   # PDF: Use pdf2pdf to fix corrupted PDFs
   # Images: Convert to PNG/JPEG
   ```

3. **Upload Timeout**
   ```bash
   # Increase timeout settings
   export REQUEST_TIMEOUT=600  # 10 minutes
   
   # For large files, use async processing
   curl -X POST "http://localhost:8000/api/v1/parse-async" \
     -F "file=@large_file.pdf"
   ```

### Issue: OCR Processing Fails

**Symptoms:**
- "OCR processing failed" errors
- Empty results for valid documents
- Partial processing results

**Diagnosis:**
```bash
# Check specific error messages
docker logs ocrflux-api | grep -i error

# Test with known good file
curl -X POST "http://localhost:8000/api/v1/parse" \
  -F "file=@test_document.pdf"
```

**Solutions:**

1. **File Quality Issues**
   ```bash
   # Increase retry attempts
   curl -X POST "http://localhost:8000/api/v1/parse" \
     -F "file=@document.pdf" \
     -F "max_page_retries=3"
   
   # Adjust image processing
   curl -X POST "http://localhost:8000/api/v1/parse" \
     -F "file=@document.pdf" \
     -F "target_longest_image_dim=1536"
   ```

2. **Model Issues**
   ```bash
   # Check model health
   curl http://localhost:8000/api/v1/health/model
   
   # Restart service to reload model
   ./scripts/deploy.sh restart
   ```

## Network and Connectivity

### Issue: Cannot Access API

**Symptoms:**
- "Connection refused" errors
- Timeouts when accessing API
- 502/503 errors from reverse proxy

**Diagnosis:**
```bash
# Check if service is running
docker ps | grep ocrflux

# Check port binding
netstat -tlnp | grep 8000

# Test local connectivity
curl -v http://localhost:8000/api/v1/health

# Check firewall
sudo ufw status
```

**Solutions:**

1. **Service Not Running**
   ```bash
   # Start service
   ./scripts/deploy.sh up
   
   # Check status
   ./scripts/deploy.sh status
   ```

2. **Firewall Issues**
   ```bash
   # Allow port through firewall
   sudo ufw allow 8000/tcp
   
   # Or use Nginx proxy (recommended)
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

3. **Docker Network Issues**
   ```bash
   # Recreate Docker network
   docker network rm ocrflux-network
   ./scripts/deploy.sh up
   ```

### Issue: CORS Errors

**Symptoms:**
- "CORS policy" errors in browser
- "Access-Control-Allow-Origin" errors

**Solutions:**

1. **Update CORS Settings**
   ```bash
   # Add your domain to CORS_ORIGINS
   export CORS_ORIGINS="https://yourdomain.com,http://localhost:3000"
   
   # Restart service
   ./scripts/deploy.sh restart
   ```

2. **Development Mode**
   ```bash
   # Allow all origins (development only)
   export CORS_ORIGINS="*"
   export DEBUG=true
   ```

## Docker-Specific Issues

### Issue: Docker Build Fails

**Symptoms:**
- Build process stops with errors
- "No space left on device" errors
- Dependency installation failures

**Solutions:**

1. **Clean Docker System**
   ```bash
   # Remove unused containers and images
   docker system prune -a
   
   # Remove unused volumes
   docker volume prune
   ```

2. **Build with More Resources**
   ```bash
   # Increase Docker memory limit
   # In Docker Desktop: Settings > Resources > Memory
   
   # Build with no cache
   docker build --no-cache -t ocrflux-api .
   ```

### Issue: Container Keeps Restarting

**Symptoms:**
- Container exits and restarts repeatedly
- "Exited (1)" status in docker ps

**Diagnosis:**
```bash
# Check container logs
docker logs ocrflux-api --tail 100

# Check exit code
docker ps -a | grep ocrflux-api
```

**Solutions:**

1. **Fix Configuration**
   ```bash
   # Check and fix .env file
   python scripts/check_config.py
   
   # Remove restart policy temporarily
   docker run -it --rm ocrflux-api:latest /bin/bash
   ```

2. **Resource Issues**
   ```bash
   # Increase memory limit
   export MEMORY_LIMIT=8G
   
   # Reduce resource requirements
   export WORKERS=1
   export MAX_CONCURRENT_TASKS=2
   ```

## Memory and Resource Issues

### Issue: Out of Memory Errors

**Symptoms:**
- "OOMKilled" in Docker logs
- System becomes unresponsive
- Service crashes during processing

**Solutions:**

1. **Immediate Relief**
   ```bash
   # Add swap space
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   
   # Restart service
   ./scripts/deploy.sh restart
   ```

2. **Long-term Solutions**
   ```bash
   # Reduce memory usage
   export GPU_MEMORY_UTILIZATION=0.5
   export MAX_CONCURRENT_TASKS=1
   export WORKERS=1
   
   # Enable memory cleanup
   export CLEANUP_INTERVAL_HOURS=0.5
   ```

### Issue: Disk Space Full

**Symptoms:**
- "No space left on device" errors
- Cannot write temporary files
- Log files not updating

**Solutions:**

1. **Clean Temporary Files**
   ```bash
   # Clean OCRFlux temp files
   rm -rf /tmp/ocrflux/*
   
   # Clean Docker system
   docker system prune -a
   
   # Clean logs
   docker logs ocrflux-api > /dev/null
   ```

2. **Configure Cleanup**
   ```bash
   # Enable automatic cleanup
   export CLEANUP_INTERVAL_HOURS=1
   export MAX_FILE_AGE_HOURS=2
   
   # Set up log rotation
   sudo nano /etc/logrotate.d/ocrflux
   ```

## Configuration Problems

### Issue: Environment Variables Not Working

**Symptoms:**
- Settings not taking effect
- Default values used instead of configured ones

**Solutions:**

1. **Check Environment File**
   ```bash
   # Verify .env file exists and is readable
   ls -la .env
   cat .env | grep -v "^#" | grep -v "^$"
   
   # Source environment manually
   set -a; source .env; set +a
   ```

2. **Docker Environment Issues**
   ```bash
   # Check environment in container
   docker exec ocrflux-api env | grep OCRFLUX
   
   # Restart with explicit env file
   ./scripts/deploy.sh --env-file .env restart
   ```

### Issue: Model Path Configuration

**Symptoms:**
- Model not found despite correct path
- Permission denied errors

**Solutions:**

1. **Fix Path and Permissions**
   ```bash
   # Check actual path
   ls -la $MODEL_PATH
   
   # Fix permissions
   sudo chown -R $USER:$USER $MODEL_PATH
   chmod -R 755 $MODEL_PATH
   ```

2. **Docker Volume Issues**
   ```bash
   # Check volume mounting
   docker inspect ocrflux-api | grep -A 10 Mounts
   
   # Fix volume path in .env
   export MODEL_VOLUME_PATH=/absolute/path/to/models
   ```

## Logging and Debugging

### Enable Debug Mode

```bash
# Set debug environment
export DEBUG=true
export LOG_LEVEL=DEBUG

# Restart service
./scripts/deploy.sh restart

# Follow logs
./scripts/deploy.sh logs -f
```

### Collect Diagnostic Information

```bash
#!/bin/bash
# diagnostic_info.sh - Collect system information for troubleshooting

echo "=== OCRFlux API Diagnostic Information ===" > diagnostic.txt
echo "Date: $(date)" >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== System Information ===" >> diagnostic.txt
uname -a >> diagnostic.txt
cat /etc/os-release >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== Docker Information ===" >> diagnostic.txt
docker version >> diagnostic.txt
docker-compose version >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== Service Status ===" >> diagnostic.txt
docker ps | grep ocrflux >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== Resource Usage ===" >> diagnostic.txt
free -h >> diagnostic.txt
df -h >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== Network Status ===" >> diagnostic.txt
netstat -tlnp | grep 8000 >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== Recent Logs ===" >> diagnostic.txt
docker logs ocrflux-api --tail 50 >> diagnostic.txt 2>&1
echo "" >> diagnostic.txt

echo "=== Configuration Check ===" >> diagnostic.txt
python scripts/check_config.py >> diagnostic.txt 2>&1

echo "Diagnostic information saved to diagnostic.txt"
```

### Common Log Messages and Solutions

| Log Message | Cause | Solution |
|-------------|-------|----------|
| "Model not loaded" | Model path incorrect or model not downloaded | Check MODEL_PATH, download model |
| "CUDA out of memory" | GPU memory insufficient | Reduce GPU_MEMORY_UTILIZATION |
| "Connection refused" | Service not running or port blocked | Check service status, firewall |
| "File too large" | Upload exceeds size limit | Increase MAX_FILE_SIZE |
| "Permission denied" | File/directory permissions | Fix permissions with chmod/chown |
| "No space left" | Disk full | Clean temporary files, add storage |

### Getting Help

If you're still experiencing issues:

1. **Collect diagnostic information** using the script above
2. **Check GitHub Issues** for similar problems
3. **Create a new issue** with:
   - Detailed problem description
   - Steps to reproduce
   - System information
   - Relevant log messages
   - Configuration details (without sensitive data)

4. **Contact Support** with diagnostic information

Remember to remove any sensitive information (API keys, passwords, personal data) before sharing diagnostic information.