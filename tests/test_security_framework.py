#!/usr/bin/env python3
"""
Security Framework Test Suite
============================

Comprehensive test suite for the enterprise-grade security framework
validating authentication, authorization, input validation, and more.

Professional security testing implementation.

Test Coverage: Authentication, Authorization, Input Validation, Rate Limiting,
               Security Headers, Data Protection, Security Logging
Author: Novel Engine Development Team
Professional test suite for enterprise security validation.
"""

import asyncio
import os
import tempfile
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

# Import the security framework components
from src.security.auth_system import (
    ROLE_PERMISSIONS,
    AuthenticationError,
    Permission,
    SecurityService,
    UserLogin,
    UserRegistration,
    UserRole,
)
from src.security.data_protection import (
    ConsentStatus,
    DataProtectionService,
    EncryptionService,
)
from src.security.input_validation import (
    InputType,
    InputValidator,
    ValidationError,
)
from src.security.rate_limiting import (
    RateLimitConfig,
    RateLimiter,
    RateLimitExceeded,
    ThreatLevel,
)
from src.security.security_headers import (
    SecurityHeaders,
    SecurityHeadersConfig,
)
from src.security.security_logging import (
    SecurityEvent,
    SecurityEventSeverity,
    SecurityEventType,
    SecurityLogger,
)


