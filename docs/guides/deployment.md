# Deployment Guide

This guide covers deploying JAP Dashboard to production environments.

## 🏗️ Production Deployment

### Prerequisites

- **Server**: Linux server (Ubuntu 20.04+ recommended)
- **Python**: 3.8+ installed
- **Web Server**: Nginx (recommended) or Apache
- **Process Manager**: systemd, PM2, or supervisor
- **SSL Certificate**: For HTTPS (Let's Encrypt recommended)
- **Firewall**: UFW or iptables configured

### 1. Server Setup

#### Update System
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv nginx -y
```

#### Create Application User
```bash
sudo adduser --system --group japdash
sudo mkdir -p /var/www/japdash
sudo chown japdash:japdash /var/www/japdash
```

### 2. Application Deployment

#### Clone Repository
```bash
sudo -u japdash git clone <repository-url> /var/www/japdash
cd /var/www/japdash
```

#### Setup Python Environment
```bash
sudo -u japdash python3 -m venv venv
sudo -u japdash /var/www/japdash/venv/bin/pip install -r requirements.txt
```

#### Configure Environment
```bash
sudo -u japdash cp .env.example .env
sudo -u japdash nano .env
```

**Production .env Configuration**:
```env
# API Keys
JAP_API_KEY=your_production_jap_key
RSS_API_KEY=your_production_rss_key
RSS_API_SECRET=your_production_rss_secret
LLM_FLOWISE_URL=https://your-flowise-instance.com

# Database Configuration
DATABASE_PATH=/var/www/japdash/social_media_accounts.db
JAP_CACHE_DB_PATH=/var/www/japdash/jap_cache.db

# Flask Configuration (Production)
FLASK_HOST=127.0.0.1
FLASK_PORT=5079
FLASK_DEBUG=False
SECRET_KEY=your-secure-secret-key-here

# Authentication (CHANGE THESE!)
ADMIN_USERNAME=your_admin_user
ADMIN_PASSWORD_HASH=your_bcrypt_hash_here

# Application Settings
TIME_ZONE=Your/Timezone
RSS_POLLING_INTERVAL=60
SESSION_TIMEOUT=30
```

**Generate Secure Credentials**:
```bash
# Generate secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate password hash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your_secure_password'))"
```

### 3. Database Setup

#### Set Database Permissions
```bash
sudo chown japdash:japdash /var/www/japdash/*.db
sudo chmod 644 /var/www/japdash/*.db
```

#### Test Application
```bash
sudo -u japdash /var/www/japdash/venv/bin/python /var/www/japdash/app.py
# Should start successfully and show migration messages
```

### 4. Process Management (systemd)

#### Create Service File
```bash
sudo nano /etc/systemd/system/japdash.service
```

**Service Configuration**:
```ini
[Unit]
Description=JAP Dashboard
After=network.target

[Service]
Type=simple
User=japdash
Group=japdash
WorkingDirectory=/var/www/japdash
Environment=PATH=/var/www/japdash/venv/bin
ExecStart=/var/www/japdash/venv/bin/python app.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable japdash
sudo systemctl start japdash
sudo systemctl status japdash
```

### 5. Web Server Configuration (Nginx)

#### Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/japdash
```

**Nginx Configuration**:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:MozTLS:10m;
    ssl_session_tickets off;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    # Application Proxy
    location / {
        proxy_pass http://127.0.0.1:5079;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
    
    # Static Files (Optional)
    location /static {
        alias /var/www/japdash/static;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
```

#### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/japdash /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get Certificate
sudo certbot --nginx -d your-domain.com

# Test Auto-renewal
sudo certbot renew --dry-run
```

### 7. Firewall Configuration

```bash
# Allow HTTP, HTTPS, and SSH
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp  
sudo ufw allow 443/tcp
sudo ufw enable

# Block direct access to Flask port
sudo ufw deny 5079
```

### 8. Monitoring and Logging

#### Log File Locations
```bash
# Application logs
tail -f /var/www/japdash/console.log

# System service logs
sudo journalctl -u japdash -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

#### Log Rotation
```bash
sudo nano /etc/logrotate.d/japdash
```

```
/var/www/japdash/console.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 644 japdash japdash
    postrotate
        sudo systemctl reload japdash
    endscript
}
```

## 🔄 Database Migration Deployment

### Automatic Migration (Recommended)
The application handles migrations automatically on startup:

```bash
# Simply restart the service
sudo systemctl restart japdash

# Check logs for migration status
sudo journalctl -u japdash | grep migration
```

### Manual Migration (If Needed)
```bash
# Backup database first
sudo -u japdash cp /var/www/japdash/social_media_accounts.db /var/www/japdash/backup_$(date +%Y%m%d_%H%M%S).db

# Run specific migration if needed
sudo -u japdash sqlite3 /var/www/japdash/social_media_accounts.db < migrations/v2_add_tags.sql
```

## 🔄 Updates and Maintenance

### Application Updates
```bash
# Navigate to application directory
cd /var/www/japdash

# Stop service
sudo systemctl stop japdash

# Backup database
sudo -u japdash cp social_media_accounts.db backup_$(date +%Y%m%d_%H%M%S).db

# Pull updates
sudo -u japdash git pull origin master

# Update dependencies if needed
sudo -u japdash /var/www/japdash/venv/bin/pip install -r requirements.txt

# Start service (migrations run automatically)
sudo systemctl start japdash

# Check status
sudo systemctl status japdash
```

### Rollback Procedure
```bash
# Stop service
sudo systemctl stop japdash

# Restore database backup
sudo -u japdash cp backup_YYYYMMDD_HHMMSS.db social_media_accounts.db

# Revert to previous commit
sudo -u japdash git checkout <previous-commit-hash>

# Start service
sudo systemctl start japdash
```

## 📊 Performance Optimization

### Database Optimization
```bash
# Regular database maintenance
sudo -u japdash sqlite3 /var/www/japdash/social_media_accounts.db "VACUUM;"
sudo -u japdash sqlite3 /var/www/japdash/social_media_accounts.db "ANALYZE;"
```

### System Resource Monitoring
```bash
# Monitor system resources
htop
df -h
free -h

# Monitor application process
sudo systemctl status japdash
ps aux | grep python
```

### Nginx Performance Tuning
Add to nginx configuration:
```nginx
# Inside server block
client_max_body_size 10M;
keepalive_timeout 65;
gzip on;
gzip_types text/plain application/json application/javascript text/css;
```

## 🛡️ Security Considerations

### File Permissions
```bash
# Set proper permissions
sudo chown -R japdash:japdash /var/www/japdash
sudo chmod -R 644 /var/www/japdash
sudo chmod +x /var/www/japdash/venv/bin/*
sudo chmod 600 /var/www/japdash/.env
```

### Regular Security Updates
```bash
# Weekly security updates
sudo apt update && sudo apt upgrade -y

# Monitor for security advisories
sudo apt install unattended-upgrades
```

### Database Security
- Regular backups to secure location
- Limit database file permissions
- Consider encryption at rest for sensitive data

### API Key Security
- Use environment variables, never commit to code
- Regular API key rotation
- Monitor API usage for anomalies

## 📈 Scaling Considerations

### Current Limitations
- Single instance application
- SQLite database (limited concurrent access)
- File-based session storage

### Scaling Options
- **Database**: Migrate to PostgreSQL for better concurrency
- **Caching**: Add Redis for session and data caching
- **Load Balancing**: Multiple application instances behind load balancer
- **Container Deployment**: Docker/Kubernetes for easier scaling

### Migration to PostgreSQL (Future)
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres createdb japdash
sudo -u postgres createuser -P japdash_user
```

## 🚨 Troubleshooting

### Common Issues

**Service Won't Start**:
```bash
# Check logs
sudo journalctl -u japdash -n 50

# Check permissions
ls -la /var/www/japdash/

# Test manually
sudo -u japdash /var/www/japdash/venv/bin/python /var/www/japdash/app.py
```

**Database Issues**:
```bash
# Check database integrity
sudo -u japdash sqlite3 /var/www/japdash/social_media_accounts.db "PRAGMA integrity_check;"

# Reset database (CAUTION)
sudo systemctl stop japdash
sudo -u japdash rm /var/www/japdash/social_media_accounts.db
sudo systemctl start japdash  # Will recreate with migrations
```

**Nginx Issues**:
```bash
# Test configuration
sudo nginx -t

# Check logs
tail -f /var/log/nginx/error.log
```

This deployment guide provides a production-ready setup with proper security, monitoring, and maintenance procedures.