"""
Identity Context Types

Type definitions for the identity context.
"""

from typing import Literal, NewType
from uuid import UUID

# ID Types
UserId = NewType("UserId", UUID)
RoleId = NewType("RoleId", UUID)
PermissionId = NewType("PermissionId", UUID)
SessionId = NewType("SessionId", UUID)

# Enumerations
UserStatus = Literal[
    "active",
    "inactive",
    "suspended",
    "pending_verification",
]

RoleName = Literal[
    "admin",
    "author",
    "reader",
    "moderator",
]

PermissionAction = Literal[
    "create",
    "read",
    "update",
    "delete",
    "publish",
    "manage",
]

TokenType = Literal[
    "access",
    "refresh",
    "verification",
    "password_reset",
]
