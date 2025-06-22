#!/bin/bash

# JobMato Chatbot Local Development Deployment Script
# Simple script for local testing and development

set -e  # Exit on any error

# Configuration
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
PID_FILE="$APP_DIR/jobmato.pid"
PORT=${PORT:-5000}
HOST=${HOST:-127.0.0.1}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"
}

# Setup virtual environment
setup_venv() {
    log "Setting up virtual environment..."
    
    # Create logs directory
    mkdir -p "$LOG_DIR"
    
    # Remove existing venv if it exists
    if [ -d "$VENV_DIR" ]; then
        warning "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    fi
    
    # Create new virtual environment
    python3 -m venv "$VENV_DIR"
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    log "Virtual environment created successfully"
}

# Install dependencies
install_dependencies() {
    log "Installing dependencies..."
    
    source "$VENV_DIR/bin/activate"
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        error "requirements.txt not found"
        exit 1
    fi
    
    log "Dependencies installed successfully"
}

# Check if app is running
check_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        else
            rm -f "$PID_FILE"  # Stale PID file
            return 1  # Not running
        fi
    fi
    return 1  # Not running
}

# Stop the application
stop_app() {
    log "Stopping JobMato chatbot..."
    
    if check_running; then
        PID=$(cat "$PID_FILE")
        log "Stopping process $PID..."
        kill -TERM "$PID" 2>/dev/null || true
        
        # Wait for graceful shutdown
        for i in {1..5}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if ps -p "$PID" > /dev/null 2>&1; then
            warning "Force killing process $PID..."
            kill -KILL "$PID" 2>/dev/null || true
        fi
        
        rm -f "$PID_FILE"
        log "Application stopped"
    else
        info "Application is not running"
    fi
}

# Start the application in development mode
start_dev() {
    log "Starting JobMato chatbot in development mode on $HOST:$PORT..."
    
    if check_running; then
        warning "Application is already running (PID: $(cat "$PID_FILE"))"
        return 0
    fi
    
    source "$VENV_DIR/bin/activate"
    
    # Change to app directory
    cd "$APP_DIR"
    
    # Start Flask development server
    log "🚀 Starting development server..."
    python app.py &
    
    # Get the PID
    APP_PID=$!
    echo "$APP_PID" > "$PID_FILE"
    
    # Wait a moment and check if it started
    sleep 3
    
    if check_running; then
        log "✅ JobMato chatbot started successfully!"
        log "🌐 Access the chatbot at: http://$HOST:$PORT"
        log "📋 PID: $APP_PID"
        log "📁 Logs: $LOG_DIR/"
        log "🛑 Press Ctrl+C or run './deploy_local.sh stop' to stop"
    else
        error "Failed to start the application"
        return 1
    fi
}

# Start the application in production mode (with gunicorn)
start_prod() {
    log "Starting JobMato chatbot in production mode on $HOST:$PORT..."
    
    if check_running; then
        warning "Application is already running (PID: $(cat "$PID_FILE"))"
        return 0
    fi
    
    source "$VENV_DIR/bin/activate"
    
    # Install gunicorn if not present
    if ! command -v gunicorn &> /dev/null; then
        log "Installing gunicorn..."
        pip install gunicorn eventlet
    fi
    
    # Change to app directory
    cd "$APP_DIR"
    
    # Start with gunicorn
    nohup gunicorn \
        --worker-class eventlet \
        --workers 1 \
        --worker-connections 1000 \
        --bind "$HOST:$PORT" \
        --timeout 120 \
        --keep-alive 5 \
        --access-logfile "$LOG_DIR/access.log" \
        --error-logfile "$LOG_DIR/error.log" \
        --log-level info \
        --pid "$PID_FILE" \
        --daemon \
        app:app
    
    # Wait a moment and check if it started
    sleep 2
    
    if check_running; then
        log "✅ JobMato chatbot started successfully!"
        log "🌐 Access the chatbot at: http://$HOST:$PORT"
        log "📋 PID: $(cat "$PID_FILE")"
        log "📁 Logs: $LOG_DIR/"
    else
        error "Failed to start the application"
        return 1
    fi
}

# Restart the application
restart_app() {
    log "Restarting JobMato chatbot..."
    stop_app
    sleep 2
    start_prod
}

# Show application status
status_app() {
    if check_running; then
        PID=$(cat "$PID_FILE")
        log "✅ JobMato chatbot is running"
        log "📋 PID: $PID"
        log "🌐 URL: http://$HOST:$PORT"
        log "📁 Logs: $LOG_DIR/"
        
        # Show recent logs
        if [ -f "$LOG_DIR/error.log" ]; then
            echo ""
            info "Recent error logs:"
            tail -n 3 "$LOG_DIR/error.log" 2>/dev/null || echo "No recent errors"
        fi
    else
        warning "❌ JobMato chatbot is not running"
    fi
}

# Show logs
show_logs() {
    if [ -f "$LOG_DIR/error.log" ]; then
        log "📋 Error logs (last 20 lines):"
        tail -n 20 "$LOG_DIR/error.log"
        echo ""
        log "📋 Following error logs (press Ctrl+C to stop):"
        tail -f "$LOG_DIR/error.log"
    else
        warning "No error log file found"
    fi
}

# Setup function
setup() {
    log "🚀 Setting up JobMato Chatbot for local development..."
    
    setup_venv
    install_dependencies
    
    log "✅ Setup completed successfully!"
    log "🎯 Run './deploy_local.sh dev' to start in development mode"
    log "🎯 Run './deploy_local.sh prod' to start in production mode"
}

# Print usage
usage() {
    cat << EOF
Usage: $0 {setup|dev|prod|stop|restart|status|logs}

Commands:
  setup     - Set up the virtual environment and install dependencies
  dev       - Start in development mode (Flask dev server)
  prod      - Start in production mode (gunicorn)
  stop      - Stop the JobMato chatbot  
  restart   - Restart the JobMato chatbot
  status    - Show application status
  logs      - Show and follow application logs

Environment Variables:
  PORT      - Port to run on (default: 5000)
  HOST      - Host to bind to (default: 127.0.0.1)

Examples:
  $0 setup              # Initial setup
  $0 dev                # Start in development mode
  PORT=8080 $0 prod     # Start in production mode on port 8080
  $0 restart            # Restart the application
  $0 logs               # View logs
EOF
}

# Main script logic
case "${1:-}" in
    setup)
        setup
        ;;
    dev)
        start_dev
        ;;
    prod)
        start_prod
        ;;
    stop)
        stop_app
        ;;
    restart)
        restart_app
        ;;
    status)
        status_app
        ;;
    logs)
        show_logs
        ;;
    *)
        usage
        exit 1
        ;;
esac

exit 0 