# OCRFlux API Service - Deployment Guide

This comprehensive guide covers all aspects of deploying the OCRFlux API service in various environments, from development to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Deployment](#development-deployment)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+) or macOS 10.15+
- **CPU**: 4 cores (x86_64)
- **RAM**: 8GB
- **Storage**: 20GB available space
- **Python**: 3.11 or higher
- **Docker**: 20.10+ (for containerized deployment)

**Recommended for Production:**
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 50GB+ SSD
- **GPU**: NVIDIA GPU with 8GB+ VRAM (optional, for better performance)
- **Network**: Stable internet connection for model downloads

### Software Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    poppler-utils libmagic1 fonts-liberation curl git

# CentOS/RHEL
sudo yum install -y python3.11 python3-pip poppler-utils \
    file libmagic fontconfig curl git

# macOS (with Homebrew)
brew install python@3.11 poppler libmagic
```

## Development Deployment

### Local Development Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-org/ocrflux-api.git
   cd ocrflux-api
   ```

2. **Create Virtual Environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   nano .env
   ```

5. **Validate Configuration**
   ```bash
   python scripts/check_config.py
   ```

6. **Start Development Server**
   ```bash
   python run_server.py --mode dev --reload
   ```

The service will be available at `http://localhost:8000`

### Development Configuration

Key settings for development (`.env` file):

```bash
# Development settings
DEBUG=true
LOG_LEVEL=DEBUG
ENABLE_RATE_LIMITING=false
CORS_ORIGINS=*

# Model configuration (adjust path)
MODEL_PATH=/path/to/your/OCRFlux-3B

# Resource settings
MAX_CONCURRENT_TASKS=2
WORKERS=1
```

## Docker Deployment

### Quick Start with Docker

1. **Clone and Configure**
   ```bash
   git clone https://github.com/your-org/ocrflux-api.git
   cd ocrflux-api
   cp .env.example .env
   # Edit .env as needed
   ```

2. **Start Basic Service**
   ```bash
   ./scripts/deploy.sh up
   ```

3. **Check Service Health**
   ```bash
   ./scripts/deploy.sh health
   ```

### Docker Deployment Options

#### Basic Deployment
```bash
# Start basic OCRFlux API service
./scripts/deploy.sh up

# View logs
./scripts/deploy.sh logs

# Stop service
./scripts/deploy.sh down
```

#### With Redis Caching
```bash
# Start with Redis for result caching
./scripts/deploy.sh -p with-redis up

# Check Redis status
docker exec ocrflux-redis redis-cli ping
```

#### With Nginx Reverse Proxy
```bash
# Start with Nginx for load balancing and SSL
./scripts/deploy.sh -p with-nginx up

# Service available at http://localhost (port 80)
curl http://localhost/api/v1/health
```

#### Full Production Stack
```bash
# Start with all services (Redis, Nginx, Monitoring)
./scripts/deploy.sh -p all up

# Access services:
# - API: http://localhost
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
```

### Docker Configuration

#### Environment Variables

Key Docker environment variables (`.env` file):

```bash
# Docker-specific settings
OCRFLUX_PORT=8000
WORKERS=2
MEMORY_LIMIT=4G
CPU_LIMIT=2.0

# Volume paths
MODEL_VOLUME_PATH=./models
CONFIG_PATH=./config

# Optional services
REDIS_PORT=6379
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

#### Volume Management

```bash
# List Docker volumes
docker volume ls | grep ocrflux

# Backup volumes
docker run --rm -v ocrflux-models:/data -v $(pwd):/backup \
    alpine tar czf /backup/models-backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v ocrflux-models:/data -v $(pwd):/backup \
    alpine tar xzf /backup/models-backup.tar.gz -C /data
```

## Production Deployment

### Production Environment Setup

1. **Server Preparation**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Docker and Docker Compose
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
       -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Application Deployment**
   ```bash
   # Clone to production directory
   sudo mkdir -p /opt/ocrflux
   sudo chown $USER:$USER /opt/ocrflux
   cd /opt/ocrflux
   
   git clone https://github.com/your-org/ocrflux-api.git .
   ```

3. **Production Configuration**
   ```bash
   # Create production environment file
   cp .env.example .env.production
   
   # Edit production settings
   nano .env.production
   ```

4. **SSL Certificate Setup** (if using HTTPS)
   ```bash
   # Create SSL directory
   mkdir -p ssl
   
   # Option 1: Self-signed certificate (development/testing)
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
       -keyout ssl/key.pem -out ssl/cert.pem
   
   # Option 2: Let's Encrypt (production)
   sudo apt install certbot
   sudo certbot certonly --standalone -d your-domain.com
   sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
   sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
   sudo chown $USER:$USER ssl/*.pem
   ```

5. **Start Production Services**
   ```bash
   # Start with full production stack
   ./scripts/deploy.sh -p all --env-file .env.production up
   ```

### Production Configuration

Production environment settings (`.env.production`):

```bash
# Production settings
DEBUG=false
LOG_LEVEL=INFO
ENABLE_RATE_LIMITING=true

# Security settings
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Performance settings
WORKERS=4
MAX_CONCURRENT_TASKS=8
MEMORY_LIMIT=8G
CPU_LIMIT=4.0

# SSL settings
NGINX_HTTPS_PORT=443
SSL_CERT_PATH=./ssl

# Monitoring
GRAFANA_PASSWORD=your_secure_password
```

### Systemd Service (Alternative to Docker)

For non-Docker production deployments:

1. **Create Service File**
   ```bash
   sudo nano /etc/systemd/system/ocrflux-api.service
   ```

   ```ini
   [Unit]
   Description=OCRFlux API Service
   After=network.target
   
   [Service]
   Type=exec
   User=ocrflux
   Group=ocrflux
   WorkingDirectory=/opt/ocrflux
   Environment=PATH=/opt/ocrflux/venv/bin
   ExecStart=/opt/ocrflux/venv/bin/python run_server.py --mode prod
   ExecReload=/bin/kill -HUP $MAINPID
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and Start Service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ocrflux-api
   sudo systemctl start ocrflux-api
   sudo systemctl status ocrflux-api
   ```

## Cloud Deployment

### AWS Deployment

#### Using AWS ECS with Fargate

1. **Create Task Definition**
   ```json
   {
     "family": "ocrflux-api",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "2048",
     "memory": "4096",
     "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "ocrflux-api",
         "image": "your-account.dkr.ecr.region.amazonaws.com/ocrflux-api:latest",
         "portMappings": [
           {
             "containerPort": 8000,
             "protocol": "tcp"
           }
         ],
         "environment": [
           {"name": "DEBUG", "value": "false"},
           {"name": "LOG_LEVEL", "value": "INFO"}
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/ocrflux-api",
             "awslogs-region": "us-west-2",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

2. **Deploy with AWS CLI**
   ```bash
   # Build and push Docker image
   aws ecr get-login-password --region us-west-2 | \
       docker login --username AWS --password-stdin \
       your-account.dkr.ecr.us-west-2.amazonaws.com
   
   docker build -t ocrflux-api .
   docker tag ocrflux-api:latest \
       your-account.dkr.ecr.us-west-2.amazonaws.com/ocrflux-api:latest
   docker push your-account.dkr.ecr.us-west-2.amazonaws.com/ocrflux-api:latest
   
   # Create ECS service
   aws ecs create-service \
       --cluster your-cluster \
       --service-name ocrflux-api \
       --task-definition ocrflux-api:1 \
       --desired-count 2 \
       --launch-type FARGATE \
       --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
   ```

#### Using AWS EC2 with Auto Scaling

1. **Create Launch Template**
   ```bash
   # User data script for EC2 instances
   #!/bin/bash
   yum update -y
   yum install -y docker
   service docker start
   usermod -a -G docker ec2-user
   
   # Install Docker Compose
   curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
       -o /usr/local/bin/docker-compose
   chmod +x /usr/local/bin/docker-compose
   
   # Deploy application
   cd /opt
   git clone https://github.com/your-org/ocrflux-api.git
   cd ocrflux-api
   cp .env.example .env
   ./scripts/deploy.sh -p with-nginx up
   ```

### Google Cloud Platform (GCP)

#### Using Cloud Run

1. **Build and Deploy**
   ```bash
   # Build image
   gcloud builds submit --tag gcr.io/your-project/ocrflux-api
   
   # Deploy to Cloud Run
   gcloud run deploy ocrflux-api \
       --image gcr.io/your-project/ocrflux-api \
       --platform managed \
       --region us-central1 \
       --allow-unauthenticated \
       --memory 4Gi \
       --cpu 2 \
       --timeout 900 \
       --set-env-vars DEBUG=false,LOG_LEVEL=INFO
   ```

#### Using GKE (Kubernetes)

1. **Create Kubernetes Manifests**
   ```yaml
   # deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: ocrflux-api
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: ocrflux-api
     template:
       metadata:
         labels:
           app: ocrflux-api
       spec:
         containers:
         - name: ocrflux-api
           image: gcr.io/your-project/ocrflux-api:latest
           ports:
           - containerPort: 8000
           env:
           - name: DEBUG
             value: "false"
           - name: LOG_LEVEL
             value: "INFO"
           resources:
             requests:
               memory: "2Gi"
               cpu: "1"
             limits:
               memory: "4Gi"
               cpu: "2"
   ```

2. **Deploy to GKE**
   ```bash
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml
   kubectl apply -f ingress.yaml
   ```

### Azure Deployment

#### Using Azure Container Instances

```bash
# Create resource group
az group create --name ocrflux-rg --location eastus

# Deploy container
az container create \
    --resource-group ocrflux-rg \
    --name ocrflux-api \
    --image your-registry.azurecr.io/ocrflux-api:latest \
    --cpu 2 \
    --memory 4 \
    --ports 8000 \
    --environment-variables DEBUG=false LOG_LEVEL=INFO \
    --dns-name-label ocrflux-api-unique
```

## Monitoring and Maintenance

### Health Monitoring

1. **Setup Health Checks**
   ```bash
   # Add to crontab for regular health checks
   */5 * * * * curl -f http://localhost:8000/api/v1/health || echo "OCRFlux API is down" | mail -s "Alert" admin@yourdomain.com
   ```

2. **Prometheus Monitoring** (with monitoring profile)
   ```yaml
   # prometheus.yml
   global:
     scrape_interval: 15s
   
   scrape_configs:
     - job_name: 'ocrflux-api'
       static_configs:
         - targets: ['ocrflux-api:8000']
       metrics_path: '/metrics'
   ```

### Log Management

1. **Log Rotation**
   ```bash
   # Add to /etc/logrotate.d/ocrflux
   /opt/ocrflux/logs/*.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
       create 644 ocrflux ocrflux
       postrotate
           docker kill -s USR1 ocrflux-api
       endscript
   }
   ```

2. **Centralized Logging** (ELK Stack)
   ```yaml
   # Add to docker-compose.yml
   filebeat:
     image: docker.elastic.co/beats/filebeat:7.15.0
     volumes:
       - ocrflux-logs:/var/log/ocrflux:ro
       - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
   ```

### Backup and Recovery

1. **Database Backup** (if using persistent storage)
   ```bash
   # Backup script
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   docker run --rm -v ocrflux-models:/data -v $(pwd)/backups:/backup \
       alpine tar czf /backup/models_$DATE.tar.gz -C /data .
   
   # Keep only last 7 days of backups
   find ./backups -name "models_*.tar.gz" -mtime +7 -delete
   ```

2. **Configuration Backup**
   ```bash
   # Backup configuration and environment files
   tar czf config_backup_$(date +%Y%m%d).tar.gz .env* nginx/ monitoring/
   ```

### Updates and Maintenance

1. **Rolling Updates**
   ```bash
   # Update with zero downtime
   ./scripts/deploy.sh pull
   ./scripts/deploy.sh -p all up --build
   ```

2. **Security Updates**
   ```bash
   # Update base images
   docker pull python:3.11-slim
   docker pull nginx:alpine
   docker pull redis:7-alpine
   
   # Rebuild and deploy
   ./scripts/deploy.sh -p all --build up
   ```

## Security Considerations

### Network Security

1. **Firewall Configuration**
   ```bash
   # UFW (Ubuntu)
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   
   # Block direct access to API port
   sudo ufw deny 8000/tcp
   ```

2. **Docker Network Security**
   ```yaml
   # docker-compose.yml
   networks:
     ocrflux-network:
       driver: bridge
       internal: true  # No external access
   ```

### Application Security

1. **Environment Variables Security**
   ```bash
   # Secure .env file permissions
   chmod 600 .env
   chown root:root .env
   ```

2. **Container Security**
   ```dockerfile
   # Run as non-root user
   USER ocrflux
   
   # Read-only root filesystem
   --read-only
   --tmpfs /tmp
   ```

### SSL/TLS Configuration

1. **Nginx SSL Configuration**
   ```nginx
   # Strong SSL configuration
   ssl_protocols TLSv1.2 TLSv1.3;
   ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
   ssl_prefer_server_ciphers off;
   
   # Security headers
   add_header Strict-Transport-Security "max-age=63072000" always;
   add_header X-Frame-Options DENY;
   add_header X-Content-Type-Options nosniff;
   ```

## Troubleshooting

### Common Issues

#### Service Won't Start

1. **Check Configuration**
   ```bash
   python scripts/check_config.py
   ```

2. **Check Docker Logs**
   ```bash
   docker logs ocrflux-api --tail 100
   ```

3. **Check Resource Usage**
   ```bash
   docker stats
   free -h
   df -h
   ```

#### Model Loading Issues

1. **Verify Model Path**
   ```bash
   ls -la $MODEL_PATH
   ```

2. **Check GPU Availability**
   ```bash
   nvidia-smi  # For NVIDIA GPUs
   ```

3. **Memory Issues**
   ```bash
   # Check available memory
   free -h
   
   # Adjust GPU memory utilization
   export GPU_MEMORY_UTILIZATION=0.6
   ```

#### Performance Issues

1. **Monitor Resource Usage**
   ```bash
   # CPU and memory
   htop
   
   # GPU usage
   nvidia-smi -l 1
   
   # Disk I/O
   iotop
   ```

2. **Optimize Configuration**
   ```bash
   # Increase worker processes
   export WORKERS=4
   
   # Increase concurrent tasks
   export MAX_CONCURRENT_TASKS=8
   
   # Adjust file size limits
   export MAX_FILE_SIZE=52428800  # 50MB
   ```

#### Network Issues

1. **Check Port Availability**
   ```bash
   netstat -tlnp | grep 8000
   ss -tlnp | grep 8000
   ```

2. **Test Connectivity**
   ```bash
   curl -v http://localhost:8000/api/v1/health
   telnet localhost 8000
   ```

3. **Check Docker Networks**
   ```bash
   docker network ls
   docker network inspect ocrflux-network
   ```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Set debug environment
export DEBUG=true
export LOG_LEVEL=DEBUG

# Restart service
./scripts/deploy.sh restart

# Follow logs
./scripts/deploy.sh logs -f
```

### Getting Support

For additional support:

1. **Check Documentation**: Review API docs at `/docs`
2. **GitHub Issues**: Report bugs and issues
3. **Community**: Join discussions and forums
4. **Professional Support**: Contact support team

This deployment guide covers most common scenarios. For specific use cases or advanced configurations, consult the official documentation or contact support.