"""Identity domain ports package.

This package contains port interfaces (abstract contracts) that the
domain layer defines and infrastructure implements.
"""

from __future__ import annotations

from .authentication_port import AuthenticationPort
from .user_repository_port import UserRepositoryPort

__all__ = [
    "UserRepositoryPort",
    "AuthenticationPort",
]
