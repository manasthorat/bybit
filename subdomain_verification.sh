#!/bin/bash

# Subdomain Verification Script for trading.theinvestmaster.in
# Run this on your EC2 instance to verify setup

echo "🔍 Trading System Subdomain Verification"
echo "========================================"
echo ""

SUBDOMAIN="trading.theinvestmaster.in"
ELASTIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# 1. Check DNS Resolution
echo "1. Checking DNS Resolution..."
DNS_IP=$(dig +short $SUBDOMAIN | tail -n1)
if [ "$DNS_IP" = "$ELASTIC_IP" ]; then
    print_status 0 "DNS is correctly pointing to $ELASTIC_IP"
else
    print_status 1 "DNS mismatch. Expected: $ELASTIC_IP, Got: $DNS_IP"
    echo -e "${YELLOW}   → Please check your GoDaddy DNS settings${NC}"
fi
echo ""

# 2. Check Nginx Configuration
echo "2. Checking Nginx Configuration..."
if sudo nginx -t 2>/dev/null; then
    print_status 0 "Nginx configuration is valid"
else
    print_status 1 "Nginx configuration has errors"
    sudo nginx -t
fi

# Check if subdomain is in Nginx config
if sudo grep -q "$SUBDOMAIN" /etc/nginx/sites-available/trading-system 2>/dev/null; then
    print_status 0 "Subdomain found in Nginx config"
else
    print_status 1 "Subdomain not found in Nginx config"
    echo -e "${YELLOW}   → Update server_name in /etc/nginx/sites-available/trading-system${NC}"
fi
echo ""

# 3. Check Application Status
echo "3. Checking Application Status..."
if sudo supervisorctl status trading-system | grep -q RUNNING; then
    print_status 0 "Trading system is running"
else
    print_status 1 "Trading system is not running"
    echo -e "${YELLOW}   → Run: sudo supervisorctl start trading-system${NC}"
fi

# Check if app is responding
if curl -s http://localhost:8000/api/account/status > /dev/null; then
    print_status 0 "Application is responding on localhost"
else
    print_status 1 "Application not responding on localhost"
fi
echo ""

# 4. Check HTTP Access
echo "4. Checking HTTP Access..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$SUBDOMAIN 2>/dev/null)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    print_status 0 "HTTP access working (Status: $HTTP_CODE)"
else
    print_status 1 "HTTP access failed (Status: $HTTP_CODE)"
    if [ -z "$DNS_IP" ]; then
        echo -e "${YELLOW}   → DNS might not have propagated yet${NC}"
    fi
fi
echo ""

# 5. Check HTTPS/SSL
echo "5. Checking HTTPS/SSL..."
if [ -f "/etc/letsencrypt/live/$SUBDOMAIN/fullchain.pem" ]; then
    print_status 0 "SSL certificate exists"
    
    # Check certificate validity
    CERT_EXPIRY=$(sudo openssl x509 -enddate -noout -in /etc/letsencrypt/live/$SUBDOMAIN/fullchain.pem | cut -d= -f2)
    echo "   Certificate expires: $CERT_EXPIRY"
    
    # Test HTTPS
    HTTPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$SUBDOMAIN 2>/dev/null)
    if [ "$HTTPS_CODE" = "200" ]; then
        print_status 0 "HTTPS access working"
    else
        print_status 1 "HTTPS access failed (Status: $HTTPS_CODE)"
    fi
else
    print_status 1 "SSL certificate not found"
    echo -e "${YELLOW}   → Run: sudo certbot --nginx -d $SUBDOMAIN${NC}"
fi
echo ""

# 6. Check API Endpoints
echo "6. Checking API Endpoints..."
# Check account status endpoint
API_RESPONSE=$(curl -s https://$SUBDOMAIN/api/account/status 2>/dev/null)
if echo "$API_RESPONSE" | grep -q "connected"; then
    print_status 0 "API endpoint responding correctly"
else
    print_status 1 "API endpoint not responding correctly"
fi

# Check webhook endpoint (should return 403 without token)
WEBHOOK_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$SUBDOMAIN/api/webhook 2>/dev/null)
if [ "$WEBHOOK_CODE" = "403" ] || [ "$WEBHOOK_CODE" = "422" ]; then
    print_status 0 "Webhook endpoint is protected (Status: $WEBHOOK_CODE)"
else
    print_status 1 "Webhook endpoint unexpected response (Status: $WEBHOOK_CODE)"
fi
echo ""

# 7. Check Environment
echo "7. Checking Environment Configuration..."
if [ -f "/var/www/trading-system/backend/.env" ]; then
    print_status 0 ".env file exists"
    
    # Check for required variables (without showing values)
    required_vars=("BYBIT_API_KEY" "BYBIT_API_SECRET" "WEBHOOK_SECRET")
    for var in "${required_vars[@]}"; do
        if grep -q "^$var=" /var/www/trading-system/backend/.env; then
            print_status 0 "$var is set"
        else
            print_status 1 "$var is missing"
        fi
    done
else
    print_status 1 ".env file not found"
    echo -e "${YELLOW}   → Create .env file in /var/www/trading-system/backend/${NC}"
fi
echo ""

# Summary
echo "========================================"
echo "📊 Summary"
echo "========================================"
echo "Subdomain: $SUBDOMAIN"
echo "Server IP: $ELASTIC_IP"
echo "DNS IP: ${DNS_IP:-Not resolved}"
echo ""

# Provide webhook URL if everything is working
if [ "$HTTPS_CODE" = "200" ] && [ -f "/var/www/trading-system/backend/.env" ]; then
    WEBHOOK_SECRET=$(grep "WEBHOOK_SECRET=" /var/www/trading-system/backend/.env | cut -d= -f2)
    if [ ! -z "$WEBHOOK_SECRET" ]; then
        echo -e "${GREEN}✅ Your TradingView webhook URL:${NC}"
        echo "https://$SUBDOMAIN/api/webhook?token=<your_webhook_secret>"
        echo ""
        echo "Test with:"
        echo "curl -X POST \"https://$SUBDOMAIN/api/webhook?token=<your_webhook_secret>\" \\"
        echo "  -H \"Content-Type: application/json\" \\"
        echo "  -d '{\"action\":\"buy\",\"symbol\":\"BTCUSDT\",\"quantity\":0.001}'"
    fi
else
    echo -e "${YELLOW}⚠️  Complete the setup before using webhooks${NC}"
fi

echo ""
echo "For detailed logs:"
echo "- App logs: sudo tail -f /var/log/trading-system.log"
echo "- Nginx logs: sudo tail -f /var/log/nginx/error.log"
echo "- Access logs: sudo tail -f /var/log/nginx/access.log"