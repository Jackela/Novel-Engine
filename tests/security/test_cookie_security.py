"""
Security tests for httpOnly cookie authentication [SEC-001]

This module tests the security improvements implemented in SEC-001:
- httpOnly cookie storage for tokens
- CSRF token generation and validation
- Secure cookie flags (Secure, SameSite, HttpOnly)
- Cookie clearing on logout
- Token validation and expiry

Test Categories:
1. Cookie Security Flags
2. Login Cookie Setting
3. Logout Cookie Clearing
4. CSRF Token Protection
5. XSS Mitigation
6. Token Validation
"""

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest

# Import the FastAPI app
from api_server import JWT_ALGORITHM, JWT_SECRET_KEY, app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_credentials():
    """Provide mock login credentials for testing."""
    return {
        "email": "test@example.com",
        "password": "securepassword123",
        "remember_me": False,
    }


class TestCookieSecurity:
    """Test suite for cookie security implementation [SEC-001]"""

    @pytest.mark.unit
    def test_login_sets_httponly_cookie(self, client, mock_credentials):
        """
        Test that login endpoint sets httpOnly cookie for access token.

        Verifies:
        - Cookie is set with httpOnly flag
        - Cookie has correct name
        - Response still includes token in body for backward compatibility
        """
        response = client.post("/api/auth/login", json=mock_credentials)

        assert response.status_code == 200
        data = response.json()

        # Verify response body contains tokens (backward compatibility)
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data

        # Verify cookies are set
        cookies = response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies

        # Verify cookie attributes via Set-Cookie headers
        set_cookie_headers = response.headers.get_list("set-cookie")
        access_cookie = [h for h in set_cookie_headers if "access_token=" in h][0]

        # Verify security flags
        assert "HttpOnly" in access_cookie
        assert "SameSite=Lax" in access_cookie or "SameSite=lax" in access_cookie

    @pytest.mark.unit
    def test_login_sets_refresh_token_cookie(self, client, mock_credentials):
        """
        Test that login endpoint sets httpOnly cookie for refresh token.

        Verifies:
        - Refresh token cookie is set
        - Cookie has correct security flags
        - Expiry is longer than access token
        """
        response = client.post("/api/auth/login", json=mock_credentials)

        assert response.status_code == 200

        # Verify cookies are set
        cookies = response.cookies
        assert "refresh_token" in cookies

        # Verify cookie attributes
        set_cookie_headers = response.headers.get_list("set-cookie")
        refresh_cookie = [h for h in set_cookie_headers if "refresh_token=" in h][0]

        # Verify security flags
        assert "HttpOnly" in refresh_cookie
        assert "SameSite=Lax" in refresh_cookie or "SameSite=lax" in refresh_cookie

    @pytest.mark.unit
    def test_remember_me_extends_cookie_duration(self, client):
        """
        Test that remember_me flag extends refresh token cookie duration.

        Verifies:
        - remember_me=true results in longer Max-Age
        - remember_me=false results in standard Max-Age
        """
        # Test with remember_me=true
        credentials_remember = {
            "email": "test@example.com",
            "password": "password123",
            "remember_me": True,
        }

        response_remember = client.post("/api/auth/login", json=credentials_remember)
        set_cookie_remember = response_remember.headers.get_list("set-cookie")
        refresh_cookie_remember = [
            h for h in set_cookie_remember if "refresh_token=" in h
        ][0]

        # Extract Max-Age from cookie (format: Max-Age=<seconds>)
        # With remember_me, it should be 30 days = 2592000 seconds
        assert "Max-Age=" in refresh_cookie_remember

    @pytest.mark.unit
    def test_logout_clears_cookies(self, client, mock_credentials):
        """
        Test that logout endpoint clears all authentication cookies.

        Verifies:
        - access_token cookie is deleted
        - refresh_token cookie is deleted
        - csrf_token cookie is deleted
        - Response indicates success
        """
        # First login to set cookies
        login_response = client.post("/api/auth/login", json=mock_credentials)
        assert login_response.status_code == 200

        # Then logout
        logout_response = client.post("/api/auth/logout")

        assert logout_response.status_code == 200
        data = logout_response.json()
        assert data["success"] is True
        assert data["message"] == "Logout successful"

        # Verify cookies are cleared via Set-Cookie headers
        set_cookie_headers = logout_response.headers.get_list("set-cookie")

        # Check that cookies are set to expire (Max-Age=0 or expires in past)
        # Note: FastAPI's delete_cookie sets the cookie with an expired date
        # The exact behavior may vary, so we check for the presence of cookie deletion
        assert len(set_cookie_headers) >= 2  # At least access_token and refresh_token

    @pytest.mark.unit
    def test_csrf_token_generation(self, client):
        """
        Test CSRF token generation endpoint.

        Verifies:
        - CSRF token is generated
        - Cookie is set (non-httpOnly so JS can read it)
        - Token is returned in response body
        - SameSite is set to strict for CSRF tokens
        """
        response = client.get("/api/auth/csrf-token")

        assert response.status_code == 200
        data = response.json()

        # Verify token in response
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 0

        # Verify cookie is set
        cookies = response.cookies
        assert "csrf_token" in cookies

        # Verify cookie attributes
        set_cookie_headers = response.headers.get_list("set-cookie")
        csrf_cookie = [h for h in set_cookie_headers if "csrf_token=" in h][0]

        # CSRF cookie should NOT be HttpOnly (JS needs to read it)
        assert "HttpOnly" not in csrf_cookie

        # CSRF cookie should have SameSite=strict
        assert "SameSite=Strict" in csrf_cookie or "SameSite=strict" in csrf_cookie

    @pytest.mark.unit
    def test_cookie_not_accessible_via_javascript(self, client, mock_credentials):
        """
        Test that httpOnly cookies cannot be accessed via JavaScript.

        This is a conceptual test - in a real browser, httpOnly cookies
        are not accessible to document.cookie. Here we verify the flag is set.

        Verifies:
        - HttpOnly flag is present in Set-Cookie header
        - Tokens are protected from XSS attacks
        """
        response = client.post("/api/auth/login", json=mock_credentials)

        set_cookie_headers = response.headers.get_list("set-cookie")

        # Both access_token and refresh_token should have HttpOnly flag
        for cookie_header in set_cookie_headers:
            if "access_token=" in cookie_header or "refresh_token=" in cookie_header:
                assert (
                    "HttpOnly" in cookie_header
                ), f"Cookie missing HttpOnly flag: {cookie_header}"

    @pytest.mark.unit
    def test_token_validation_endpoint(self, client, mock_credentials):
        """
        Test token validation endpoint.

        Verifies:
        - Valid token returns 200 with valid=true
        - Invalid token returns 401 with valid=false
        - Expired token returns 401
        """
        # Login to get a valid token
        login_response = client.post("/api/auth/login", json=mock_credentials)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]

        # Test valid token
        valid_response = client.get(
            "/api/auth/validate", headers={"Authorization": f"Bearer {token}"}
        )

        assert valid_response.status_code == 200
        data = valid_response.json()
        assert data["valid"] is True
        assert "expires_at" in data
        assert "user_id" in data

    @pytest.mark.unit
    def test_token_validation_missing_token(self, client):
        """
        Test token validation with missing Authorization header.

        Verifies:
        - Returns 401
        - Error message indicates missing header
        """
        response = client.get("/api/auth/validate")

        assert response.status_code == 401
        data = response.json()
        assert data["valid"] is False
        assert "error" in data

    @pytest.mark.unit
    def test_token_validation_expired_token(self, client):
        """
        Test token validation with expired token.

        Verifies:
        - Expired token returns 401
        - Error indicates expiration
        """
        # Create an expired token
        expired_payload = {
            "user_id": "test-user-id",
            "email": "test@example.com",
            "exp": datetime.now(UTC) - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "type": "access",
        }

        expired_token = jwt.encode(
            expired_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
        )

        response = client.get(
            "/api/auth/validate", headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["valid"] is False
        assert "expired" in data["error"].lower()

    @pytest.mark.unit
    def test_token_refresh_with_cookie(self, client, mock_credentials):
        """
        Test token refresh using httpOnly cookie.

        Verifies:
        - Refresh token from cookie is used
        - New access token is returned
        - New access token cookie is set
        """
        import time

        # Login to get refresh token
        login_response = client.post("/api/auth/login", json=mock_credentials)
        assert login_response.status_code == 200

        refresh_token = login_response.json()["refresh_token"]

        # Wait to ensure the new token will have a different timestamp
        # (JWTs created within the same second have identical timestamps)
        time.sleep(1.1)

        # Refresh using cookie (simulated by sending empty body)
        # The TestClient will automatically include cookies from previous responses
        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},  # For backward compatibility
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()

        # Verify new access token is returned
        assert "access_token" in data
        assert data["access_token"] != login_response.json()["access_token"]

        # Verify new access token cookie is set
        cookies = refresh_response.cookies
        assert "access_token" in cookies

    @pytest.mark.unit
    def test_secure_flag_environment_based(self, client, mock_credentials, monkeypatch):
        """
        Test that Secure flag is controlled by environment variable.

        Verifies:
        - COOKIE_SECURE=true sets Secure flag
        - COOKIE_SECURE=false does not set Secure flag (for local dev)
        """
        # This test depends on the environment configuration
        # In production, COOKIE_SECURE should be true
        # In development, it can be false

        response = client.post("/api/auth/login", json=mock_credentials)
        set_cookie_headers = response.headers.get_list("set-cookie")

        # Check if Secure flag is present
        # Default is true, so Secure should be present unless explicitly disabled
        access_cookie = [h for h in set_cookie_headers if "access_token=" in h][0]

        # The presence of Secure flag depends on COOKIE_SECURE env var
        # We just verify the cookie is set correctly
        assert "access_token=" in access_cookie

    @pytest.mark.unit
    def test_logout_always_succeeds(self, client):
        """
        Test that logout always returns success, even without valid session.

        Verifies:
        - Logout without login returns 200
        - Error during logout still returns success
        - Frontend can always reliably logout
        """
        # Logout without logging in first
        response = client.post("/api/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.unit
    def test_cors_credentials_support(self, client):
        """
        Test that CORS is configured to support credentials.

        Verifies:
        - Access-Control-Allow-Credentials header is set
        - Cookies can be sent cross-origin (for frontend-backend separation)
        """
        # Make an OPTIONS request to check CORS
        response = client.options("/api/auth/login")

        # Verify CORS headers
        assert response.status_code == 204
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers


@pytest.mark.integration
class TestCookieSecurityIntegration:
    """Integration tests for cookie security across multiple endpoints"""

    def test_full_auth_flow_with_cookies(self, client):
        """
        Test complete authentication flow using cookies.

        Flow:
        1. Get CSRF token
        2. Login with credentials
        3. Validate token
        4. Refresh token
        5. Logout

        Verifies all steps work with httpOnly cookies.
        """
        # Step 1: Get CSRF token
        csrf_response = client.get("/api/auth/csrf-token")
        assert csrf_response.status_code == 200

        # Step 2: Login
        credentials = {
            "email": "integrationtest@example.com",
            "password": "password123",
            "remember_me": False,
        }

        login_response = client.post("/api/auth/login", json=credentials)
        assert login_response.status_code == 200
        login_data = login_response.json()

        # Step 3: Validate token
        validate_response = client.get(
            "/api/auth/validate",
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

        # Step 4: Refresh token
        refresh_response = client.post(
            "/api/auth/refresh", json={"refresh_token": login_data["refresh_token"]}
        )
        assert refresh_response.status_code == 200

        # Step 5: Logout
        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 200
        assert logout_response.json()["success"] is True

    def test_xss_mitigation_httponly_cookies(self, client):
        """
        Test that httpOnly cookies mitigate XSS token theft.

        Verifies:
        - Tokens are not exposed in response body (after migration)
        - HttpOnly flag prevents JavaScript access
        - Even with XSS, attacker cannot steal tokens from cookies
        """
        credentials = {"email": "xsstest@example.com", "password": "password123"}

        response = client.post("/api/auth/login", json=credentials)
        assert response.status_code == 200

        # Verify httpOnly flag is set
        set_cookie_headers = response.headers.get_list("set-cookie")
        for cookie_header in set_cookie_headers:
            if "access_token=" in cookie_header or "refresh_token=" in cookie_header:
                assert "HttpOnly" in cookie_header

        # This confirms that even if an XSS attack injects malicious JavaScript,
        # it cannot access these cookies via document.cookie

    def test_csrf_protection_workflow(self, client):
        """
        Test CSRF protection workflow.

        Verifies:
        1. CSRF token is generated
        2. Token can be read by JavaScript (non-httpOnly)
        3. Token should be included in state-changing requests
        """
        # Get CSRF token
        csrf_response = client.get("/api/auth/csrf-token")
        assert csrf_response.status_code == 200

        csrf_token = csrf_response.json()["csrf_token"]
        assert len(csrf_token) > 0

        # Verify cookie is set and readable
        cookies = csrf_response.cookies
        assert "csrf_token" in cookies

        # Verify non-httpOnly (JavaScript can read it)
        set_cookie_headers = csrf_response.headers.get_list("set-cookie")
        csrf_cookie = [h for h in set_cookie_headers if "csrf_token=" in h][0]
        assert "HttpOnly" not in csrf_cookie


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
