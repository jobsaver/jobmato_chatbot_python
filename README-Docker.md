# JobMato Chatbot - Docker Deployment

This repository contains a complete Docker setup for the JobMato Chatbot Flask application with Nginx reverse proxy and SSL certificates via Certbot.

## 🏗️ Architecture

- **Flask App**: Python Flask application running on port 5003
- **Nginx**: Reverse proxy with SSL termination on ports 80/443
- **Certbot**: Automatic SSL certificate management
- **Redis**: External Redis instance for session management
- **MongoDB**: External MongoDB instance for data persistence

## 📋 Prerequisites

- Docker and Docker Compose installed
- Domain `chatbot-server.jobmato.com` pointing to your server
- Ports 80 and 443 open on your server
- Email `jobmatofficial@gmail.com` for SSL certificate notifications

## 🚀 Quick Start

1. **Clone and navigate to the project:**
   ```bash
   cd jobmato_chatbot_python
   ```

2. **Run the deployment script:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

   This script will:
   - Create necessary directories
   - Build Docker images
   - Initialize SSL certificates
   - Start all services
   - Verify deployment

## 🔧 Manual Setup

If you prefer manual setup:

1. **Create directories:**
   ```bash
   mkdir -p logs/nginx certbot/conf certbot/www
   ```

2. **Make scripts executable:**
   ```bash
   chmod +x init-letsencrypt.sh renew-ssl.sh
   ```

3. **Build and start services:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

4. **Initialize SSL certificates:**
   ```bash
   ./init-letsencrypt.sh
   ```

## 📁 File Structure

```
jobmato_chatbot_python/
├── Dockerfile                 # Flask app container
├── docker-compose.yml         # Multi-service orchestration
├── nginx.conf                 # Nginx configuration
├── init-letsencrypt.sh        # SSL certificate initialization
├── renew-ssl.sh              # SSL certificate renewal
├── deploy.sh                 # Complete deployment script
├── .dockerignore             # Docker build exclusions
├── logs/                     # Application logs
│   └── nginx/               # Nginx logs
└── certbot/                 # SSL certificates
    ├── conf/                # Certificate configuration
    └── www/                 # Webroot for verification
```

## 🔐 SSL Certificate Management

### Initial Setup
The `init-letsencrypt.sh` script handles the initial SSL certificate setup:
- Creates dummy certificates for Nginx startup
- Requests real certificates from Let's Encrypt
- Configures automatic renewal

### Automatic Renewal
SSL certificates auto-renew every 60 days. The renewal process:
1. Certbot checks for expiring certificates
2. Renews certificates if needed
3. Reloads Nginx configuration

### Manual Renewal
To manually renew certificates:
```bash
./renew-ssl.sh
```

## 🌐 Service Endpoints

- **Main Application**: https://chatbot-server.jobmato.com
- **Health Check**: https://chatbot-server.jobmato.com/health
- **API Endpoints**: https://chatbot-server.jobmato.com/api/
- **WebSocket**: wss://chatbot-server.jobmato.com/socket.io/

## 🔧 Configuration

### Environment Variables
Key environment variables in `docker-compose.yml`:
- `FLASK_ENV`: Production environment
- `REDIS_URL`: Redis connection string
- `MONGODB_URI`: MongoDB connection string
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET`: JWT signing secret

### Nginx Configuration
The `nginx.conf` includes:
- SSL/TLS security settings
- Rate limiting
- Gzip compression
- WebSocket proxy support
- Security headers
- File upload limits (10MB)

## 📊 Monitoring and Logs

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f flask
docker-compose logs -f nginx
```

### Health Checks
```bash
# Check service status
docker-compose ps

# Health check endpoint
curl https://chatbot-server.jobmato.com/health
```

## 🛠️ Maintenance

### Restart Services
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart flask
```

### Update Application
```bash
# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup SSL Certificates
```bash
# Backup certificates
tar -czf ssl-backup-$(date +%Y%m%d).tar.gz certbot/
```

## 🔒 Security Features

- **SSL/TLS**: Automatic HTTPS with Let's Encrypt
- **Rate Limiting**: API rate limiting via Nginx
- **Security Headers**: XSS protection, content type options
- **Non-root User**: Flask app runs as non-root user
- **HSTS**: Strict Transport Security headers

## 🚨 Troubleshooting

### Common Issues

1. **SSL Certificate Issues**
   ```bash
   # Check certificate status
   docker-compose exec nginx nginx -t
   
   # Reinitialize certificates
   ./init-letsencrypt.sh
   ```

2. **Service Not Starting**
   ```bash
   # Check logs
   docker-compose logs flask
   
   # Check health
   docker-compose ps
   ```

3. **Port Conflicts**
   ```bash
   # Check port usage
   sudo netstat -tulpn | grep :80
   sudo netstat -tulpn | grep :443
   ```

### Log Locations
- **Flask App**: `docker-compose logs flask`
- **Nginx**: `logs/nginx/access.log` and `logs/nginx/error.log`
- **Certbot**: `docker-compose logs certbot`

## 📞 Support

For issues related to:
- **Docker Setup**: Check this README and logs
- **Application Logic**: Check Flask app logs
- **SSL Certificates**: Check Certbot logs
- **Network Issues**: Check Nginx logs

## 🔄 Updates

To update the application:
1. Pull latest code
2. Rebuild containers: `docker-compose build --no-cache`
3. Restart services: `docker-compose up -d`
4. Verify deployment: `docker-compose ps` 