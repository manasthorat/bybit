# AWS Deployment Guide for Trading System

## Prerequisites
- AWS Account
- GoDaddy domain
- Your trading system code on GitHub or ready to transfer
- Bybit API credentials
- Basic knowledge of Linux commands

## Step 1: Launch EC2 Instance

### 1.1 Create EC2 Instance
1. Go to AWS Console → EC2 → Launch Instance
2. Choose:
   - **Name**: `trading-system-server`
   - **OS**: Ubuntu Server 22.04 LTS
   - **Instance Type**: t3.small (or t3.micro for testing)
   - **Key Pair**: Create new or use existing

### 1.2 Configure Storage
- **Storage**: 20-30 GB gp3 (SSD)

### 1.3 Network Settings
- **VPC**: Default VPC
- **Subnet**: Default
- **Auto-assign Public IP**: Enable
- **Create Security Group** with rules:
  - SSH (22) - Your IP
  - HTTP (80) - Anywhere
  - HTTPS (443) - Anywhere
  - Custom TCP (8000) - Anywhere (for testing, remove later)

### 1.4 Launch Instance
Click "Launch Instance" and wait for it to start.

## Step 2: Configure Security Group (Important!)

Edit your security group to ensure these inbound rules:

```
Type        Port    Source          Description
SSH         22      Your IP         Admin access
HTTP        80      0.0.0.0/0      Web traffic
HTTPS       443     0.0.0.0/0      Secure web traffic
Custom TCP  8000    0.0.0.0/0      FastAPI (temporary)
```

## Step 3: Connect to EC2 Instance

```bash
# Connect via SSH
ssh -i your-key.pem ubuntu@your-ec2-public-ip

# Update system
sudo apt update && sudo apt upgrade -y
```

## Step 4: Install Required Software

```bash
# Install Python 3.10+ and pip
sudo apt install python3.10 python3.10-venv python3-pip -y

# Install Node.js (for any JS tools if needed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install Nginx
sudo apt install nginx -y

# Install Git
sudo apt install git -y

# Install SQLite (if using SQLite)
sudo apt install sqlite3 -y

# Install certbot for SSL
sudo apt install certbot python3-certbot-nginx -y

# Install supervisor for process management
sudo apt install supervisor -y
```

## Step 5: Clone and Setup Your Application

```bash
# Create app directory
sudo mkdir -p /var/www/trading-system
sudo chown ubuntu:ubuntu /var/www/trading-system
cd /var/www/trading-system

# Clone your repository (or upload files)
git clone https://github.com/yourusername/your-trading-system.git .
# OR use SCP to upload files:
# scp -i your-key.pem -r local-folder/* ubuntu@your-ec2-ip:/var/www/trading-system/

# Create Python virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install fastapi uvicorn sqlalchemy aiosqlite pybit python-dotenv

# Create .env file
nano .env
```

Add to .env file:
```
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
BYBIT_TESTNET=False
DATABASE_URL=sqlite:///./trading_system.db
WEBHOOK_SECRET=your_webhook_secret
HOST=0.0.0.0
PORT=8000
```

## Step 6: Configure Nginx as Reverse Proxy

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/trading-system
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Important for webhooks
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Specific handling for webhook endpoint
    location /api/webhook {
        proxy_pass http://localhost:8000/api/webhook;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Important for webhook bodies
        proxy_buffering off;
        proxy_request_buffering off;
        client_max_body_size 10M;
    }
}
```

Enable the site:
```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/trading-system /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

## Step 7: Configure Domain (GoDaddy)

### 7.1 Get EC2 Elastic IP
1. AWS Console → EC2 → Elastic IPs
2. Allocate Elastic IP
3. Associate with your EC2 instance

### 7.2 Configure GoDaddy DNS
1. Log in to GoDaddy
2. Go to DNS Management for your domain
3. Update/Add records:

```
Type    Name    Value               TTL
A       @       your-elastic-ip     600
A       www     your-elastic-ip     600
```

Wait 5-30 minutes for DNS propagation.

## Step 8: Setup SSL Certificate

```bash
# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Follow prompts:
# - Enter email
# - Agree to terms
# - Choose redirect HTTP to HTTPS (recommended)
```

## Step 9: Setup Process Management with Supervisor