class TestSecurityService:
    """Security Service Tests"""

    @pytest_asyncio.fixture
    async def security_service(self):
        """Create a temporary security service for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        service = SecurityService(db_path, "test_secret_key")
        await service.initialize_database()

        yield service

        # Cleanup
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_user_registration(self, security_service):
        """Test user registration functionality"""
        registration = UserRegistration(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            role=UserRole.READER,
        )

        user = await security_service.register_user(
            registration, "127.0.0.1", "test-agent"
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.READER
        assert user.is_active is True
        assert user.password_hash != "securepassword123"  # Should be hashed

    @pytest.mark.asyncio
    async def test_duplicate_user_registration(self, security_service):
        """Test that duplicate usernames are rejected"""
        registration = UserRegistration(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            role=UserRole.READER,
        )

        # First registration should succeed
        await security_service.register_user(registration, "127.0.0.1", "test-agent")

        # Second registration with same username should fail
        with pytest.raises(AuthenticationError, match="Username already exists"):
            await security_service.register_user(
                registration, "127.0.0.1", "test-agent"
            )

    @pytest.mark.asyncio
    async def test_user_authentication(self, security_service):
        """Test user authentication"""
        # Register a user first
        registration = UserRegistration(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            role=UserRole.READER,
        )
        await security_service.register_user(registration, "127.0.0.1", "test-agent")

        # Test successful login
        login = UserLogin(username="testuser", password="securepassword123")
        user = await security_service.authenticate_user(
            login, "127.0.0.1", "test-agent"
        )

        assert user is not None
        assert user.username == "testuser"

        # Test failed login
        wrong_login = UserLogin(username="testuser", password="wrongpassword")
        user = await security_service.authenticate_user(
            wrong_login, "127.0.0.1", "test-agent"
        )

        assert user is None

    @pytest.mark.asyncio
    async def test_account_lockout(self, security_service):
        """Test account lockout after failed attempts"""
        # Register a user
        registration = UserRegistration(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            role=UserRole.READER,
        )
        await security_service.register_user(registration, "127.0.0.1", "test-agent")

        # Attempt multiple failed logins
        wrong_login = UserLogin(username="testuser", password="wrongpassword")

        for i in range(5):  # MAX_LOGIN_ATTEMPTS = 5
            user = await security_service.authenticate_user(
                wrong_login, "127.0.0.1", "test-agent"
            )
            assert user is None

        # Next attempt should raise account locked error
        with pytest.raises(AuthenticationError, match="Account is temporarily locked"):
            await security_service.authenticate_user(
                wrong_login, "127.0.0.1", "test-agent"
            )

    @pytest.mark.asyncio
    async def test_token_creation_and_refresh(self, security_service):
        """Test JWT token creation and refresh"""
        # Register and authenticate user
        registration = UserRegistration(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            role=UserRole.CONTENT_CREATOR,
        )
        user = await security_service.register_user(
            registration, "127.0.0.1", "test-agent"
        )

        # Create token pair
        token_pair = await security_service.create_token_pair(user)

        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == "Bearer"

        # Test token refresh
        new_token_pair = await security_service.refresh_access_token(
            token_pair.refresh_token
        )

        assert new_token_pair.access_token != token_pair.access_token
        assert new_token_pair.refresh_token is not None

    @pytest.mark.asyncio
    async def test_role_permissions(self, security_service):
        """Test role-based permissions"""
        # Test admin permissions
        admin_permissions = ROLE_PERMISSIONS[UserRole.ADMIN]
        assert Permission.SYSTEM_ADMIN in admin_permissions
        assert Permission.USER_MANAGE_ROLES in admin_permissions

        # Test reader permissions
        reader_permissions = ROLE_PERMISSIONS[UserRole.READER]
        assert Permission.SYSTEM_ADMIN not in reader_permissions
        assert Permission.STORY_READ in reader_permissions

    @pytest.mark.asyncio
    async def test_api_key_generation(self, security_service):
        """Test API key generation"""
        # Register a user
        registration = UserRegistration(
            username="apiuser",
            email="api@example.com",
            password="securepassword123",
            role=UserRole.API_USER,
        )
        user = await security_service.register_user(
            registration, "127.0.0.1", "test-agent"
        )

        # Generate API key
        api_key = await security_service.generate_api_key(user.id)

        assert api_key.startswith("nve_")
        assert len(api_key) > 32

        # Validate API key
        validated_user = await security_service.validate_api_key(api_key)

        assert validated_user is not None
        assert validated_user.username == "apiuser"


class TestInputValidator:
    """Input Validator Tests"""

    @pytest.fixture
    def validator(self):
        """Create input validator for testing"""
        return InputValidator()

    def test_sql_injection_detection(self, validator):
        """Test SQL injection detection"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM passwords",
            "'; INSERT INTO admin VALUES ('hacker'); --",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValidationError):
                validator.validate_input(malicious_input, InputType.TEXT)

    def test_xss_detection(self, validator):
        """Test XSS detection"""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
        ]

        for xss_input in xss_inputs:
            with pytest.raises(ValidationError):
                validator.validate_input(xss_input, InputType.TEXT)

    def test_command_injection_detection(self, validator):
        """Test command injection detection"""
        command_injections = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc -l 4444",
            "$(whoami)",
        ]

        for cmd_injection in command_injections:
            with pytest.raises(ValidationError):
                validator.validate_input(cmd_injection, InputType.TEXT)

    def test_path_traversal_detection(self, validator):
        """Test path traversal detection"""
        path_traversals = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//etc/passwd",
        ]

        for path_traversal in path_traversals:
            with pytest.raises(ValidationError):
                validator.validate_input(path_traversal, InputType.FILENAME)

    def test_valid_input_passes(self, validator):
        """Test that valid input passes validation"""
        valid_inputs = [
            ("Hello, World!", InputType.TEXT),
            ("user@example.com", InputType.EMAIL),
            ("validfilename.txt", InputType.FILENAME),
            ("https://example.com", InputType.URL),
        ]

        for valid_input, input_type in valid_inputs:
            # Should not raise exception
            result = validator.validate_input(valid_input, input_type)
            assert result is not None

    def test_json_validation(self, validator):
        """Test JSON validation"""
        # Valid JSON
        valid_json = '{"name": "test", "value": 123}'
        result = validator.validate_json(valid_json)
        assert result["name"] == "test"
        assert result["value"] == 123

        # Invalid JSON
        invalid_json = '{"name": "test", malformed'
        with pytest.raises(ValidationError):
            validator.validate_json(invalid_json)

        # JSON with malicious content
        malicious_json = '{"script": "<script>alert(1)</script>"}'
        with pytest.raises(ValidationError):
            validator.validate_json(malicious_json)


