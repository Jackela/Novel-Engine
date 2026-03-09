"""
Tests for Authentication System Module

Coverage targets:
- Password hashing (bcrypt)
- JWT token generation and validation
- Token refresh
- Password verification
"""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio

pytestmark = pytest.mark.unit

from src.security.auth_system import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ROLE_PERMISSIONS,
    AuthenticationError,
    AuthorizationError,
    OperationError,
    OperationResult,
    Permission,
    SecurityService,
    TokenPair,
    User,
    UserLogin,
    UserRegistration,
    UserRole,
    get_security_service,
    initialize_security_service,
)


class TestUserRole:
    """Tests for UserRole enum."""

    def test_user_roles(self):
        """Test all user roles are defined."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.MODERATOR.value == "moderator"
        assert UserRole.CONTENT_CREATOR.value == "creator"
        assert UserRole.API_USER.value == "api_user"
        assert UserRole.READER.value == "reader"
        assert UserRole.GUEST.value == "guest"


class TestPermission:
    """Tests for Permission enum."""

    def test_system_permissions(self):
        """Test system-level permissions."""
        assert Permission.SYSTEM_ADMIN.value == "system:admin"
        assert Permission.SYSTEM_CONFIG.value == "system:config"
        assert Permission.SYSTEM_HEALTH.value == "system:health"

    def test_user_permissions(self):
        """Test user management permissions."""
        assert Permission.USER_CREATE.value == "user:create"
        assert Permission.USER_READ.value == "user:read"
        assert Permission.USER_UPDATE.value == "user:update"
        assert Permission.USER_DELETE.value == "user:delete"

    def test_content_permissions(self):
        """Test content permissions."""
        assert Permission.STORY_CREATE.value == "story:create"
        assert Permission.STORY_READ.value == "story:read"
        assert Permission.CHARACTER_CREATE.value == "character:create"
        assert Permission.CHARACTER_READ.value == "character:read"


class TestRolePermissions:
    """Tests for ROLE_PERMISSIONS mapping."""

    def test_admin_has_all_permissions(self):
        """Test admin role has all permissions."""
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        # Should have system admin
        assert Permission.SYSTEM_ADMIN in admin_perms
        # Should have user management
        assert Permission.USER_CREATE in admin_perms
        assert Permission.USER_DELETE in admin_perms
        # Should have content permissions
        assert Permission.STORY_CREATE in admin_perms
        assert Permission.CHARACTER_CREATE in admin_perms

    def test_reader_limited_permissions(self):
        """Test reader role has limited permissions."""
        reader_perms = ROLE_PERMISSIONS[UserRole.READER]
        assert Permission.STORY_READ in reader_perms
        assert Permission.CHARACTER_READ in reader_perms
        assert Permission.SYSTEM_HEALTH in reader_perms
        # Should not have write permissions
        assert Permission.STORY_CREATE not in reader_perms
        assert Permission.USER_CREATE not in reader_perms

    def test_guest_minimal_permissions(self):
        """Test guest role has minimal permissions."""
        guest_perms = ROLE_PERMISSIONS[UserRole.GUEST]
        assert len(guest_perms) == 2
        assert Permission.SYSTEM_HEALTH in guest_perms
        assert Permission.STORY_READ in guest_perms


@pytest.mark.asyncio
class TestSecurityService:
    """Tests for SecurityService class."""

    @pytest_asyncio.fixture
    async def security_service(self):
        """Create a SecurityService instance with temp database."""
        service = SecurityService(
            database_path=":memory:",
            secret_key="test_secret_key_for_testing_only",
        )
        await service.initialize_database()
        yield service
        await service.close()

    async def test_initialization(self):
        """Test service initialization requires secret key."""
        with pytest.raises(ValueError, match="secret key is required"):
            SecurityService(":memory:")

    async def test_initialize_database(self, security_service):
        """Test database initialization creates tables."""
        # Tables should be created during fixture setup
        async with security_service._connection() as conn:
            # Check users table exists
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "users"

            # Check refresh_tokens table exists
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='refresh_tokens'"
            )
            row = await cursor.fetchone()
            assert row is not None

    async def test_password_hashing(self, security_service):
        """Test password hashing with bcrypt."""
        password = "test_password_123"
        hashed = security_service._hash_password(password)

        # Hash should be different from original
        assert hashed != password
        # Hash should be valid bcrypt format
        assert hashed.startswith("$2")
        # Should verify correctly
        assert security_service._verify_password(password, hashed) is True
        # Wrong password should fail
        assert security_service._verify_password("wrong_password", hashed) is False

    async def test_hash_password_unique(self, security_service):
        """Test that same password produces different hashes (due to salt)."""
        password = "test_password_123"
        hash1 = security_service._hash_password(password)
        hash2 = security_service._hash_password(password)

        # Hashes should be different due to different salts
        assert hash1 != hash2
        # But both should verify correctly
        assert security_service._verify_password(password, hash1) is True
        assert security_service._verify_password(password, hash2) is True

    async def test_user_registration_success(self, security_service):
        """Test successful user registration."""
        registration = UserRegistration(
            username="testuser",
            email="test@example.com",
            password="secure_password_123",
            role=UserRole.READER,
        )

        user = await security_service.register_user(
            registration,
            ip_address="127.0.0.1",
            user_agent="Test Agent",
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.READER
        assert user.is_active is True
        assert user.id is not None

    async def test_user_registration_duplicate_username(self, security_service):
        """Test registration fails with duplicate username."""
        registration = UserRegistration(
            username="testuser",
            email="test@example.com",
            password="secure_password_123",
        )

        await security_service.register_user(registration, "127.0.0.1", "Test Agent")

        # Try to register again with same username
        registration2 = UserRegistration(
            username="testuser",
            email="different@example.com",
            password="secure_password_123",
        )

        with pytest.raises(AuthenticationError, match="Username already exists"):
            await security_service.register_user(
                registration2, "127.0.0.1", "Test Agent"
            )

    async def test_user_registration_duplicate_email(self, security_service):
        """Test registration fails with duplicate email."""
        registration = UserRegistration(
            username="user1",
            email="test@example.com",
            password="secure_password_123",
        )

        await security_service.register_user(registration, "127.0.0.1", "Test Agent")

        # Try to register again with same email
        registration2 = UserRegistration(
            username="user2",
            email="test@example.com",
            password="secure_password_123",
        )

        with pytest.raises(AuthenticationError, match="Email already exists"):
            await security_service.register_user(
                registration2, "127.0.0.1", "Test Agent"
            )

    async def test_authenticate_user_success(self, security_service):
        """Test successful user authentication."""
        # Register a user first
        registration = UserRegistration(
            username="authuser",
            email="auth@example.com",
            password="secure_password_123",
        )
        await security_service.register_user(registration, "127.0.0.1", "Test Agent")

        # Authenticate
        login = UserLogin(username="authuser", password="secure_password_123")
        user = await security_service.authenticate_user(
            login, ip_address="127.0.0.1", user_agent="Test Agent"
        )

        assert user is not None
        assert user.username == "authuser"
        assert user.last_login is not None

    async def test_authenticate_user_wrong_password(self, security_service):
        """Test authentication fails with wrong password."""
        # Register a user first
        registration = UserRegistration(
            username="authuser2",
            email="auth2@example.com",
            password="secure_password_123",
        )
        await security_service.register_user(registration, "127.0.0.1", "Test Agent")

        # Try to authenticate with wrong password
        login = UserLogin(username="authuser2", password="wrong_password")
        user = await security_service.authenticate_user(
            login, ip_address="127.0.0.1", user_agent="Test Agent"
        )

        assert user is None

    async def test_authenticate_user_not_found(self, security_service):
        """Test authentication fails for non-existent user."""
        login = UserLogin(username="nonexistent", password="password")
        user = await security_service.authenticate_user(
            login, ip_address="127.0.0.1", user_agent="Test Agent"
        )

        assert user is None

    async def test_authenticate_user_account_locked(self, security_service):
        """Test authentication fails for locked account."""
        # Register a user
        registration = UserRegistration(
            username="lockeduser",
            email="locked@example.com",
            password="secure_password_123",
        )
        await security_service.register_user(registration, "127.0.0.1", "Test Agent")

        # Fail login multiple times to lock account
        login = UserLogin(username="lockeduser", password="wrong")
        for _ in range(5):
            await security_service.authenticate_user(
                login, ip_address="127.0.0.1", user_agent="Test Agent"
            )

        # Next attempt should raise account locked error
        with pytest.raises(AuthenticationError, match="Account is temporarily locked"):
            await security_service.authenticate_user(
                login, ip_address="127.0.0.1", user_agent="Test Agent"
            )

    async def test_create_token_pair(self, security_service):
        """Test token pair creation."""
        # Create a user
        user = User(
            id="test_user_id",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role=UserRole.READER,
        )

        token_pair = await security_service.create_token_pair(user)

        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == "Bearer"
        assert token_pair.expires_in == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    async def test_token_generation_and_validation(self, security_service):
        """Test JWT token generation and validation."""
        # Create a token
        payload = {"user_id": "test123", "username": "testuser", "role": "reader"}
        token = security_service._generate_token(
            payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # Verify token can be decoded
        decoded = security_service._decode_token(token)
        assert decoded["user_id"] == "test123"
        assert decoded["username"] == "testuser"
        assert decoded["role"] == "reader"
        assert "exp" in decoded
        assert "iat" in decoded
        assert "jti" in decoded

    async def test_token_expiration(self, security_service):
        """Test expired token raises error."""
        # Create an expired token
        payload = {"user_id": "test123"}
        token = security_service._generate_token(
            payload,
            timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(AuthenticationError, match="Token has expired"):
            security_service._decode_token(token)

    async def test_invalid_token(self, security_service):
        """Test invalid token raises error."""
        with pytest.raises(AuthenticationError, match="Invalid token"):
            security_service._decode_token("invalid_token")

    async def test_refresh_access_token_success(self, security_service):
        """Test successful token refresh."""
        # Create a user and token pair
        user = User(
            id="refresh_test_id",
            username="refreshuser",
            email="refresh@example.com",
            password_hash="hashed",
            role=UserRole.READER,
        )

        # Insert user into database
        async with security_service._connection() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    user.id,
                    user.username,
                    user.email,
                    user.password_hash,
                    user.role.value,
                    True,
                ),
            )
            await conn.commit()

        token_pair = await security_service.create_token_pair(user)

        # Refresh the token
        new_token_pair = await security_service.refresh_access_token(
            token_pair.refresh_token
        )

        assert isinstance(new_token_pair, TokenPair)
        assert new_token_pair.access_token != token_pair.access_token

    async def test_refresh_access_token_invalid(self, security_service):
        """Test refresh with invalid token fails."""
        with pytest.raises(AuthenticationError, match="Invalid refresh token"):
            await security_service.refresh_access_token("invalid_token")

    async def test_validate_token_success(self, security_service):
        """Test successful token validation."""
        # Create a valid token
        payload = {"user_id": "test123", "type": "access"}
        token = security_service._generate_token(payload, timedelta(minutes=15))

        result = await security_service.validate_token(token)

        assert result.success is True
        assert result.data["user_id"] == "test123"
        assert result.data["token_type"] == "access"

    async def test_validate_token_expired(self, security_service):
        """Test expired token validation returns error."""
        # Create an expired token
        payload = {"user_id": "test123"}
        token = security_service._generate_token(payload, timedelta(seconds=-1))

        result = await security_service.validate_token(token)

        assert result.success is False
        assert result.error is not None
        assert "expired" in result.error.message.lower()

    async def test_has_permission(self, security_service):
        """Test permission checking."""
        # Admin should have all permissions
        assert (
            security_service.has_permission(UserRole.ADMIN, Permission.SYSTEM_ADMIN)
            is True
        )
        assert (
            security_service.has_permission(UserRole.ADMIN, Permission.USER_DELETE)
            is True
        )

        # Reader should have limited permissions
        assert (
            security_service.has_permission(UserRole.READER, Permission.STORY_READ)
            is True
        )
        assert (
            security_service.has_permission(UserRole.READER, Permission.STORY_CREATE)
            is False
        )

        # String role should work too
        assert security_service.has_permission("admin", Permission.SYSTEM_ADMIN) is True
        assert (
            security_service.has_permission("invalid_role", Permission.SYSTEM_ADMIN)
            is False
        )

    async def test_get_role_permissions(self, security_service):
        """Test getting permissions for a role."""
        admin_perms = security_service.get_role_permissions(UserRole.ADMIN)
        assert len(admin_perms) > 10  # Admin has many permissions

        guest_perms = security_service.get_role_permissions(UserRole.GUEST)
        assert len(guest_perms) == 2

        # Invalid role returns empty set
        invalid_perms = security_service.get_role_permissions("invalid")
        assert len(invalid_perms) == 0

    async def test_generate_api_key(self, security_service):
        """Test API key generation."""
        # Create a user
        async with security_service._connection() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "api_test_id",
                    "apiuser",
                    "api@example.com",
                    "hashed",
                    UserRole.API_USER.value,
                    True,
                ),
            )
            await conn.commit()

        api_key = await security_service.generate_api_key("api_test_id")

        assert api_key.startswith("nve_")
        assert len(api_key) > 20  # Should be reasonably long

    async def test_validate_api_key_success(self, security_service):
        """Test successful API key validation."""
        # Create user with API key
        api_key = "nve_test_key_123"
        async with security_service._connection() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, username, email, password_hash, role, is_active, api_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "api_val_id",
                    "apiuser",
                    "api@example.com",
                    "hashed",
                    UserRole.API_USER.value,
                    True,
                    api_key,
                ),
            )
            await conn.commit()

        user = await security_service.validate_api_key(api_key)

        assert user is not None
        assert user.username == "apiuser"
        assert user.role == UserRole.API_USER

    async def test_validate_api_key_invalid(self, security_service):
        """Test invalid API key returns None."""
        user = await security_service.validate_api_key("invalid_key")
        assert user is None

    async def test_create_user_validation(self, security_service):
        """Test user creation with password validation."""
        # Valid password
        result = await security_service.create_user(
            username="validuser",
            email="valid@example.com",
            password="Secure_Pass123",
            role=UserRole.READER,
        )

        assert result.success is True
        assert result.data["username"] == "validuser"

    async def test_create_user_short_password(self, security_service):
        """Test user creation fails with short password."""
        with pytest.raises(AuthenticationError, match="at least 8 characters"):
            await security_service.create_user(
                username="shortpass",
                email="short@example.com",
                password="short",
                role=UserRole.READER,
            )

    async def test_create_user_common_password(self, security_service):
        """Test user creation fails with common password."""
        with pytest.raises(AuthenticationError, match="too common"):
            await security_service.create_user(
                username="commonpass",
                email="common@example.com",
                password="password",
                role=UserRole.READER,
            )

    async def test_create_user_weak_password(self, security_service):
        """Test user creation fails with weak password."""
        with pytest.raises(AuthenticationError, match="at least one number"):
            await security_service.create_user(
                username="weakpass",
                email="weak@example.com",
                password="onlyletters",
                role=UserRole.READER,
            )


class TestTokenPair:
    """Tests for TokenPair model."""

    def test_token_pair_defaults(self):
        """Test TokenPair default values."""
        token = TokenPair(access_token="access123", refresh_token="refresh456")
        assert token.access_token == "access123"
        assert token.refresh_token == "refresh456"
        assert token.token_type == "Bearer"
        assert token.expires_in == ACCESS_TOKEN_EXPIRE_MINUTES * 60


class TestUser:
    """Tests for User dataclass."""

    def test_user_creation(self):
        """Test User creation."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role=UserRole.READER,
            is_active=True,
            is_verified=False,
        )

        assert user.id == "user123"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.READER
        assert user.is_active is True
        assert user.is_verified is False
        assert user.created_at is not None

    def test_user_post_init(self):
        """Test User post_init sets created_at."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            password_hash="hashed",
            role=UserRole.READER,
        )

        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)


class TestOperationResult:
    """Tests for OperationResult dataclass."""

    def test_success_result(self):
        """Test successful operation result."""
        result = OperationResult(
            success=True,
            data={"user_id": "123"},
        )
        assert result.success is True
        assert result.data["user_id"] == "123"
        assert result.error is None

    def test_error_result(self):
        """Test error operation result."""
        error = OperationError(message="Something went wrong", code="ERROR_001")
        result = OperationResult(
            success=False,
            error=error,
        )
        assert result.success is False
        assert result.error.message == "Something went wrong"
        assert result.error.code == "ERROR_001"


class TestExceptions:
    """Tests for custom exceptions."""

    def test_authentication_error(self):
        """Test AuthenticationError exception."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Authentication failed")

    def test_authorization_error(self):
        """Test AuthorizationError exception."""
        with pytest.raises(AuthorizationError):
            raise AuthorizationError("Not authorized")


class TestGlobalInstances:
    """Tests for global instances and initialization."""

    async def test_get_security_service_not_initialized(self):
        """Test getting service before initialization raises error."""
        import src.security.auth_system as auth_module

        original = auth_module.security_service
        auth_module.security_service = None

        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                get_security_service()
        finally:
            auth_module.security_service = original

    async def test_initialize_security_service(self):
        """Test security service initialization."""
        import src.security.auth_system as auth_module

        original = auth_module.security_service

        try:
            auth_module.security_service = None
            service = initialize_security_service(":memory:", "test_key")
            assert service is not None
            assert auth_module.security_service is service
        finally:
            if auth_module.security_service:
                await auth_module.security_service.close()
            auth_module.security_service = original
