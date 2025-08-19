# 🛡️ Quick Security Deployment Guide

## ⚡ Immediate Deployment (5 minutes)

### 1. Basic Secure Setup
```bash
# Set environment variables for production security
export DEBUG=false
export ENABLE_RATE_LIMITING=true
export ENABLE_HTTPS=false  # Set to true when you have SSL certs
export LOG_LEVEL=WARNING

# Generate JWT secret (IMPORTANT: Save this securely!)
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Start the secured server
python src/api/main_api_server.py
```

### 2. Development Mode with Self-Signed SSL
```bash
# Generate self-signed certificates for development
python scripts/deploy_secure.py --generate-ssl

# Enable HTTPS for development
export ENABLE_HTTPS=true
export SSL_CERT_FILE=certs/localhost.crt
export SSL_KEY_FILE=certs/localhost.key

# Start with HTTPS
python src/api/main_api_server.py
```

### 3. Production Deployment
```bash
# Use the automated deployment script
python scripts/deploy_secure.py --environment production

# Or deploy with specific configuration
export ENVIRONMENT=production
export JWT_SECRET=your-secure-jwt-secret-here
export SSL_CERT_FILE=/path/to/your/certificate.crt
export SSL_KEY_FILE=/path/to/your/private.key
export CORS_ORIGINS=https://yourdomain.com

python src/api/main_api_server.py
```

## 🔧 Security Features Enabled

### ✅ Automatic Protections (Always On)
- **SQL Injection Protection**: Parameterized queries + input validation
- **XSS Protection**: HTML escaping + content security policy
- **Rate Limiting**: 100 req/min default, endpoint-specific limits
- **Security Headers**: OWASP compliant headers
- **Input Validation**: Multi-layer validation and sanitization
- **Error Handling**: No information disclosure

### ⚙️ Configurable Features
- **Authentication**: Set `ENABLE_AUTH=true` (requires JWT_SECRET)
- **HTTPS/SSL**: Set `ENABLE_HTTPS=true` (requires certificates)
- **Rate Limiting**: Set `ENABLE_RATE_LIMITING=false` to disable
- **Debug Mode**: Set `DEBUG=true` for development (disables some security)

## 🚀 Testing Your Deployment

### 1. Quick Health Check
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy", ...}
```

### 2. Security Headers Check
```bash
curl -I http://localhost:8000/
# Should see security headers like:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# etc.
```

### 3. Rate Limiting Test
```bash
# Send multiple requests quickly
for i in {1..10}; do curl http://localhost:8000/ & done
# Should see rate limiting headers:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 99
```

### 4. Input Validation Test
```bash
# Try SQL injection (should be blocked)
curl -X POST http://localhost:8000/api/v1/characters \
  -H "Content-Type: application/json" \
  -d '{"name": "'; DROP TABLE users; --"}'
# Should return 400 Bad Request with validation error
```

## 📋 Security Checklist

### ✅ Before Production
- [ ] Set strong JWT_SECRET (32+ characters)
- [ ] Configure proper SSL certificates
- [ ] Set DEBUG=false
- [ ] Configure specific CORS_ORIGINS
- [ ] Review security configuration in `config/security.yaml`
- [ ] Test all endpoints with authentication
- [ ] Verify rate limiting is working
- [ ] Check security headers are present

### 🔍 Monitoring
- [ ] Set up log monitoring for security events
- [ ] Configure alerts for:
  - Failed authentication attempts
  - Rate limit violations
  - Input validation failures
  - SSL certificate expiration
- [ ] Regular security scans

## 🆘 Troubleshooting

### Common Issues

**1. Rate Limiting Too Strict**
```bash
# Temporarily disable for testing
export ENABLE_RATE_LIMITING=false
```

**2. SSL Certificate Issues**
```bash
# Generate new self-signed certs
python scripts/deploy_secure.py --generate-ssl
```

**3. Authentication Required Errors**
```bash
# Disable auth for testing
export ENABLE_AUTH=false
```

**4. CORS Errors in Browser**
```bash
# Allow localhost origins
export CORS_ORIGINS="http://localhost:3000,http://localhost:8080"
```

### Debug Mode
```bash
# Enable debug mode for detailed error messages
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## 📞 Need Help?

1. **Check Logs**: Look at `deployment.log` for security events
2. **Run Tests**: `python -m pytest tests/security/ -v`
3. **Security Report**: Review `SECURITY_COMPLIANCE_REPORT.md`
4. **Configuration**: Check `config/security.yaml`

## 🎯 Next Steps

1. **Deploy to staging** with production-like configuration
2. **Obtain proper SSL certificates** for your domain
3. **Set up monitoring** and alerting
4. **Run security tests** regularly
5. **Keep dependencies updated** for security patches

---

**Your Novel Engine is now secured with enterprise-grade protection! 🛡️**

For detailed security information, see `SECURITY_COMPLIANCE_REPORT.md`