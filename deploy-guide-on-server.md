Here’s a complete and clean `README.md` for deploying and redeploying your **Jobmato Chatbot Flask app** with **PM2**, **Gunicorn**, **NGINX**, and **SSL via Certbot**.

---

## 📘 `README.md` — Deploying Jobmato Chatbot on Ubuntu Server

### 🧱 Stack

* **Flask** + **Gunicorn**
* **PM2** for process management
* **NGINX** as reverse proxy
* **Certbot (Let's Encrypt)** for HTTPS
* **MongoDB** (already integrated)

---

## 🚀 One-Time Deployment Instructions

### ✅ 1. Clone Project & Set Up Virtual Environment

```bash
cd ~
git clone <repo-url> jobmato_chatbot_python
cd jobmato_chatbot_python

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

### ✅ 2. Run Flask App in Production via PM2

Install Node.js and PM2:

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

Start the app with Gunicorn + PM2:

```bash
cd ~/jobmato_chatbot_python
pm2 start venv/bin/gunicorn --interpreter none --name jobmato-chatbot -- -w 4 -b 127.0.0.1:8000 app:app
```

Make PM2 start on boot:

```bash
pm2 save
pm2 startup
```

---

### ✅ 3. Configure NGINX for the App

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

### ✅ 4. Secure with SSL (HTTPS)

Install Certbot:

```bash
sudo apt install certbot python3-certbot-nginx -y
```

Issue SSL certificate:

```bash
sudo certbot --nginx -d chatbot-server.jobmato.com
```

Verify:

```bash
sudo certbot renew --dry-run
```

---

## 🔁 Redeploy Instructions (After Code Updates)

```bash
cd ~/jobmato_chatbot_python
git pull origin main  # or your branch
source venv/bin/activate
pip install -r requirements.txt

# Restart PM2 process
pm2 restart jobmato-chatbot
```

---

## 🛠️ Useful Commands

| Action                | Command                       |
| --------------------- | ----------------------------- |
| View running apps     | `pm2 list`                    |
| View logs             | `pm2 logs jobmato-chatbot`    |
| Restart app           | `pm2 restart jobmato-chatbot` |
| Stop app              | `pm2 stop jobmato-chatbot`    |
| Remove app            | `pm2 delete jobmato-chatbot`  |
| Save PM2 process list | `pm2 save`                    |
| Enable on startup     | `pm2 startup`                 |

---

## 🌐 App URL

Visit: **[https://chatbot-server.jobmato.com](https://chatbot-server.jobmato.com)**

---

Would you like a `deploy.sh` bash script version of this for automation?