class TestRateLimiter:
    """Rate Limiter Tests"""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing"""
        config = RateLimitConfig(
            requests_per_minute=10, requests_per_hour=100, burst_size=5
        )
        return RateLimiter(config)

    @pytest.fixture
    def mock_request(self):
        """Create mock request for testing"""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent"}
        request.url.path = "/test"
        return request

    @pytest.mark.asyncio
    async def test_rate_limiting_allows_normal_requests(
        self, rate_limiter, mock_request
    ):
        """Test that normal requests are allowed"""
        # Should allow first few requests
        for i in range(5):
            result = await rate_limiter.check_rate_limit(mock_request)
            assert result is True

    @pytest.mark.asyncio
    async def test_rate_limiting_blocks_excessive_requests(
        self, rate_limiter, mock_request
    ):
        """Test that excessive requests are blocked"""
        # Exhaust the rate limit
        for i in range(10):
            try:
                await rate_limiter.check_rate_limit(mock_request)
            except RateLimitExceeded:
                break

        # Next request should be blocked
        with pytest.raises(RateLimitExceeded):
            await rate_limiter.check_rate_limit(mock_request)

    @pytest.mark.asyncio
    async def test_threat_detection(self, rate_limiter, mock_request):
        """Test threat detection capabilities"""
        # Simulate rapid requests
        for i in range(20):
            try:
                await rate_limiter.check_rate_limit(mock_request)
                await asyncio.sleep(0.05)  # Very fast requests
            except RateLimitExceeded as e:
                # Should detect as suspicious activity
                assert e.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
                break

    @pytest.mark.asyncio
    async def test_ip_blacklist(self, rate_limiter, mock_request):
        """Test IP blacklisting"""
        # Add IP to blacklist
        rate_limiter.config.blacklist_ips.append("127.0.0.1")

        # Request should be immediately blocked
        with pytest.raises(RateLimitExceeded) as exc_info:
            await rate_limiter.check_rate_limit(mock_request)

        assert "blacklisted" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ip_whitelist(self, rate_limiter, mock_request):
        """Test IP whitelisting"""
        # Add IP to whitelist
        rate_limiter.config.whitelist_ips.append("127.0.0.1")

        # Should allow unlimited requests
        for i in range(50):
            result = await rate_limiter.check_rate_limit(mock_request)
            assert result is True


class TestSecurityHeaders:
    """Security Headers Tests"""

    @pytest.fixture
    def security_headers(self):
        """Create security headers for testing"""
        config = SecurityHeadersConfig()
        return SecurityHeaders(config)

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = MagicMock()
        request.url.scheme = "https"
        request.headers = {"host": "example.com"}
        request.method = "GET"
        return request

    @pytest.fixture
    def mock_response(self):
        """Create mock response"""
        response = MagicMock()
        response.headers = {}
        return response

    def test_csp_header_construction(self, security_headers):
        """Test CSP header construction"""
        csp_header = security_headers._build_csp_header()

        assert "default-src 'self'" in csp_header
        assert "script-src 'self'" in csp_header
        assert "object-src 'none'" in csp_header
        assert "frame-ancestors 'none'" in csp_header

    def test_security_headers_application(
        self, security_headers, mock_request, mock_response
    ):
        """Test security headers are applied correctly"""
        response = security_headers.apply_headers(mock_response, mock_request)

        # Check essential security headers
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "Referrer-Policy" in response.headers

        # Check values
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_hsts_header_construction(self, security_headers):
        """Test HSTS header construction"""
        hsts_header = security_headers._build_hsts_header()

        assert "max-age=" in hsts_header
        assert "includeSubDomains" in hsts_header
        assert "preload" in hsts_header

    def test_permissions_policy_construction(self, security_headers):
        """Test Permissions Policy header construction"""
        permissions_header = security_headers._build_permissions_policy_header()

        assert "camera=()" in permissions_header
        assert "microphone=()" in permissions_header
        assert "geolocation=()" in permissions_header


class TestDataProtection:
    """Data Protection Tests"""

    @pytest_asyncio.fixture
    async def data_protection_service(self):
        """Create data protection service for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        service = DataProtectionService(db_path, "test_master_key")
        await service.initialize_database()

        yield service

        # Cleanup
        os.unlink(db_path)

    def test_encryption_service(self):
        """Test encryption and decryption"""
        encryption_service = EncryptionService("test_key")

        original_data = "sensitive information"
        encrypted_data = encryption_service.encrypt(original_data)
        decrypted_data = encryption_service.decrypt(encrypted_data)

        assert encrypted_data != original_data
        assert decrypted_data == original_data

    def test_dictionary_encryption(self):
        """Test dictionary encryption"""
        encryption_service = EncryptionService("test_key")

        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "secret123",
            "public_info": "not sensitive",
        }

        fields_to_encrypt = ["email", "password"]
        encrypted_data = encryption_service.encrypt_dict(data, fields_to_encrypt)

        # Should encrypt specified fields
        assert encrypted_data["email"] != data["email"]
        assert encrypted_data["password"] != data["password"]
        # Should not encrypt other fields
        assert encrypted_data["username"] == data["username"]
        assert encrypted_data["public_info"] == data["public_info"]

        # Test decryption
        decrypted_data = encryption_service.decrypt_dict(
            encrypted_data, fields_to_encrypt
        )
        assert decrypted_data["email"] == data["email"]
        assert decrypted_data["password"] == data["password"]

    @pytest.mark.asyncio
    async def test_consent_management(self, data_protection_service):
        """Test consent recording and checking"""
        user_id = "test_user_123"
        purpose = "story_generation"
        processing_activities = ["generate_stories", "save_preferences"]
        consent_text = "I consent to story generation processing"

        # Record consent
        consent_record = await data_protection_service.record_consent(
            user_id, purpose, processing_activities, consent_text
        )

        assert consent_record.user_id == user_id
        assert consent_record.purpose == purpose
        assert consent_record.status == ConsentStatus.GRANTED

        # Check consent
        has_consent = await data_protection_service.check_consent(user_id, purpose)
        assert has_consent is True

        # Withdraw consent
        withdrawn = await data_protection_service.withdraw_consent(user_id, purpose)
        assert withdrawn is True

        # Check consent after withdrawal
        has_consent = await data_protection_service.check_consent(user_id, purpose)
        assert has_consent is False

    @pytest.mark.asyncio
    async def test_data_encryption_by_type(self, data_protection_service):
        """Test data encryption based on data type"""
        user_data = {
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "preferences": "dark_mode",
        }

        # Encrypt user email data
        encrypted_data = await data_protection_service.encrypt_personal_data(
            user_data, "user_email"
        )

        # Email should be encrypted
        assert encrypted_data["email"] != user_data["email"]

        # Decrypt data
        decrypted_data = await data_protection_service.decrypt_personal_data(
            encrypted_data, "user_email"
        )

        assert decrypted_data["email"] == user_data["email"]

    @pytest.mark.asyncio
    async def test_data_retention_scheduling(self, data_protection_service):
        """Test data retention scheduling"""
        from src.security.data_protection import DataRetentionPeriod

        await data_protection_service.schedule_data_deletion(
            "user_data", "test_user", DataRetentionPeriod.SHORT_TERM
        )

        # In a real test, you would check the database for the scheduled deletion
        # For now, we just verify no exception was raised


