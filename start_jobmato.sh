#!/bin/bash

# JobMato Chatbot Production Deployment Script
# This script sets up and runs the JobMato chatbot in production mode

set -e  # Exit on any error

# Configuration
APP_NAME="jobmato_chatbot"
APP_DIR="/var/www/$APP_NAME"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="/var/log/$APP_NAME"
PID_FILE="/var/run/$APP_NAME.pid"
PORT=${PORT:-5000}
HOST=${HOST:-0.0.0.0}
WORKERS=${WORKERS:-4}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check if running as root for system-wide installation
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log "Running as root - setting up system-wide deployment"
    else
        warning "Not running as root - using local deployment"
        APP_DIR="$(pwd)"
        VENV_DIR="$APP_DIR/venv"
        LOG_DIR="$APP_DIR/logs"
        PID_FILE="$APP_DIR/jobmato.pid"
    fi
}

# Create necessary directories
setup_directories() {
    log "Setting up directories..."
    
    # Create app directory if running as root
    if [[ $EUID -eq 0 ]]; then
        mkdir -p "$APP_DIR"
        cd "$APP_DIR"
        
        # Copy files if not already there
        if [ ! -f "$APP_DIR/app.py" ]; then
            log "Copying application files..."
            cp -r /tmp/jobmato_chatbot/* "$APP_DIR/" 2>/dev/null || true
        fi
    fi
    
    mkdir -p "$LOG_DIR"
    mkdir -p "$(dirname "$PID_FILE")"
}

# Install system dependencies
install_system_deps() {
    if [[ $EUID -eq 0 ]]; then
        log "Installing system dependencies..."
        
        # Detect package manager and install Python3 and pip
        if command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y python3 python3-pip python3-venv python3-dev build-essential
        elif command -v yum &> /dev/null; then
            yum install -y python3 python3-pip python3-devel gcc gcc-c++ make
        elif command -v dnf &> /dev/null; then
            dnf install -y python3 python3-pip python3-devel gcc gcc-c++ make
        elif command -v pacman &> /dev/null; then
            pacman -S --noconfirm python python-pip base-devel
        else
            warning "Package manager not detected. Please install Python3, pip, and build tools manually."
        fi
    else
        info "Skipping system dependencies (not running as root)"
    fi
}

# Setup Python virtual environment
setup_venv() {
    log "Setting up Python virtual environment..."
    
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

# Install Python dependencies
install_dependencies() {
    log "Installing Python dependencies..."
    
    source "$VENV_DIR/bin/activate"
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        error "requirements.txt not found"
        exit 1
    fi
    
    # Install production server (gunicorn with eventlet worker)
    pip install gunicorn eventlet
    
    log "Dependencies installed successfully"
}

# Check if app is already running
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
        log "Killing process $PID..."
        kill -TERM "$PID" 2>/dev/null || true
        
        # Wait for graceful shutdown
        for i in {1..10}; do
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

# Start the application
start_app() {
    log "Starting JobMato chatbot on $HOST:$PORT..."
    
    if check_running; then
        warning "Application is already running (PID: $(cat "$PID_FILE"))"
        return 0
    fi
    
    source "$VENV_DIR/bin/activate"
    
    # Change to app directory
    cd "$APP_DIR"
    
    # Start with gunicorn for production
    nohup gunicorn \
        --worker-class eventlet \
        --workers 1 \
        --worker-connections 1000 \
        --bind "$HOST:$PORT" \
        --timeout 120 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --preload \
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
    start_app
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
            tail -n 5 "$LOG_DIR/error.log" 2>/dev/null || echo "No recent errors"
        fi
    else
        warning "❌ JobMato chatbot is not running"
    fi
}

# Show logs
show_logs() {
    if [ -f "$LOG_DIR/error.log" ]; then
        log "📋 Error logs:"
        tail -f "$LOG_DIR/error.log"
    else
        warning "No error log file found"
    fi
}

# Create systemd service (if running as root)
create_service() {
    if [[ $EUID -eq 0 ]]; then
        log "Creating systemd service..."
        
        cat > /etc/systemd/system/jobmato-chatbot.service << EOF
[Unit]
Description=JobMato Chatbot Service
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment=PATH=$VENV_DIR/bin
ExecStart=$APP_DIR/start_jobmato.sh start
ExecStop=$APP_DIR/start_jobmato.sh stop
ExecReload=$APP_DIR/start_jobmato.sh restart
PIDFile=$PID_FILE
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload
        systemctl enable jobmato-chatbot.service
        
        log "✅ Systemd service created. You can now use:"
        log "   systemctl start jobmato-chatbot"
        log "   systemctl stop jobmato-chatbot"
        log "   systemctl restart jobmato-chatbot"
        log "   systemctl status jobmato-chatbot"
    else
        info "Skipping systemd service creation (not running as root)"
    fi
}

# Setup auto-restart with cron (fallback if not using systemd)
setup_cron() {
    if [[ $EUID -ne 0 ]]; then
        log "Setting up cron job for auto-restart monitoring..."
        
        # Create monitor script
        cat > "$APP_DIR/monitor.sh" << EOF
#!/bin/bash
cd "$APP_DIR"
if ! ./start_jobmato.sh status >/dev/null 2>&1; then
    echo "\$(date): JobMato chatbot was down, restarting..." >> "$LOG_DIR/monitor.log"
    ./start_jobmato.sh start
fi
EOF
        
        chmod +x "$APP_DIR/monitor.sh"
        
        # Add to crontab (check every 5 minutes)
        (crontab -l 2>/dev/null; echo "*/5 * * * * $APP_DIR/monitor.sh") | crontab -
        
        log "✅ Cron job created to monitor and restart the application every 5 minutes"
    fi
}

# Main setup function
setup() {
    log "🚀 Setting up JobMato Chatbot for production..."
    
    check_permissions
    setup_directories
    install_system_deps
    setup_venv
    install_dependencies
    
    if [[ $EUID -eq 0 ]]; then
        create_service
    else
        setup_cron
    fi
    
    log "✅ Setup completed successfully!"
    log "🎯 Run './start_jobmato.sh start' to start the application"
}

# Print usage
usage() {
    cat << EOF
Usage: $0 {setup|start|stop|restart|status|logs}

Commands:
  setup     - Set up the environment and install dependencies
  start     - Start the JobMato chatbot
  stop      - Stop the JobMato chatbot  
  restart   - Restart the JobMato chatbot
  status    - Show application status
  logs      - Show application logs

Environment Variables:
  PORT      - Port to run on (default: 5000)
  HOST      - Host to bind to (default: 0.0.0.0)
  WORKERS   - Number of worker processes (default: 4)

Examples:
  PORT=8080 $0 start    # Start on port 8080
  $0 setup              # Initial setup
  $0 restart            # Restart the application
EOF
}

# Main script logic
case "${1:-}" in
    setup)
        setup
        ;;
    start)
        start_app
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