```bash
# Create supervisor configuration
sudo nano /etc/supervisor/conf.d/trading-system.conf
```

Add:
```ini
[program:trading-system]
command=/var/www/trading-system/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
directory=/var/www/trading-system/backend
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/trading-system.log
environment=PATH="/var/www/trading-system/venv/bin"
```

Start supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start trading-system
```

## Step 10: Configure TradingView Webhook

In TradingView Alert settings, set webhook URL to:
```
https://yourdomain.com/api/webhook?token=your_webhook_secret
```

## Step 11: Test Your Deployment

### 11.1 Check Application Status
```bash
# Check if app is running
sudo supervisorctl status trading-system

# Check logs
tail -f /var/log/trading-system.log

# Check Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 11.2 Test Endpoints
```bash
# Test from server
curl http://localhost:8000/api/account/status

# Test from outside
curl https://yourdomain.com/api/account/status
```

### 11.3 Test Webhook
Use curl to simulate webhook:
```bash
curl -X POST https://yourdomain.com/api/webhook?token=your_webhook_secret \
  -H "Content-Type: application/json" \
  -d '{"action":"buy","symbol":"BTCUSDT","quantity":0.001}'
```

## Step 12: Security Hardening

### 12.1 Setup UFW Firewall
```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 12.2 Remove Unnecessary Ports
Go back to AWS Security Group and remove port 8000 rule.

### 12.3 Setup Fail2ban
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Step 13: Setup Monitoring and Backups

### 13.1 CloudWatch Monitoring
1. Install CloudWatch agent:
```bash
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
```

### 13.2 Database Backups
Create backup script:
```bash
nano /home/ubuntu/backup.sh
```

Add:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp /var/www/trading-system/backend/trading_system.db /home/ubuntu/backups/trading_system_$DATE.db
# Keep only last 7 days
find /home/ubuntu/backups -name "trading_system_*.db" -mtime +7 -delete
```

Make executable and schedule:
```bash
chmod +x /home/ubuntu/backup.sh
mkdir -p /home/ubuntu/backups

# Add to crontab
crontab -e
# Add: 0 */6 * * * /home/ubuntu/backup.sh
```

## Step 14: Auto-restart on Reboot

```bash
# Enable services to start on boot
sudo systemctl enable nginx
sudo systemctl enable supervisor

# Create systemd service (alternative to supervisor)
sudo nano /etc/systemd/system/trading-system.service
```

Add:
```ini
[Unit]
Description=Trading System FastAPI
After=network.target

[Service]
Type=exec
User=ubuntu
WorkingDirectory=/var/www/trading-system/backend
Environment="PATH=/var/www/trading-system/venv/bin"
ExecStart=/var/www/trading-system/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Common Issues:

1. **502 Bad Gateway**: App not running
   - Check: `sudo supervisorctl status`
   - Check logs: `tail -f /var/log/trading-system.log`

2. **Webhook not receiving**: 
   - Check security group allows HTTPS
   - Verify webhook secret in URL
   - Check Nginx logs

3. **Bybit connection issues**:
   - Verify API credentials in .env
   - Check if EC2 can reach Bybit servers
   - Test: `curl https://api.bybit.com/v2/public/time`

4. **Database errors**:
   - Check permissions: `ls -la trading_system.db`
   - Initialize DB: `python -c "from database import init_db; import asyncio; asyncio.run(init_db())"`

## Maintenance Commands

```bash
# Restart application
sudo supervisorctl restart trading-system

# View logs
tail -f /var/log/trading-system.log

# Update code
cd /var/www/trading-system
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart trading-system

# Renew SSL certificate (auto-renews, but manual command)
sudo certbot renew --dry-run
```

## Cost Optimization

- Use t3.micro for testing (free tier eligible)
- Use t3.small for production (~$15/month)
- Consider Reserved Instances for long-term savings
- Monitor CloudWatch for usage patterns

## Final Notes

1. **Keep your webhook secret secure** - it's your authentication
2. **Monitor your logs regularly** for any issues
3. **Set up CloudWatch alarms** for high CPU/memory usage
4. **Regular backups** of your database
5. **Keep system updated**: `sudo apt update && sudo apt upgrade`

Your trading system should now be live at https://yourdomain.com!