#!/bin/bash

# Deployment script for JobMato Chatbot
# This script sets up the entire Docker environment with SSL certificates

set -e

echo "🚀 Starting JobMato Chatbot deployment..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs/nginx
mkdir -p certbot/conf
mkdir -p certbot/www

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x init-letsencrypt.sh
chmod +x renew-ssl.sh

# Build and start services
echo "🏗️ Building and starting services..."
docker-compose build

# Initialize SSL certificates
echo "🔐 Initializing SSL certificates..."
./init-letsencrypt.sh

# Start all services
echo "🚀 Starting all services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ All services are running successfully!"
else
    echo "❌ Some services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Display service status
echo "📊 Service status:"
docker-compose ps

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Service URLs:"
echo "   - HTTPS: https://chatbot-server.jobmato.com"
echo "   - HTTP (redirects to HTTPS): http://chatbot-server.jobmato.com"
echo ""
echo "🔧 Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop services: docker-compose down"
echo "   - Restart services: docker-compose restart"
echo "   - Renew SSL: ./renew-ssl.sh"
echo ""
echo "📝 SSL certificate will auto-renew every 60 days"
echo "📧 Certificate notifications will be sent to: jobmatofficial@gmail.com" 