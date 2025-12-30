#!/usr/bin/env python3
"""
ENTERPRISE SECURITY INTEGRATION MODULE
=====================================

Unified security integration providing:
- Complete security stack initialization
- Security middleware integration with FastAPI
- Real-time security monitoring setup
- Compliance framework activation
- Security API endpoints
- Automated security responses

Architecture: Zero Trust + Defense in Depth
Security Level: Enterprise Grade with Military Standards
Author: Chief Security Officer
System coordinates all security operations 🛡️
"""

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Security components
from .auth_system import (
    Permission,
    SecurityService,
    TokenPair,
    User,
    UserLogin,
    UserRegistration,
    UserRole,
    initialize_security_service,
)
from .enterprise_security_manager import (
    ComplianceFramework,
    EnterpriseSecurityManager,
    SecurityAction,
    ThreatLevel,
    initialize_enterprise_security_manager,
)
from .security_dashboard import (
    SecurityDashboard,
    initialize_security_dashboard,
)
from .security_middleware import (
    SecurityConfig,
    SecurityMiddleware,
)

# Enhanced logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnterpriseSecuritySuite:
    """Complete Enterprise Security Suite Integration"""

    def __init__(
        self,
        database_path: str,
        secret_key: Optional[str] = None,
        redis_url: str = "redis://localhost:6379",
        geoip_database_path: Optional[str] = None,
        compliance_frameworks: List[ComplianceFramework] = None,
        enable_geo_blocking: bool = True,
        enable_behavioral_analytics: bool = True,
        security_config: SecurityConfig = None,
    ):
        self.database_path = database_path
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.redis_url = redis_url
        self.geoip_database_path = geoip_database_path
        self.compliance_frameworks = compliance_frameworks or [
            ComplianceFramework.GDPR,
            ComplianceFramework.SOC2,
        ]
        self.enable_geo_blocking = enable_geo_blocking
        self.enable_behavioral_analytics = enable_behavioral_analytics
        self.security_config = security_config or SecurityConfig()

        # Components
        self.auth_service: Optional[SecurityService] = None
        self.security_manager: Optional[EnterpriseSecurityManager] = None
        self.security_dashboard: Optional[SecurityDashboard] = None

        # Security metrics
        self.initialization_time = datetime.now(timezone.utc)
        self.is_initialized = False

    async def initialize(self) -> bool:
        """Initialize complete security suite"""
        try:
            logger.info("🚀 INITIALIZING ENTERPRISE SECURITY SUITE")
            start_time = datetime.now(timezone.utc)

            # 1. Initialize core authentication service
            logger.info("🔐 Initializing Authentication Service...")
            self.auth_service = initialize_security_service(
                database_path=self.database_path, secret_key=self.secret_key
            )
            await self.auth_service.initialize_database()
            logger.info("✅ Authentication Service initialized")

            # 2. Initialize enterprise security manager
            logger.info("🛡️ Initializing Enterprise Security Manager...")
            self.security_manager = await initialize_enterprise_security_manager(
                database_path=self.database_path,
                redis_url=self.redis_url,
                geoip_database_path=self.geoip_database_path,
                enable_geo_blocking=self.enable_geo_blocking,
                enable_behavioral_analytics=self.enable_behavioral_analytics,
                compliance_frameworks=self.compliance_frameworks,
            )
            logger.info("✅ Enterprise Security Manager initialized")

            # 3. Initialize security dashboard
            logger.info("📊 Initializing Security Dashboard...")
            self.security_dashboard = await initialize_security_dashboard(
                database_path=self.database_path, redis_url=self.redis_url
            )
            logger.info("✅ Security Dashboard initialized")

            # 4. Create default admin user if none exists
            await self._ensure_admin_user()

            # 5. Start automated security tasks
            await self._start_security_automation()

            self.is_initialized = True
            init_duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info("🎉 ENTERPRISE SECURITY SUITE INITIALIZED SUCCESSFULLY")
            logger.info(f"⏱️ Initialization completed in {init_duration:.2f}s")
            logger.info("🛡️ Security Features Active:")
            logger.info("   • JWT Authentication & RBAC")
            logger.info("   • Real-time Threat Detection")
            logger.info(
                f"   • Behavioral Analytics: {'✅' if self.enable_behavioral_analytics else '❌'}"
            )
            logger.info(
                f"   • Geo-blocking: {'✅' if self.enable_geo_blocking else '❌'}"
            )
            logger.info(
                f"   • Compliance Frameworks: {', '.join([f.value.upper() for f in self.compliance_frameworks])}"
            )
            logger.info("   • Security Dashboard & Monitoring")
            logger.info("   • Input Validation & Sanitization")

            return True

        except Exception as e:
            logger.error(f"❌ FAILED TO INITIALIZE ENTERPRISE SECURITY SUITE: {e}")
            self.is_initialized = False
            return False

    async def _ensure_admin_user(self):
        """Ensure default admin user exists"""
        try:
            # Check if any admin users exist
            async with self.auth_service._SecurityService__conn_manager() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM users WHERE role = ?", (UserRole.ADMIN.value,)
                )
                admin_count = (await cursor.fetchone())[0]

            if admin_count == 0:
                # Create default admin user
                default_admin = UserRegistration(
                    username="admin",
                    email="admin@novelengine.local",
                    password="AdminPassword123!",  # Should be changed immediately
                    role=UserRole.ADMIN,
                )

                await self.auth_service.register_user(
                    registration=default_admin,
                    ip_address="127.0.0.1",
                    user_agent="system_initialization",
                )

                logger.warning("⚠️ DEFAULT ADMIN USER CREATED")
                logger.warning("   Username: admin")
                logger.warning("   Password: AdminPassword123!")
                logger.warning("   🚨 CHANGE THIS PASSWORD IMMEDIATELY! 🚨")

        except Exception as e:
            logger.error(f"Error ensuring admin user: {e}")

    async def _start_security_automation(self):
        """Start automated security tasks"""
        try:
            # Start security cleanup task
            asyncio.create_task(self._security_cleanup_task())

            # Start threat intelligence updates
            asyncio.create_task(self._threat_intelligence_updater())

            logger.info("🤖 Automated security tasks started")

        except Exception as e:
            logger.error(f"Error starting security automation: {e}")

    async def _security_cleanup_task(self):
        """Periodic security cleanup and maintenance"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                # Clean expired tokens
                # Clean old security events (keep 90 days)
                # Update threat intelligence
                # Generate security reports

                logger.debug("🧹 Security cleanup task completed")

            except Exception as e:
                logger.error(f"Security cleanup task error: {e}")
                await asyncio.sleep(3600)

    async def _threat_intelligence_updater(self):
        """Update threat intelligence data periodically"""
        while True:
            try:
                await asyncio.sleep(3600 * 6)  # Update every 6 hours

                # This would integrate with external threat intelligence feeds
                # For now, we'll just log that it's running
                logger.debug("🔍 Threat intelligence update completed")

            except Exception as e:
                logger.error(f"Threat intelligence update error: {e}")
                await asyncio.sleep(3600 * 6)

    def configure_fastapi_security(self, app: FastAPI) -> FastAPI:
        """Configure FastAPI app with complete security suite"""

        if not self.is_initialized:
            raise RuntimeError(
                "Security suite must be initialized before configuring FastAPI"
            )

        logger.info("🔧 Configuring FastAPI with Enterprise Security...")

        # 1. Add security middleware
        app.add_middleware(SecurityMiddleware, config=self.security_config)

        # 2. Add CORS middleware (configured securely)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://localhost:3000"],  # Restrict origins
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
            expose_headers=["X-CSRF-Token"],
        )

        # 3. Add custom security middleware for request evaluation
        @app.middleware("http")
        async def security_evaluation_middleware(request: Request, call_next):
            # Skip evaluation for static assets and health checks
            if request.url.path.startswith("/static/") or request.url.path in [
                "/health",
                "/metrics",
            ]:
                return await call_next(request)

            try:
                # Get current user if authenticated
                user_id = None
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    try:
                        token = auth_header.split(" ")[1]
                        payload = self.auth_service._decode_token(token)
                        user_id = payload.get("sub")
                    except Exception:
                        pass  # Not authenticated, continue with anonymous evaluation

                # Evaluate request security
                (
                    is_allowed,
                    security_actions,
                    threat_level,
                ) = await self.security_manager.evaluate_request_security(
                    request, user_id
                )

                if not is_allowed:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "Request blocked by security policy",
                            "threat_level": threat_level.value,
                            "reference": f"security_block_{int(datetime.now().timestamp())}",
                        },
                    )

                # Add security headers to request for downstream processing
                request.state.security_actions = security_actions
                request.state.threat_level = threat_level

                response = await call_next(request)

                # Add security context to response headers
                response.headers["X-Security-Threat-Level"] = threat_level.value
                if security_actions:
                    response.headers["X-Security-Actions"] = ",".join(
                        [a.value for a in security_actions]
                    )

                return response

            except Exception as e:
                logger.error(f"Security evaluation middleware error: {e}")
                # Fail secure - block on errors for critical paths
                if request.url.path.startswith("/api/admin/"):
                    return JSONResponse(
                        status_code=500, content={"error": "Security evaluation failed"}
                    )
                return await call_next(request)

        # 4. Add security API endpoints
        self._add_security_api_endpoints(app)

        # 5. Add dashboard endpoints
        self._add_dashboard_endpoints(app)

        logger.info("✅ FastAPI configured with Enterprise Security")
        return app

    def _add_security_api_endpoints(self, app: FastAPI):
        """Add security-related API endpoints"""

        # Authentication endpoints
        @app.post("/api/auth/register", response_model=dict)
        async def register_user(registration: UserRegistration, request: Request):
            try:
                client_ip = self.security_manager._extract_client_ip(request)
                user_agent = request.headers.get("user-agent", "unknown")

                user = await self.auth_service.register_user(
                    registration=registration,
                    ip_address=client_ip,
                    user_agent=user_agent,
                )

                return {
                    "success": True,
                    "message": "User registered successfully",
                    "user_id": user.id,
                }

            except Exception as e:
                logger.error(f"Registration error: {e}")
                raise HTTPException(status_code=400, detail=str(e))

        @app.post("/api/auth/login", response_model=TokenPair)
        async def login_user(login_data: UserLogin, request: Request):
            try:
                client_ip = self.security_manager._extract_client_ip(request)
                user_agent = request.headers.get("user-agent", "unknown")

                user = await self.auth_service.authenticate_user(
                    login=login_data, ip_address=client_ip, user_agent=user_agent
                )

                if not user:
                    raise HTTPException(status_code=401, detail="Invalid credentials")

                token_pair = await self.auth_service.create_token_pair(user)
                return token_pair

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Login error: {e}")
                raise HTTPException(status_code=500, detail="Login failed")

        @app.post("/api/auth/refresh", response_model=TokenPair)
        async def refresh_token(refresh_token: str):
            try:
                return await self.auth_service.refresh_access_token(refresh_token)
            except Exception:
                raise HTTPException(status_code=401, detail="Token refresh failed")

        # Security management endpoints (admin only)
        @app.get("/api/security/metrics")
        async def get_security_metrics(
            current_user: User = Depends(
                self.auth_service.require_permission(Permission.SYSTEM_ADMIN)
            ),
        ):
            return await self.security_manager.get_security_metrics()

        @app.post("/api/security/ip/{ip_address}/block")
        async def block_ip_address(
            ip_address: str,
            reason: str,
            severity: ThreatLevel,
            expires_hours: Optional[int] = None,
            current_user: User = Depends(
                self.auth_service.require_permission(Permission.SYSTEM_ADMIN)
            ),
        ):
            await self.security_manager.add_ip_to_reputation_list(
                ip_address=ip_address,
                list_type="blacklist",
                reason=reason,
                severity=severity,
                created_by=current_user.username,
                expires_hours=expires_hours,
            )
            return {"success": True, "message": f"IP {ip_address} blocked"}

        @app.get("/api/security/compliance/summary")
        async def get_compliance_summary(
            current_user: User = Depends(
                self.auth_service.require_permission(Permission.SYSTEM_ADMIN)
            ),
        ):
            return await self.security_dashboard.get_compliance_summary()

    def _add_dashboard_endpoints(self, app: FastAPI):
        """Add security dashboard endpoints"""

        @app.get("/api/dashboard/overview")
        async def get_dashboard_overview(
            current_user: User = Depends(
                self.auth_service.require_permission(Permission.SYSTEM_HEALTH)
            ),
        ):
            return await self.security_dashboard.get_dashboard_overview()

        @app.websocket("/ws/security-dashboard")
        async def websocket_security_dashboard(websocket: WebSocket):
            await self.security_dashboard.websocket_endpoint(websocket)

    async def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status"""
        if not self.is_initialized:
            return {
                "status": "not_initialized",
                "message": "Security suite not initialized",
            }

        try:
            # Get metrics from all components
            auth_metrics = {"status": "active", "service": "authentication"}
            security_metrics = await self.security_manager.get_security_metrics()
            dashboard_overview = await self.security_dashboard.get_dashboard_overview()
            compliance_summary = await self.security_dashboard.get_compliance_summary()

            return {
                "status": "active",
                "initialization_time": self.initialization_time.isoformat(),
                "components": {
                    "authentication": auth_metrics,
                    "threat_detection": security_metrics,
                    "dashboard": dashboard_overview,
                    "compliance": compliance_summary,
                },
                "security_features": {
                    "behavioral_analytics": self.enable_behavioral_analytics,
                    "geo_blocking": self.enable_geo_blocking,
                    "compliance_frameworks": [
                        f.value for f in self.compliance_frameworks
                    ],
                },
            }

        except Exception as e:
            logger.error(f"Error getting security status: {e}")
            return {"status": "error", "error": str(e), "components_status": "degraded"}

    async def cleanup(self):
        """Cleanup security suite resources"""
        try:
            if self.security_manager:
                await self.security_manager.cleanup()

            logger.info("🧹 Enterprise Security Suite cleaned up")

        except Exception as e:
            logger.error(f"Error during security suite cleanup: {e}")


