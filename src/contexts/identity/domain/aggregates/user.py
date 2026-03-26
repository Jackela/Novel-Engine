"""
User Aggregate Root

Manages user accounts, authentication state, and profile information.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.contexts.identity.domain.types import UserStatus
from src.shared.domain.base.aggregate import AggregateRoot


@dataclass(kw_only=True, eq=False)
class User(AggregateRoot):
    """
    User aggregate root for authentication and identity management.

    AI注意:
    - Users are the central identity in the system
    - Email must be unique across the system
    - Password is always hashed, never stored plaintext
    - Supports multiple roles per user
    """

    email: str
    username: str
    hashed_password: str
    status: UserStatus = field(default="active")
    roles: List[str] = field(default_factory=list)
    profile: Dict[str, Any] = field(default_factory=dict)
    email_verified: bool = field(default=False)
    last_login: Optional[datetime] = None
    failed_login_attempts: int = field(default=0)
    locked_until: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate user invariants."""
        super().__post_init__()

        if not self.email or "@" not in self.email:
            raise ValueError("Valid email required")

        if not self.username or len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")

        if not self.hashed_password:
            raise ValueError("Password hash required")

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == "active" and not self.is_locked

    def verify_email(self) -> None:
        """Mark email as verified."""
        self.email_verified = True
        self.updated_at = datetime.utcnow()

    def record_login(self, success: bool) -> None:
        """
        Record a login attempt.

        Args:
            success: Whether the login was successful
        """
        if success:
            self.last_login = datetime.utcnow()
            self.failed_login_attempts = 0
            self.locked_until = None
        else:
            self.failed_login_attempts += 1

            # Lock account after 5 failed attempts
            if self.failed_login_attempts >= 5:
                self.locked_until = datetime.utcnow() + timedelta(
                    seconds=3600
                )  # 1 hour

        self.updated_at = datetime.utcnow()

    def change_password(self, new_hashed_password: str) -> None:
        """
        Change user password.

        Args:
            new_hashed_password: Pre-hashed new password
        """
        self.hashed_password = new_hashed_password
        self.updated_at = datetime.utcnow()

    def add_role(self, role: str) -> None:
        """Add a role to the user."""
        if role not in self.roles:
            self.roles.append(role)
            self.updated_at = datetime.utcnow()

    def remove_role(self, role: str) -> None:
        """Remove a role from the user."""
        if role in self.roles:
            self.roles.remove(role)
            self.updated_at = datetime.utcnow()

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.status = "inactive"
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the user account."""
        self.status = "active"
        self.updated_at = datetime.utcnow()

    def update_profile(self, **kwargs: Any) -> None:
        """Update user profile fields."""
        self.profile.update(kwargs)
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary (excludes sensitive data)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "status": self.status,
            "roles": self.roles,
            "profile": self.profile,
            "email_verified": self.email_verified,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