class TestSecurityLogging:
    """Security Logging Tests"""

    @pytest_asyncio.fixture
    async def security_logger(self):
        """Create security logger for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        with tempfile.TemporaryDirectory() as log_dir:
            logger = SecurityLogger(db_path, log_dir)
            await logger.initialize_database()

            yield logger

            await logger.shutdown()

        # Cleanup
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_security_event_logging(self, security_logger):
        """Test security event logging"""
        event = SecurityEvent(
            event_id="test_event_123",
            event_type=SecurityEventType.LOGIN_SUCCESS,
            severity=SecurityEventSeverity.INFO,
            timestamp=datetime.now(timezone.utc),
            source_ip="127.0.0.1",
            user_id="test_user",
            username="testuser",
            message="User login successful",
        )

        await security_logger.log_security_event(event)

        # Retrieve events to verify logging
        events = await security_logger.get_security_events(limit=1)

        assert len(events) == 1
        assert events[0]["event_id"] == "test_event_123"
        assert events[0]["event_type"] == "login_success"
        assert events[0]["source_ip"] == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_security_statistics(self, security_logger):
        """Test security statistics generation"""
        # Log multiple events
        events = [
            SecurityEvent(
                event_id=f"event_{i}",
                event_type=(
                    SecurityEventType.LOGIN_SUCCESS
                    if i % 2 == 0
                    else SecurityEventType.LOGIN_FAILURE
                ),
                severity=(
                    SecurityEventSeverity.INFO
                    if i % 2 == 0
                    else SecurityEventSeverity.WARNING
                ),
                timestamp=datetime.now(timezone.utc),
                source_ip=f"127.0.0.{i}",
                message=f"Event {i}",
            )
            for i in range(10)
        ]

        for event in events:
            await security_logger.log_security_event(event)

        # Get statistics
        stats = await security_logger.get_security_statistics(time_range_hours=1)

        assert stats["total_events"] == 10
        assert "login_success" in stats["event_counts"]
        assert "login_failure" in stats["event_counts"]
        assert stats["event_counts"]["login_success"] == 5
        assert stats["event_counts"]["login_failure"] == 5

    @pytest.mark.asyncio
    async def test_threat_detection_logging(self, security_logger):
        """Test threat detection and alerting"""
        # Simulate multiple failed login attempts from same IP
        for i in range(15):
            event = SecurityEvent(
                event_id=f"failed_login_{i}",
                event_type=SecurityEventType.LOGIN_FAILURE,
                severity=SecurityEventSeverity.WARNING,
                timestamp=datetime.now(timezone.utc),
                source_ip="192.168.1.100",
                message="Failed login attempt",
            )
            await security_logger.log_security_event(event)

        # Should trigger threat detection
        events = await security_logger.get_security_events(
            event_type=SecurityEventType.INTRUSION_DETECTED, limit=5
        )

        # Should have generated an intrusion detection event
        assert len(events) > 0


class TestIntegratedSecurity:
    """Integrated Security Tests"""

    @pytest.mark.asyncio
    async def test_end_to_end_security_flow(self):
        """Test complete security flow from registration to protected access"""
        # This would test the complete security flow in a real API context
        # For now, we'll test the integration between components

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Initialize services
            security_service = SecurityService(db_path, "test_secret")
            await security_service.initialize_database()

            validator = InputValidator()

            # Test user registration with validation
            username = "testuser"
            email = "test@example.com"
            password = "securepassword123"

            # Validate inputs
            validated_username = validator.validate_input(username, InputType.USERNAME)
            validated_email = validator.validate_input(email, InputType.EMAIL)
            validated_password = validator.validate_input(password, InputType.PASSWORD)

            # Register user
            registration = UserRegistration(
                username=validated_username,
                email=validated_email,
                password=validated_password,
                role=UserRole.CONTENT_CREATOR,
            )

            user = await security_service.register_user(
                registration, "127.0.0.1", "test-agent"
            )

            # Create token
            token_pair = await security_service.create_token_pair(user)

            # Verify token contains correct permissions
            payload = security_service._decode_token(token_pair.access_token)

            assert payload["username"] == "testuser"
            assert payload["role"] == "creator"
            assert Permission.STORY_CREATE.value in payload["permissions"]
            assert Permission.SYSTEM_ADMIN.value not in payload["permissions"]

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_security_middleware_integration(self):
        """Test security middleware working together"""
        # This would test rate limiting + input validation + security headers
        # working together in a middleware stack

        config = RateLimitConfig(requests_per_minute=5, burst_size=2)
        rate_limiter = RateLimiter(config)
        validator = InputValidator()

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"user-agent": "test-agent"}
        mock_request.url.path = "/api/test"
        mock_request.method = "POST"
        mock_request.query_params = {"search": "normal query"}

        # Should pass rate limiting
        result = await rate_limiter.check_rate_limit(mock_request)
        assert result is True

        # Should pass input validation
        validated_query = validator.validate_input(
            mock_request.query_params["search"], InputType.TEXT
        )
        assert validated_query == "normal query"

        # Test with malicious input
        mock_request.query_params = {"search": "'; DROP TABLE users; --"}

        with pytest.raises(ValidationError):
            validator.validate_input(
                mock_request.query_params["search"], InputType.TEXT
            )


@pytest.mark.asyncio
async def test_performance_under_load():
    """Test security framework performance under load"""
    validator = InputValidator()

    # Test input validation performance
    start_time = time.time()

    for i in range(1000):
        validator.validate_input(f"test_input_{i}", InputType.TEXT)

    end_time = time.time()
    total_time = end_time - start_time

    # Should validate 1000 inputs in under 1 second
    assert total_time < 1.0

    # Test rate limiter performance
    config = RateLimitConfig(requests_per_minute=1000)
    rate_limiter = RateLimiter(config)

    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers = {"user-agent": "test-agent"}
    mock_request.url.path = "/test"

    start_time = time.time()

    for i in range(100):
        await rate_limiter.check_rate_limit(mock_request)

    end_time = time.time()
    total_time = end_time - start_time

    # Should handle 100 rate limit checks in under 100ms
    assert total_time < 0.1


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
