#!/bin/bash
# OCRFlux API Service - Docker Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_DIR}/.env"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"

# Default values
PROFILE="default"
ACTION="up"
BUILD=false
PULL=false
LOGS=false
FOLLOW_LOGS=false

# Functions
print_usage() {
    cat << EOF
OCRFlux API Service - Docker Deployment Script

Usage: $0 [OPTIONS] [ACTION]

ACTIONS:
    up          Start the services (default)
    down        Stop the services
    restart     Restart the services
    logs        Show logs
    status      Show service status
    build       Build the images
    pull        Pull the latest images
    clean       Clean up containers and volumes
    health      Check service health

OPTIONS:
    -p, --profile PROFILE   Docker Compose profile to use
                           (default, with-redis, with-nginx, with-monitoring)
    -e, --env-file FILE     Environment file to use (default: .env)
    -b, --build            Build images before starting
    -P, --pull             Pull images before starting
    -f, --follow           Follow logs (for logs action)
    -h, --help             Show this help message

PROFILES:
    default         Basic OCRFlux API service only
    with-redis      Include Redis for caching
    with-nginx      Include Nginx reverse proxy
    with-monitoring Include Prometheus and Grafana
    all             Include all optional services

EXAMPLES:
    $0                                    # Start basic service
    $0 -p with-redis up                  # Start with Redis
    $0 -p with-nginx -b up               # Start with Nginx and build
    $0 -p all up                         # Start all services
    $0 logs -f                           # Follow logs
    $0 down                              # Stop services
    $0 clean                             # Clean up everything

EOF
}

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

check_requirements() {
    log "Checking requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    log "Requirements check passed"
}

setup_environment() {
    log "Setting up environment..."
    
    # Check if .env file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f "${PROJECT_DIR}/.env.example" ]]; then
            warn ".env file not found. Creating from .env.example"
            cp "${PROJECT_DIR}/.env.example" "$ENV_FILE"
            warn "Please review and update the .env file before proceeding"
        else
            error ".env file not found and no .env.example available"
            exit 1
        fi
    fi
    
    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    log "Environment setup complete"
}

get_compose_command() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        echo "docker compose"
    fi
}

build_images() {
    log "Building Docker images..."
    
    local compose_cmd=$(get_compose_command)
    local profile_args=""
    
    if [[ "$PROFILE" != "default" ]]; then
        if [[ "$PROFILE" == "all" ]]; then
            profile_args="--profile with-redis --profile with-nginx --profile with-monitoring"
        else
            profile_args="--profile $PROFILE"
        fi
    fi
    
    $compose_cmd -f "$COMPOSE_FILE" $profile_args build
    
    log "Image build complete"
}

pull_images() {
    log "Pulling Docker images..."
    
    local compose_cmd=$(get_compose_command)
    local profile_args=""
    
    if [[ "$PROFILE" != "default" ]]; then
        if [[ "$PROFILE" == "all" ]]; then
            profile_args="--profile with-redis --profile with-nginx --profile with-monitoring"
        else
            profile_args="--profile $PROFILE"
        fi
    fi
    
    $compose_cmd -f "$COMPOSE_FILE" $profile_args pull
    
    log "Image pull complete"
}

start_services() {
    log "Starting OCRFlux API services..."
    
    local compose_cmd=$(get_compose_command)
    local profile_args=""
    local build_args=""
    
    if [[ "$PROFILE" != "default" ]]; then
        if [[ "$PROFILE" == "all" ]]; then
            profile_args="--profile with-redis --profile with-nginx --profile with-monitoring"
        else
            profile_args="--profile $PROFILE"
        fi
    fi
    
    if [[ "$BUILD" == true ]]; then
        build_args="--build"
    fi
    
    if [[ "$PULL" == true ]]; then
        pull_images
    fi
    
    $compose_cmd -f "$COMPOSE_FILE" $profile_args up -d $build_args
    
    log "Services started successfully"
    show_status
}

