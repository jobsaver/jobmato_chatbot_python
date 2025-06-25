# 🚀 Jobmato Chatbot Deployment Guide

A comprehensive guide for deploying the Jobmato Chatbot Flask application on Ubuntu Server with production-grade infrastructure.

## 📋 Table of Contents

- [System Requirements](#system-requirements)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Initial Deployment](#initial-deployment)
- [SSL Configuration](#ssl-configuration)
- [Redeployment](#redeployment)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

---

## 🖥️ System Requirements

- **OS**: Ubuntu 20.04 LTS or higher
- **RAM**: Minimum 2GB (4GB recommended)
- **Storage**: 20GB available space
- **Domain**: A registered domain name pointing to your server
- **User**: Sudo privileges

---

## 🧱 Technology Stack

| Component | Purpose | Version |
|-----------|---------|---------|
| **Flask** | Web framework | Latest stable |
| **Gunicorn** | WSGI server | Latest stable |
| **PM2** | Process manager | Latest stable |
| **NGINX** | Reverse proxy | Latest stable |
| **Certbot** | SSL certificates | Latest stable |
| **MongoDB** | Database | Latest stable |
| **Python** | Runtime | 3.8+ |

---

## ✅ Prerequisites

### 1. Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Install Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv

# Install build essentials (for some Python packages)
sudo apt install -y build-essential python3-dev
```

### 2. Domain Configuration

Ensure your domain points to your server's IP address:

```bash
# Check your server's public IP
curl ifconfig.me

# Verify domain resolution
nslookup your-domain.com
```

---

## 🚀 Initial Deployment

### Step 1: Clone and Setup Project

```bash
# Navigate to home directory
cd ~

# Clone the repository
git clone https://github.com/your-username/jobmato_chatbot_python.git
cd jobmato_chatbot_python

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create environment file
cp env.example .env
nano .env  # Configure your environment variables
```

### Step 2: Install and Configure PM2

```bash
# Install Node.js (required for PM2)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2 globally
sudo npm install -g pm2

# Verify installation
pm2 --version
node --version
```

### Step 3: Start Application with PM2

```bash
# Navigate to project directory
cd ~/jobmato_chatbot_python

# Start the application with Gunicorn via PM2
pm2 start venv/bin/gunicorn \
  --interpreter none \
  --name jobmato-chatbot \
  -- -w 4 -b 127.0.0.1:8000 \
  --timeout 120 \
  --keep-alive 2 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  app:app

# Save PM2 configuration
pm2 save

# Setup PM2 to start on system boot
pm2 startup
# Follow the instructions provided by the above command
```

### Step 4: Install and Configure NGINX

```bash
# Install NGINX
sudo apt install nginx -y

# Create NGINX configuration
sudo nano /etc/nginx/sites-available/jobmato-chatbot
```

Add the following configuration:

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Client max body size
    client_max_body_size 10M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript;
    
    location / {
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        # Proxy settings
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Static files (if any)
    location /static/ {
        alias /home/ubuntu/jobmato_chatbot_python/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/jobmato-chatbot /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test NGINX configuration
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx

# Enable NGINX to start on boot
sudo systemctl enable nginx
```

---

## 🔒 SSL Configuration

### Step 1: Install Certbot

```bash
# Install Certbot and NGINX plugin
sudo apt install certbot python3-certbot-nginx -y

# Verify installation
certbot --version
```

### Step 2: Obtain SSL Certificate

```bash
# Obtain certificate (interactive)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Or non-interactive (for automation)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com --non-interactive --agree-tos --email your-email@domain.com
```

### Step 3: Verify Auto-Renewal

```bash
# Test renewal process
sudo certbot renew --dry-run

# Check renewal timer
sudo systemctl status certbot.timer
```

---

## 🔄 Redeployment

### Quick Redeploy Script

Create a redeploy script for easy updates:

```bash
# Create redeploy script
nano ~/redeploy.sh
```

Add the following content:

```bash
#!/bin/bash

echo "🚀 Starting Jobmato Chatbot redeployment..."

# Navigate to project directory
cd ~/jobmato_chatbot_python

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies
echo "📦 Updating dependencies..."
pip install -r requirements.txt

# Restart application
echo "🔄 Restarting application..."
pm2 restart jobmato-chatbot

# Check status
echo "✅ Checking application status..."
pm2 status jobmato-chatbot

echo "🎉 Redeployment completed!"
```

Make it executable:

```bash
chmod +x ~/redeploy.sh
```

### Manual Redeployment

```bash
# Navigate to project
cd ~/jobmato_chatbot_python

# Pull latest changes
git pull origin main

# Activate environment and update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart application
pm2 restart jobmato-chatbot

# Verify status
pm2 status jobmato-chatbot
```

---

## 📊 Monitoring & Maintenance

### PM2 Commands

| Command | Description |
|---------|-------------|
| `pm2 list` | View all processes |
| `pm2 status jobmato-chatbot` | Check specific app status |
| `pm2 logs jobmato-chatbot` | View application logs |
| `pm2 logs jobmato-chatbot --lines 100` | View last 100 log lines |
| `pm2 monit` | Open monitoring dashboard |
| `pm2 restart jobmato-chatbot` | Restart application |
| `pm2 stop jobmato-chatbot` | Stop application |
| `pm2 delete jobmato-chatbot` | Remove from PM2 |
| `pm2 save` | Save current process list |
| `pm2 startup` | Configure startup script |

### NGINX Commands

| Command | Description |
|---------|-------------|
| `sudo nginx -t` | Test configuration |
| `sudo systemctl reload nginx` | Reload configuration |
| `sudo systemctl restart nginx` | Restart NGINX |
| `sudo systemctl status nginx` | Check NGINX status |
| `sudo tail -f /var/log/nginx/error.log` | Monitor error logs |
| `sudo tail -f /var/log/nginx/access.log` | Monitor access logs |

### System Monitoring

```bash
# Check system resources
htop

# Check disk usage
df -h

# Check memory usage
free -h

# Check running processes
ps aux | grep -E "(gunicorn|nginx|pm2)"

# Monitor application logs
pm2 logs jobmato-chatbot --lines 50 -f
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Application Not Starting

```bash
# Check PM2 logs
pm2 logs jobmato-chatbot

# Check if port is in use
sudo netstat -tlnp | grep :8000

# Test application manually
cd ~/jobmato_chatbot_python
source venv/bin/activate
python app.py
```

#### 2. NGINX Configuration Errors

```bash
# Test NGINX configuration
sudo nginx -t

# Check NGINX error logs
sudo tail -f /var/log/nginx/error.log

# Check NGINX status
sudo systemctl status nginx
```

#### 3. SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -text -noout | grep "Not After"
```

#### 4. Permission Issues

```bash
# Fix file permissions
sudo chown -R $USER:$USER ~/jobmato_chatbot_python
chmod -R 755 ~/jobmato_chatbot_python

# Fix NGINX permissions
sudo chown -R www-data:www-data /var/www/html
```

### Performance Optimization

#### 1. Gunicorn Optimization

```bash
# Optimize Gunicorn settings
pm2 restart jobmato-chatbot -- -w 4 -b 127.0.0.1:8000 --timeout 120 --keep-alive 2 --max-requests 1000 --max-requests-jitter 100 --worker-class gevent
```

#### 2. NGINX Optimization

Add to NGINX configuration:

```nginx
# Enable gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

# Enable caching
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

## 🔐 Security Considerations

### 1. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Check status
sudo ufw status
```

### 2. Regular Updates

```bash
# Create update script
nano ~/update-system.sh
```

Add content:

```bash
#!/bin/bash
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
sudo apt autoclean
```

### 3. Backup Strategy

```bash
# Create backup script
nano ~/backup.sh
```

Add content:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ubuntu/backups"

mkdir -p $BACKUP_DIR

# Backup application
tar -czf $BACKUP_DIR/jobmato-chatbot_$DATE.tar.gz ~/jobmato_chatbot_python

# Backup NGINX configuration
sudo tar -czf $BACKUP_DIR/nginx-config_$DATE.tar.gz /etc/nginx

# Backup SSL certificates
sudo tar -czf $BACKUP_DIR/ssl-certs_$DATE.tar.gz /etc/letsencrypt

echo "Backup completed: $BACKUP_DIR"
```

---

## 📞 Support

For issues and support:

1. Check the troubleshooting section above
2. Review application logs: `pm2 logs jobmato-chatbot`
3. Check system logs: `sudo journalctl -u nginx`
4. Verify configuration files
5. Test connectivity: `curl -I http://localhost:8000`

---

## 🎯 Quick Reference

### URLs
- **Production**: https://your-domain.com
- **Health Check**: https://your-domain.com/health

### Key Files
- **Application**: `~/jobmato_chatbot_python/app.py`
- **NGINX Config**: `/etc/nginx/sites-available/jobmato-chatbot`
- **PM2 Config**: `~/.pm2/ecosystem.config.js`
- **Environment**: `~/jobmato_chatbot_python/.env`

### Quick Commands
```bash
# Redeploy
~/redeploy.sh

# Check status
pm2 status jobmato-chatbot

# View logs
pm2 logs jobmato-chatbot

# Restart everything
pm2 restart jobmato-chatbot && sudo systemctl reload nginx
```

---

*Last updated: $(date)*
