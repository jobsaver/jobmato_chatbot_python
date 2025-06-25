# JobMato ChatBot Deployment Guide (Flask + Gunicorn + PM2 + NGINX + SSL)

This guide explains how to deploy and manage the **JobMato Chatbot**, a real-time AI-powered chatbot built with **Flask**, **WebSocket (SocketIO)**, and deployed using **Gunicorn**, **PM2**, **NGINX**, and **Let's Encrypt SSL**.

---

## 🧱 Stack Overview

* **Flask** backend with **Flask-SocketIO**
* **Gunicorn** WSGI server with **eventlet** for WebSocket support
* **PM2** for process management and restart
* **NGINX** as a reverse proxy
* **Certbot (Let's Encrypt)** for HTTPS
* **MongoDB** + **Redis** for persistence and session management

---

## 🚀 One-Time Setup Instructions

### ✅ 1. Clone Project & Set Up Environment

```bash
cd ~
git clone <repo-url> jobmato_chatbot_python
cd jobmato_chatbot_python

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### ✅ 2. Install PM2 & Run Flask App via Gunicorn

Install Node.js & PM2:

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

Run Gunicorn with **eventlet** for WebSocket support:

```bash
pm2 start venv/bin/gunicorn \
  --name jobmato-chatbot \
  --interpreter none \
  -- \
  -k eventlet -w 1 -b 127.0.0.1:8000 app:app
```

Enable PM2 restart on reboot:

```bash
pm2 save
pm2 startup
```

---

### ✅ 3. NGINX Reverse Proxy Setup

Install NGINX:

```bash
sudo apt install nginx -y
```

Create a config file:

```bash
sudo nano /etc/nginx/sites-available/chatbot-server.jobmato.com
```

Paste this:

```nginx
server {
    listen 80;
    server_name chatbot-server.jobmato.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/chatbot-server.jobmato.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### ✅ 4. Enable SSL via Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d chatbot-server.jobmato.com
sudo certbot renew --dry-run
```

---

## 🔁 Redeploying After Code Updates

```bash
cd ~/jobmato_chatbot_python
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
pm2 restart jobmato-chatbot
```

Or automate with:

### `redeploy.sh`

```bash
#!/bin/bash

cd ~/jobmato_chatbot_python || exit

echo "🔄 Pulling latest code..."
git pull origin main

echo "🐍 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🚀 Restarting PM2 process..."
pm2 restart jobmato-chatbot

echo "✅ Redeploy complete!"
```

Make executable:

```bash
chmod +x redeploy.sh
```

---

## 🛠️ PM2 Commands

| Task           | Command                       |
| -------------- | ----------------------------- |
| View processes | `pm2 list`                    |
| View logs      | `pm2 logs jobmato-chatbot`    |
| Restart        | `pm2 restart jobmato-chatbot` |
| Stop           | `pm2 stop jobmato-chatbot`    |
| Delete         | `pm2 delete jobmato-chatbot`  |
| Save state     | `pm2 save`                    |
| Enable on boot | `pm2 startup`                 |

---

## ✅ Production WebSocket URL Setup

Make sure your **React frontend `.env.production`** uses the correct WebSocket URL:

```env
VITE_SOCKET_URL=wss://chatbot-server.jobmato.com
```

If you use `ws://`, the browser will block it on HTTPS pages.

---

## 🌐 App Access URL

Visit: **[https://chatbot-server.jobmato.com](https://chatbot-server.jobmato.com)**

---

For support, deployment automation, or CI/CD integration, reach out or create a GitHub issue.

---

**✔️ JobMato ChatBot server now supports production-grade WebSocket communication via NGINX + SSL + PM2 + Gunicorn.**