stop_services() {
    log "Stopping OCRFlux API services..."
    
    local compose_cmd=$(get_compose_command)
    local profile_args=""
    
    if [[ "$PROFILE" != "default" ]]; then
        if [[ "$PROFILE" == "all" ]]; then
            profile_args="--profile with-redis --profile with-nginx --profile with-monitoring"
        else
            profile_args="--profile $PROFILE"
        fi
    fi
    
    $compose_cmd -f "$COMPOSE_FILE" $profile_args down
    
    log "Services stopped successfully"
}

restart_services() {
    log "Restarting OCRFlux API services..."
    stop_services
    start_services
}

show_logs() {
    log "Showing service logs..."
    
    local compose_cmd=$(get_compose_command)
    local profile_args=""
    local follow_args=""
    
    if [[ "$PROFILE" != "default" ]]; then
        if [[ "$PROFILE" == "all" ]]; then
            profile_args="--profile with-redis --profile with-nginx --profile with-monitoring"
        else
            profile_args="--profile $PROFILE"
        fi
    fi
    
    if [[ "$FOLLOW_LOGS" == true ]]; then
        follow_args="-f"
    fi
    
    $compose_cmd -f "$COMPOSE_FILE" $profile_args logs $follow_args
}

show_status() {
    log "Service status:"
    
    local compose_cmd=$(get_compose_command)
    local profile_args=""
    
    if [[ "$PROFILE" != "default" ]]; then
        if [[ "$PROFILE" == "all" ]]; then
            profile_args="--profile with-redis --profile with-nginx --profile with-monitoring"
        else
            profile_args="--profile $PROFILE"
        fi
    fi
    
    $compose_cmd -f "$COMPOSE_FILE" $profile_args ps
}

check_health() {
    log "Checking service health..."
    
    # Check main API service
    if curl -f -s http://localhost:${OCRFLUX_PORT:-8000}/api/v1/health > /dev/null; then
        log "✅ OCRFlux API service is healthy"
    else
        error "❌ OCRFlux API service is not responding"
    fi
    
    # Check Redis if enabled
    if [[ "$PROFILE" == "with-redis" || "$PROFILE" == "all" ]]; then
        if docker exec ocrflux-redis redis-cli ping > /dev/null 2>&1; then
            log "✅ Redis service is healthy"
        else
            warn "⚠️  Redis service is not responding"
        fi
    fi
    
    # Check Nginx if enabled
    if [[ "$PROFILE" == "with-nginx" || "$PROFILE" == "all" ]]; then
        if curl -f -s http://localhost:${NGINX_HTTP_PORT:-80}/health > /dev/null; then
            log "✅ Nginx service is healthy"
        else
            warn "⚠️  Nginx service is not responding"
        fi
    fi
}

clean_up() {
    log "Cleaning up Docker resources..."
    
    local compose_cmd=$(get_compose_command)
    
    # Stop and remove containers
    $compose_cmd -f "$COMPOSE_FILE" --profile with-redis --profile with-nginx --profile with-monitoring down -v
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (be careful with this)
    read -p "Do you want to remove all unused volumes? This will delete all data! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
        log "Volumes cleaned up"
    else
        log "Volumes preserved"
    fi
    
    log "Cleanup complete"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -e|--env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        -b|--build)
            BUILD=true
            shift
            ;;
        -P|--pull)
            PULL=true
            shift
            ;;
        -f|--follow)
            FOLLOW_LOGS=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        up|down|restart|logs|status|build|pull|clean|health)
            ACTION="$1"
            shift
            ;;
        *)
            error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log "OCRFlux API Service - Docker Deployment"
    log "Profile: $PROFILE"
    log "Action: $ACTION"
    log "Project Directory: $PROJECT_DIR"
    
    check_requirements
    setup_environment
    
    case $ACTION in
        up)
            start_services
            ;;
        down)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        build)
            build_images
            ;;
        pull)
            pull_images
            ;;
        clean)
            clean_up
            ;;
        health)
            check_health
            ;;
        *)
            error "Unknown action: $ACTION"
            print_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"