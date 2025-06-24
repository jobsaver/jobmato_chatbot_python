#!/bin/bash

# Enhanced WebSocket Setup Script for JobMato Chatbot
# This script sets up the enhanced WebSocket functionality with Redis

set -e

echo "🚀 Setting up Enhanced WebSocket for JobMato Chatbot"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.8+ is installed
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    print_success "Python $python_version is compatible"
else
    print_error "Python 3.8+ is required. Found: $python_version"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip first."
    exit 1
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
pip3 install -r requirements.txt
print_success "Python dependencies installed"

# Check if Redis is installed
print_status "Checking Redis installation..."
if command -v redis-server &> /dev/null; then
    print_success "Redis is already installed"
else
    print_warning "Redis is not installed. Installing Redis..."
    
    # Detect OS and install Redis
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y redis-server
        elif command -v yum &> /dev/null; then
            sudo yum install -y redis
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y redis
        else
            print_error "Could not install Redis automatically. Please install Redis manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install redis
        else
            print_error "Homebrew is required to install Redis on macOS. Please install Homebrew first."
            exit 1
        fi
    else
        print_error "Unsupported OS. Please install Redis manually."
        exit 1
    fi
fi

# Start Redis if not running
print_status "Starting Redis server..."
if ! pgrep -x "redis-server" > /dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start redis
    else
        sudo systemctl start redis-server
        sudo systemctl enable redis-server
    fi
    print_success "Redis server started"
else
    print_success "Redis server is already running"
fi

# Test Redis connection
print_status "Testing Redis connection..."
if redis-cli ping | grep -q "PONG"; then
    print_success "Redis connection successful"
else
    print_error "Redis connection failed. Please check Redis installation."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_status "Creating .env file from template..."
    cp env.example .env
    print_warning "Please edit .env file with your actual configuration values"
else
    print_success ".env file already exists"
fi

# Check if MongoDB is available (optional)
print_status "Checking MongoDB connection..."
if command -v mongod &> /dev/null; then
    if pgrep -x "mongod" > /dev/null; then
        print_success "MongoDB is running"
    else
        print_warning "MongoDB is installed but not running. Starting MongoDB..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew services start mongodb-community
        else
            sudo systemctl start mongod
            sudo systemctl enable mongod
        fi
    fi
else
    print_warning "MongoDB is not installed. The app will use in-memory storage."
    print_warning "For production, consider installing MongoDB for persistent storage."
fi

# Make scripts executable
chmod +x deploy_local.sh
chmod +x start_jobmato.sh

print_success "Enhanced WebSocket setup completed!"
echo ""
echo "🎉 Setup Summary:"
echo "=================="
echo "✅ Python dependencies installed"
echo "✅ Redis server configured and running"
echo "✅ Environment file created"
echo "✅ Scripts made executable"
echo ""
echo "📋 Next Steps:"
echo "=============="
echo "1. Edit .env file with your configuration:"
echo "   - Add your GEMINI_API_KEY"
echo "   - Configure MongoDB URI if needed"
echo "   - Set your SECRET_KEY"
echo ""
echo "2. Start the application:"
echo "   ./start_jobmato.sh"
echo ""
echo "3. Or run in development mode:"
echo "   python3 app.py"
echo ""
echo "🌐 The application will be available at:"
echo "   http://localhost:5002"
echo ""
echo "📚 For more information, check the README.md file" 