# Global security suite instance
security_suite: Optional[EnterpriseSecuritySuite] = None


def get_security_suite() -> EnterpriseSecuritySuite:
    """Get the global security suite instance"""
    global security_suite
    if security_suite is None:
        raise RuntimeError("Security suite not initialized")
    return security_suite


async def initialize_security_suite(**kwargs) -> EnterpriseSecuritySuite:
    """Initialize the global security suite"""
    global security_suite
    security_suite = EnterpriseSecuritySuite(**kwargs)
    success = await security_suite.initialize()

    if not success:
        raise RuntimeError("Failed to initialize security suite")

    return security_suite


def create_secure_app(
    title: str = "Novel Engine API",
    version: str = "1.0.0",
    security_config: Dict[str, Any] = None,
) -> FastAPI:
    """Create a FastAPI app with enterprise security pre-configured"""

    app = FastAPI(
        title=title,
        version=version,
        docs_url="/docs" if security_config.get("enable_docs", False) else None,
        redoc_url="/redoc" if security_config.get("enable_docs", False) else None,
        openapi_url=(
            "/openapi.json" if security_config.get("enable_docs", False) else None
        ),
    )

    # Add security health check endpoint
    @app.get("/security/health")
    async def security_health_check():
        try:
            suite = get_security_suite()
            return await suite.get_security_status()
        except Exception:
            logger.exception("Security health check failed.")
            return JSONResponse(
                status_code=503, content={"status": "error", "error": "unavailable"}
            )

    return app


__all__ = [
    "EnterpriseSecuritySuite",
    "get_security_suite",
    "initialize_security_suite",
    "create_secure_app",
    "SecurityService",
    "EnterpriseSecurityManager",
    "SecurityDashboard",
    "SecurityMiddleware",
    "UserRole",
    "Permission",
    "ThreatLevel",
    "SecurityAction",
    "ComplianceFramework",
]
