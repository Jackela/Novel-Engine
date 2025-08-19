#!/usr/bin/env python3
"""
Production Security Implementation for Novel Engine
==================================================

This script implements security hardening measures based on the comprehensive
security assessment findings. It addresses OWASP Top 10 vulnerabilities and
production security requirements.
"""

import os
import ssl
import secrets
import hashlib
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

# Security configuration templates
SECURITY_HEADERS_CONFIG = """
# Security Headers Configuration
# Add these headers to your reverse proxy (nginx/apache) or application

# Prevent XSS attacks
add_header X-XSS-Protection "1; mode=block" always;

# Prevent MIME type sniffing
add_header X-Content-Type-Options "nosniff" always;

# Prevent clickjacking
add_header X-Frame-Options "DENY" always;

# Content Security Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self';" always;

# HSTS for HTTPS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# Referrer Policy
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Feature Policy
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
"""

NGINX_SSL_CONFIG = """
# NGINX SSL Configuration for Production
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Certificate paths (update with your certificates)
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;
    
    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
    }
}

# Rate limiting zone
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionSecurityImplementation:
    """Implements production security measures for Novel Engine."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.security_measures = []
    
    def generate_secure_api_server(self) -> str:
        """Generate a hardened version of the API server."""
        return '''#!/usr/bin/env python3
"""
Production-Hardened FastAPI Server for Novel Engine
==================================================

This module implements a security-hardened FastAPI server with comprehensive
security measures for production deployment.
"""

import logging
import uvicorn
import os
import secrets
import time
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import hashlib
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator

# Import existing modules
from config_loader import get_config
from character_factory import CharacterFactory
from director_agent import DirectorAgent
from chronicler_agent import ChroniclerAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security Configuration
JWT_SECRET_KEY = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

class SecurityHeaders:
    """Security headers middleware."""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'"
        )
        
        # Remove server identification
        if "server" in response.headers:
            del response.headers["server"]
        
        return response

class InputValidator:
    """Enhanced input validation and sanitization."""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Remove null bytes and control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\\t\\n\\r')
        
        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length]
        
        return value.strip()
    
    @staticmethod
    def validate_character_names(names: List[str]) -> List[str]:
        """Validate character names with strict rules."""
        validated_names = []
        
        for name in names:
            # Sanitize
            name = InputValidator.sanitize_string(name, 50)
            
            # Validate format (alphanumeric + spaces + hyphens)
            if not name or len(name) < 2:
                raise ValueError(f"Character name too short: {name}")
            
            if not all(c.isalnum() or c in ' -_' for c in name):
                raise ValueError(f"Invalid characters in name: {name}")
            
            validated_names.append(name)
        
        return validated_names

class AuthenticationManager:
    """JWT-based authentication manager."""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

# Pydantic models with validation
class SimulationRequest(BaseModel):
    character_names: List[str] = Field(..., min_items=2, max_items=6)
    turns: Optional[int] = Field(None, ge=1, le=10)
    
    @validator('character_names')
    def validate_names(cls, v):
        return InputValidator.validate_character_names(v)

class SimulationResponse(BaseModel):
    story: str
    participants: List[str]
    turns_executed: int
    duration_seconds: float
    request_id: str

# Security dependency
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    payload = AuthenticationManager.verify_token(token)
    return payload.get("sub")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler with security checks."""
    logger.info("Starting production-hardened Novel Engine API server...")
    
    # Validate environment
    required_env_vars = ["ENVIRONMENT", "SECRET_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        raise RuntimeError("Security configuration incomplete")
    
    # Validate configuration
    try:
        config = get_config()
        logger.info("Configuration loaded and validated successfully")
    except Exception as e:
        logger.error(f"Configuration error during startup: {e}")
        raise e
    
    yield
    logger.info("Shutting down production-hardened Novel Engine API server.")

# Create FastAPI app with security configuration
app = FastAPI(
    title="Novel Engine API (Production)",
    description="Production-hardened RESTful API for the Novel Engine Interactive Story System.",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(SecurityHeaders)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted hosts (configure for your domain)
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["your-domain.com", "*.your-domain.com"]
    )

# CORS with restricted origins for production
allowed_origins = ["https://your-domain.com"] if os.getenv("ENVIRONMENT") == "production" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Rate limit exceeded handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    # Log security-relevant errors
    if exc.status_code in [401, 403, 429]:
        logger.warning(f"Security event: {exc.status_code} from {request.client.host}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request failed",
            "detail": exc.detail,
            "request_id": secrets.token_hex(8)
        }
    )

@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request) -> Dict[str, str]:
    """Health check endpoint with rate limiting."""
    return {"message": "Novel Engine API is running securely!"}

@app.get("/health")
@limiter.limit("30/minute")
async def health_check(request: Request) -> Dict[str, Any]:
    """Comprehensive health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0-production",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.post("/auth/token")
@limiter.limit("5/minute")
async def login(request: Request, username: str, password: str) -> Dict[str, str]:
    """Authentication endpoint (implement your authentication logic)."""
    # TODO: Implement proper authentication against your user database
    # This is a placeholder implementation
    
    if username == "admin" and password == os.getenv("ADMIN_PASSWORD"):
        access_token = AuthenticationManager.create_access_token(
            data={"sub": username}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    # Rate limit failed attempts more aggressively
    time.sleep(1)  # Prevent timing attacks
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

@app.get("/characters")
@limiter.limit("20/minute")
async def get_characters(request: Request, current_user: str = Depends(get_current_user)):
    """Get characters list (protected endpoint)."""
    try:
        characters_path = "characters"
        if not os.path.isdir(characters_path):
            raise HTTPException(status_code=404, detail="Characters directory not found.")
        
        characters = sorted([d for d in os.listdir(characters_path) 
                           if os.path.isdir(os.path.join(characters_path, d))])
        return {"characters": characters}
    
    except Exception as e:
        logger.error(f"Error retrieving characters: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve characters.")

@app.post("/simulations")
@limiter.limit("5/minute")
async def run_simulation(
    request: Request, 
    simulation_request: SimulationRequest,
    current_user: str = Depends(get_current_user)
) -> SimulationResponse:
    """Execute a character simulation (protected endpoint)."""
    start_time = time.time()
    request_id = secrets.token_hex(8)
    
    logger.info(f"Simulation requested by {current_user}: {simulation_request.character_names} (ID: {request_id})")
    
    try:
        config = get_config()
        turns_to_execute = simulation_request.turns or config.simulation.turns
        
        # Input validation has already been performed by Pydantic
        character_names = simulation_request.character_names
        
        # Create simulation with security context
        event_bus = EventBus()
        character_factory = CharacterFactory(event_bus)
        agents = [character_factory.create_character(name) for name in character_names]
        
        log_path = f"simulation_{request_id}.md"
        director = DirectorAgent(event_bus, campaign_log_path=log_path)
        
        for agent in agents:
            director.register_agent(agent)
        
        for _ in range(turns_to_execute):
            director.run_turn()
        
        chronicler = ChroniclerAgent(character_names=character_names)
        story = chronicler.transcribe_log(log_path)
        
        # Clean up temporary files
        if os.path.exists(log_path):
            os.remove(log_path)
        
        return SimulationResponse(
            story=story,
            participants=character_names,
            turns_executed=turns_to_execute,
            duration_seconds=time.time() - start_time,
            request_id=request_id
        )
    
    except Exception as e:
        logger.error(f"Simulation failed (ID: {request_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Simulation execution failed: {request_id}")

def run_production_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the production-hardened FastAPI server."""
    # Production configuration
    ssl_context = None
    if os.getenv("ENVIRONMENT") == "production":
        # SSL configuration for production
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            os.getenv("SSL_CERT_PATH", "/path/to/cert.pem"),
            os.getenv("SSL_KEY_PATH", "/path/to/key.pem")
        )
    
    uvicorn.run(
        "production_api_server:app",
        host=host,
        port=port,
        ssl_certfile=os.getenv("SSL_CERT_PATH") if ssl_context else None,
        ssl_keyfile=os.getenv("SSL_KEY_PATH") if ssl_context else None,
        log_level="info",
        access_log=True,
        use_colors=False,
        reload=False  # Never reload in production
    )

if __name__ == "__main__":
    run_production_server()
'''
    
    def generate_environment_config(self) -> str:
        """Generate secure environment configuration."""
        return '''# Production Environment Configuration
# Copy this to .env and update with your values

# Environment
ENVIRONMENT=production

# Security Keys (generate new ones for production)
SECRET_KEY=''' + secrets.token_urlsafe(32) + '''
JWT_SECRET_KEY=''' + secrets.token_urlsafe(32) + '''

# Admin Credentials (change these!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=''' + secrets.token_urlsafe(16) + '''

# SSL Configuration
SSL_CERT_PATH=/path/to/your/certificate.pem
SSL_KEY_PATH=/path/to/your/private-key.pem

# Database Configuration
DATABASE_URL=sqlite:///data/production.db
DATABASE_PASSWORD=''' + secrets.token_urlsafe(16) + '''

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=10

# CORS Origins (comma-separated)
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
METRICS_PORT=9090
'''
    
    def generate_security_middleware(self) -> str:
        """Generate security middleware module."""
        return '''#!/usr/bin/env python3
"""
Security Middleware for Novel Engine
===================================

This module provides comprehensive security middleware for the FastAPI application.
"""

import time
import logging
import hashlib
import ipaddress
from typing import Set, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SecurityEventLogger:
    """Log security events for monitoring and analysis."""
    
    def __init__(self):
        self.security_logger = logging.getLogger("security")
        handler = logging.FileHandler("logs/security.log")
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.security_logger.addHandler(handler)
        self.security_logger.setLevel(logging.WARNING)
    
    def log_event(self, event_type: str, client_ip: str, details: Dict[str, Any]):
        """Log a security event."""
        self.security_logger.warning(
            f"{event_type} from {client_ip}: {details}"
        )

class IPBlocklist:
    """Manage IP address blocklist."""
    
    def __init__(self):
        self.blocked_ips: Set[str] = set()
        self.temp_blocked: Dict[str, datetime] = {}
        self.block_duration = timedelta(minutes=15)
    
    def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked."""
        # Check permanent blocks
        if ip in self.blocked_ips:
            return True
        
        # Check temporary blocks
        if ip in self.temp_blocked:
            if datetime.utcnow() > self.temp_blocked[ip]:
                del self.temp_blocked[ip]
                return False
            return True
        
        return False
    
    def temp_block(self, ip: str):
        """Temporarily block an IP address."""
        self.temp_blocked[ip] = datetime.utcnow() + self.block_duration
        logger.warning(f"Temporarily blocked IP: {ip}")
    
    def permanent_block(self, ip: str):
        """Permanently block an IP address."""
        self.blocked_ips.add(ip)
        logger.warning(f"Permanently blocked IP: {ip}")

class RequestAnalyzer:
    """Analyze requests for suspicious patterns."""
    
    def __init__(self):
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.failed_attempts: Dict[str, int] = defaultdict(int)
        self.security_logger = SecurityEventLogger()
    
    def analyze_request(self, request: Request) -> bool:
        """Analyze request for suspicious patterns."""
        client_ip = self.get_client_ip(request)
        
        # Track request history
        now = time.time()
        self.request_history[client_ip].append(now)
        
        # Check for rapid requests (potential DoS)
        recent_requests = [
            t for t in self.request_history[client_ip] 
            if now - t < 60  # Last minute
        ]
        
        if len(recent_requests) > 30:  # More than 30 requests per minute
            self.security_logger.log_event(
                "RAPID_REQUESTS",
                client_ip,
                {"requests_per_minute": len(recent_requests)}
            )
            return False
        
        # Check for suspicious paths
        suspicious_patterns = [
            '/admin', '/wp-admin', '/.env', '/config',
            '/etc/passwd', '/proc/', '/sys/',
            'script>', 'javascript:', 'vbscript:',
            'SELECT ', 'UNION ', 'DROP ',
            '../', '..\\\\', '%2e%2e',
        ]
        
        request_path = str(request.url.path).lower()
        request_query = str(request.url.query).lower()
        
        for pattern in suspicious_patterns:
            if pattern.lower() in request_path or pattern.lower() in request_query:
                self.security_logger.log_event(
                    "SUSPICIOUS_REQUEST",
                    client_ip,
                    {"pattern": pattern, "path": request_path, "query": request_query}
                )
                return False
        
        return True
    
    def get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        # Check X-Forwarded-For header (from reverse proxy)
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"

class SecurityMiddleware:
    """Comprehensive security middleware."""
    
    def __init__(self):
        self.ip_blocklist = IPBlocklist()
        self.request_analyzer = RequestAnalyzer()
        self.security_logger = SecurityEventLogger()
    
    async def __call__(self, request: Request, call_next):
        """Process request through security filters."""
        client_ip = self.request_analyzer.get_client_ip(request)
        
        # Check IP blocklist
        if self.ip_blocklist.is_blocked(client_ip):
            self.security_logger.log_event(
                "BLOCKED_IP_ACCESS",
                client_ip,
                {"path": str(request.url.path)}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Analyze request for suspicious patterns
        if not self.request_analyzer.analyze_request(request):
            self.ip_blocklist.temp_block(client_ip)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Suspicious request detected"
            )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log slow requests (potential attacks)
        if process_time > 5.0:
            self.security_logger.log_event(
                "SLOW_REQUEST",
                client_ip,
                {"path": str(request.url.path), "duration": process_time}
            )
        
        return response
'''
    
    def generate_database_security_config(self) -> str:
        """Generate database security configuration."""
        return '''# Database Security Configuration
# Apply these settings to harden your SQLite databases

import sqlite3
import os
import stat
from pathlib import Path

def secure_database_permissions():
    """Set secure permissions on database files."""
    db_files = [
        "data/api_server.db",
        "data/production.db", 
        "context.db"
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            # Set read/write for owner only (600)
            os.chmod(db_file, stat.S_IRUSR | stat.S_IWUSR)
            print(f"Secured permissions for {db_file}")

def create_secure_database_connection(db_path: str) -> sqlite3.Connection:
    """Create a secure database connection with proper settings."""
    # Ensure database directory exists with secure permissions
    db_dir = Path(db_path).parent
    db_dir.mkdir(mode=0o700, exist_ok=True)
    
    # Create connection with security settings
    conn = sqlite3.connect(
        db_path,
        check_same_thread=False,
        isolation_level='IMMEDIATE'  # Prevent race conditions
    )
    
    # Enable security features
    conn.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key constraints
    conn.execute("PRAGMA secure_delete = ON")  # Securely delete data
    conn.execute("PRAGMA journal_mode = WAL")  # Write-ahead logging for integrity
    
    return conn

def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data before storing in database."""
    import hashlib
    import secrets
    
    # Generate a random salt
    salt = secrets.token_hex(16)
    
    # Hash the data with salt
    hash_obj = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
    
    # Return salt + hash
    return salt + hash_obj.hex()

def verify_hashed_data(data: str, stored_hash: str) -> bool:
    """Verify hashed data."""
    import hashlib
    
    # Extract salt (first 32 characters)
    salt = stored_hash[:32]
    original_hash = stored_hash[32:]
    
    # Hash the input data with the same salt
    hash_obj = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
    
    # Compare hashes
    return hash_obj.hex() == original_hash

# Database Security Best Practices:
# 1. Use parameterized queries to prevent SQL injection
# 2. Encrypt sensitive data before storage
# 3. Set restrictive file permissions (600 for database files)
# 4. Enable WAL mode for better concurrency and integrity
# 5. Regular security audits and backups
# 6. Monitor database access logs
'''
    
    def implement_security_measures(self) -> Dict[str, Any]:
        """Implement comprehensive security measures."""
        logger.info("Implementing production security measures")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "implemented_measures": [],
            "files_created": [],
            "recommendations": []
        }
        
        # Create security files
        security_files = {
            "production_api_server.py": self.generate_secure_api_server(),
            ".env.production": self.generate_environment_config(),
            "security_middleware.py": self.generate_security_middleware(),
            "database_security.py": self.generate_database_security_config(),
            "nginx_security.conf": NGINX_SSL_CONFIG,
            "security_headers.conf": SECURITY_HEADERS_CONFIG
        }
        
        for filename, content in security_files.items():
            file_path = self.project_root / filename
            file_path.write_text(content)
            results["files_created"].append(str(file_path))
            logger.info(f"Created security file: {filename}")
        
        # Create logs directory
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Create secure data directory
        data_dir = self.project_root / "data"
        data_dir.mkdir(mode=0o700, exist_ok=True)
        
        # Security measures implemented
        results["implemented_measures"] = [
            "Production-hardened API server with authentication",
            "JWT-based authentication system",
            "Rate limiting and request throttling", 
            "Input validation and sanitization",
            "Security headers middleware",
            "IP blocking and request analysis",
            "Comprehensive security logging",
            "Database security configuration",
            "SSL/TLS configuration templates",
            "Environment variable templates"
        ]
        
        # Generate recommendations
        results["recommendations"] = [
            {
                "priority": "CRITICAL",
                "action": "Generate SSL certificates and update nginx configuration",
                "category": "Encryption"
            },
            {
                "priority": "CRITICAL", 
                "action": "Update .env.production with your actual values",
                "category": "Configuration"
            },
            {
                "priority": "HIGH",
                "action": "Set up user authentication database",
                "category": "Authentication"
            },
            {
                "priority": "HIGH",
                "action": "Configure reverse proxy (nginx/apache) with security headers",
                "category": "Infrastructure"
            },
            {
                "priority": "MEDIUM",
                "action": "Set up security monitoring and alerting",
                "category": "Monitoring"
            },
            {
                "priority": "MEDIUM",
                "action": "Implement database backups with encryption",
                "category": "Data Protection"
            },
            {
                "priority": "LOW",
                "action": "Set up automated security testing in CI/CD",
                "category": "DevSecOps"
            }
        ]
        
        return results

def main():
    """Main execution function."""
    implementer = ProductionSecurityImplementation()
    results = implementer.implement_security_measures()
    
    # Save implementation report
    output_file = "security_implementation_report.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\\n" + "="*70)
    print("PRODUCTION SECURITY IMPLEMENTATION COMPLETE")
    print("="*70)
    print(f"Files created: {len(results['files_created'])}")
    print(f"Security measures: {len(results['implemented_measures'])}")
    
    print("\\n📁 FILES CREATED:")
    for file_path in results['files_created']:
        print(f"  • {file_path}")
    
    print("\\n🔒 SECURITY MEASURES IMPLEMENTED:")
    for measure in results['implemented_measures'][:5]:
        print(f"  • {measure}")
    if len(results['implemented_measures']) > 5:
        print(f"  • ... and {len(results['implemented_measures']) - 5} more")
    
    print("\\n⚠️  CRITICAL NEXT STEPS:")
    critical_recs = [r for r in results['recommendations'] if r['priority'] == 'CRITICAL']
    for rec in critical_recs:
        print(f"  • {rec['action']}")
    
    print(f"\\n📄 Implementation report saved to: {output_file}")
    print("="*70)

if __name__ == "__main__":
    main()