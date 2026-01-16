#!/bin/bash
# =============================================================================
# DockingVina Deployment Script
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Configuration
# =============================================================================

SERVICE_NAME="dockingvina"
SERVICE_PORT="${SERVICE_PORT:-8002}"
SERVICE_HOST="${SERVICE_HOST:-0.0.0.0}"
WORKERS="${WORKERS:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# =============================================================================
# Functions
# =============================================================================

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    if ! command -v pip &> /dev/null; then
        log_error "pip is not installed"
        exit 1
    fi
    
    log_info "Dependencies check passed"
}

install_package() {
    log_info "Installing package in editable mode..."
    cd "$PROJECT_ROOT"
    pip install -e .
    log_info "Package installed successfully"
}

start_service() {
    log_info "Starting $SERVICE_NAME service..."
    
    cd "$PROJECT_ROOT"
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_warn ".env file not found, using default configuration"
        if [ -f ".env.example" ]; then
            log_info "Copying .env.example to .env"
            cp .env.example .env
        fi
    fi
    
    # Start the service
    python -m dockingvina \
        --host "$SERVICE_HOST" \
        --port "$SERVICE_PORT" \
        --workers "$WORKERS" \
        --log-level "$LOG_LEVEL"
}

start_service_background() {
    log_info "Starting $SERVICE_NAME service in background..."
    
    cd "$PROJECT_ROOT"
    
    nohup python -m dockingvina \
        --host "$SERVICE_HOST" \
        --port "$SERVICE_PORT" \
        --workers "$WORKERS" \
        --log-level "$LOG_LEVEL" \
        > logs/service.log 2>&1 &
    
    echo $! > /tmp/${SERVICE_NAME}.pid
    log_info "Service started with PID $(cat /tmp/${SERVICE_NAME}.pid)"
}

stop_service() {
    log_info "Stopping $SERVICE_NAME service..."
    
    if [ -f "/tmp/${SERVICE_NAME}.pid" ]; then
        PID=$(cat /tmp/${SERVICE_NAME}.pid)
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            log_info "Service stopped (PID: $PID)"
        else
            log_warn "Service is not running"
        fi
        rm -f /tmp/${SERVICE_NAME}.pid
    else
        log_warn "PID file not found"
        
        # Try to find and kill by process name
        pkill -f "dockingvina" || log_warn "No process found to kill"
    fi
}

status_service() {
    log_info "Checking $SERVICE_NAME service status..."
    
    if [ -f "/tmp/${SERVICE_NAME}.pid" ]; then
        PID=$(cat /tmp/${SERVICE_NAME}.pid)
        if ps -p $PID > /dev/null 2>&1; then
            log_info "Service is running (PID: $PID)"
            
            # Check health endpoint
            if command -v curl &> /dev/null; then
                HEALTH=$(curl -s "http://localhost:${SERVICE_PORT}/health" || echo "unreachable")
                log_info "Health check: $HEALTH"
            fi
        else
            log_warn "Service is not running (stale PID file)"
        fi
    else
        # Check if process is running without PID file
        if pgrep -f "dockingvina" > /dev/null; then
            log_info "Service appears to be running (no PID file)"
        else
            log_info "Service is not running"
        fi
    fi
}

run_tests() {
    log_info "Running tests..."
    cd "$PROJECT_ROOT"
    pytest tests/ -v
}

# =============================================================================
# Main
# =============================================================================

case "${1:-}" in
    install)
        check_dependencies
        install_package
        ;;
    start)
        start_service
        ;;
    start-bg)
        start_service_background
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        sleep 2
        start_service_background
        ;;
    status)
        status_service
        ;;
    test)
        run_tests
        ;;
    *)
        echo "Usage: $0 {install|start|start-bg|stop|restart|status|test}"
        echo ""
        echo "Commands:"
        echo "  install   - Install the package"
        echo "  start     - Start the service (foreground)"
        echo "  start-bg  - Start the service (background)"
        echo "  stop      - Stop the service"
        echo "  restart   - Restart the service"
        echo "  status    - Check service status"
        echo "  test      - Run tests"
        echo ""
        echo "Environment variables:"
        echo "  SERVICE_PORT - Service port (default: 8002)"
        echo "  SERVICE_HOST - Service host (default: 0.0.0.0)"
        echo "  WORKERS      - Number of workers (default: 1)"
        echo "  LOG_LEVEL    - Log level (default: info)"
        exit 1
        ;;
esac
