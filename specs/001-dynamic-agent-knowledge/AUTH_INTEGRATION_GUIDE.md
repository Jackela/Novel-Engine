# Authentication Integration Guide

**Tasks**: T008, T043  
**Goal**: Integrate Novel Engine authentication system with Knowledge Management API  
**Date**: 2025-01-04

---

## Overview

This guide provides complete implementation instructions for integrating the existing Novel Engine authentication system with the Knowledge Management API endpoints.

**Existing System**: `src/security/auth_system.py`  
**Target Files**: `src/api/knowledge_api.py`, `backend/api/middleware/auth_middleware.py`

---

## Current Authentication System Analysis

### Key Components

**1. SecurityService Class**:
```python
class SecurityService:
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials) -> User
    def require_permission(self, permission: Permission)
    def require_role(self, required_role: UserRole)
```

**2. User Roles** (src/security/auth_system.py:47-56):
```python
class UserRole(str, Enum):
    ADMIN = "admin"              # Full system access ✅
    MODERATOR = "moderator"       # Content moderation
    CONTENT_CREATOR = "creator"   # Story generation ✅
    API_USER = "api_user"        # API access
    READER = "reader"            # Read-only access
    GUEST = "guest"              # Limited access
```

**3. Permissions** (src/security/auth_system.py:58-112):
```python
class Permission(str, Enum):
    SYSTEM_ADMIN = "system:admin"
    # ... many more permissions
```

**4. Role-Permission Mapping** (lines 114-198):
- `ADMIN`: All permissions including system admin
- `CONTENT_CREATOR`: Story/character/simulation permissions
- Other roles: Limited permissions

### FastAPI Integration Pattern

**Standalone Dependency Functions** (lines 961-992):
```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> User:
    """Standalone wrapper for getting current user from token"""
    service = get_security_service()
    return await service.get_current_user(credentials)

def require_permission(permission: Permission):
    """Standalone wrapper for requiring permission"""
    service = get_security_service()
    return service.require_permission(permission)
```

---

## Recommended Role for Knowledge Management

### Option 1: Use Existing ADMIN Role ✅ **RECOMMENDED**

**Rationale**:
- ADMIN has full system access
- Appropriate for Game Masters managing centralized knowledge
- Already has all necessary permissions

**Implementation**:
```python
from src.security.auth_system import get_current_user, require_role, UserRole, User

@router.post("/entries", ...)
async def create_entry(
    request: CreateKnowledgeEntryRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    ...
) -> CreateKnowledgeEntryResponse:
    ...
```

### Option 2: Use CONTENT_CREATOR Role

**Rationale**:
- CONTENT_CREATOR can create stories, characters, simulations
- Knowledge management is similar to content creation
- More permissive than ADMIN

**Implementation**:
```python
@router.post("/entries", ...)
async def create_entry(
    request: CreateKnowledgeEntryRequest,
    current_user: User = Depends(require_role(UserRole.CONTENT_CREATOR)),
    ...
) -> CreateKnowledgeEntryResponse:
    ...
```

### Option 3: Create New GAME_MASTER Role (Future Enhancement)

**Rationale**:
- Specific role for Game Masters
- Separate from general ADMIN role
- More granular access control

**Requires**:
1. Add `GAME_MASTER = "game_master"` to `UserRole` enum
2. Define permissions for game masters
3. Add role-permission mapping

**Not Recommended for MVP**: Use existing roles first

---

## Implementation Steps

### Step 1: Update knowledge_api.py Dependencies

**Current Code** (src/api/knowledge_api.py:95-98):
```python
async def get_current_user() -> UserId:
    """Get current authenticated user ID (placeholder for auth integration)."""
    # TODO: Integrate with authentication middleware (T008)
    return "admin-user-001"
```

**Updated Code**:
```python
from src.security.auth_system import get_current_user, require_role, UserRole, User

# Remove placeholder function
# async def get_current_user() -> UserId: ...

# No longer needed - use SecurityService dependency directly
```

### Step 2: Update API Endpoint Dependencies

**Pattern for All Endpoints**:

**Before**:
```python
async def create_entry(
    request: CreateKnowledgeEntryRequest,
    repository: IKnowledgeRepository = Depends(get_repository),
    event_publisher: IEventPublisher = Depends(get_event_publisher),
    current_user: UserId = Depends(get_current_user),  # OLD
) -> CreateKnowledgeEntryResponse:
    ...
```

**After**:
```python
async def create_entry(
    request: CreateKnowledgeEntryRequest,
    repository: IKnowledgeRepository = Depends(get_repository),
    event_publisher: IEventPublisher = Depends(get_event_publisher),
    current_user: User = Depends(require_role(UserRole.ADMIN)),  # NEW
) -> CreateKnowledgeEntryResponse:
    # Extract user ID from User object
    user_id = current_user.user_id
    
    # Pass to use case
    entry_id = await use_case.execute(
        ...,
        created_by=user_id,  # Use extracted user_id
    )
    ...
```

### Step 3: Update All CRUD Endpoints

**Endpoints to Update**:
1. `POST /entries` (create_entry) - Requires ADMIN or CONTENT_CREATOR
2. `GET /entries` (list_entries) - Requires ADMIN or CONTENT_CREATOR
3. `GET /entries/{id}` (get_entry) - Requires ADMIN or CONTENT_CREATOR
4. `PUT /entries/{id}` (update_entry) - Requires ADMIN or CONTENT_CREATOR
5. `DELETE /entries/{id}` (delete_entry) - Requires ADMIN only

**Decision Matrix**:
```python
# Option A: All operations require ADMIN (strictest)
current_user: User = Depends(require_role(UserRole.ADMIN))

# Option B: Read operations allow CONTENT_CREATOR, write requires ADMIN
# GET endpoints:
current_user: User = Depends(require_role(UserRole.CONTENT_CREATOR))
# POST/PUT/DELETE endpoints:
current_user: User = Depends(require_role(UserRole.ADMIN))
```

**Recommended**: Option A (all require ADMIN) for MVP simplicity

---

## Complete Implementation Code

### File: src/api/knowledge_api.py

**Add Imports**:
```python
from src.security.auth_system import get_current_user, require_role, UserRole, User
```

**Remove Placeholder**:
```python
# DELETE THIS FUNCTION:
# async def get_current_user() -> UserId:
#     """Get current authenticated user ID (placeholder for auth integration)."""
#     # TODO: Integrate with authentication middleware (T008)
#     return "admin-user-001"
```

**Update create_entry**:
```python
@router.post(
    "/entries",
    response_model=CreateKnowledgeEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Knowledge Entry",
    description="Create a new knowledge entry with specified access control (FR-002)",
)
async def create_entry(
    request: CreateKnowledgeEntryRequest,
    repository: IKnowledgeRepository = Depends(get_repository),
    event_publisher: IEventPublisher = Depends(get_event_publisher),
    current_user: User = Depends(require_role(UserRole.ADMIN)),  # UPDATED
) -> CreateKnowledgeEntryResponse:
    """
    Create a new knowledge entry.
    
    Requires: Admin role (enforced by authentication middleware)
    """
    # Extract user ID from User object
    user_id = current_user.user_id
    
    # Start OpenTelemetry span (Article VII - Observability)
    if OTEL_AVAILABLE and tracer:
        with tracer.start_as_current_span("knowledge.create_entry") as span:
            span.set_attribute("knowledge_type", request.knowledge_type.value)
            span.set_attribute("access_level", request.access_level.value)
            span.set_attribute("user_id", user_id)  # UPDATED
            
            try:
                use_case = CreateKnowledgeEntryUseCase(repository, event_publisher)
                entry_id = await use_case.execute(
                    content=request.content,
                    knowledge_type=request.knowledge_type,
                    owning_character_id=request.owning_character_id,
                    access_level=request.access_level,
                    created_by=user_id,  # UPDATED
                    allowed_roles=tuple(request.allowed_roles),
                    allowed_character_ids=tuple(request.allowed_character_ids),
                )
                
                span.set_attribute("entry_id", entry_id)
                span.set_attribute("success", True)
                return CreateKnowledgeEntryResponse(entry_id=entry_id)
                
            except ValueError as e:
                span.set_attribute("error", str(e))
                span.set_attribute("success", False)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            except Exception as e:
                span.set_attribute("error", str(e))
                span.set_attribute("success", False)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    else:
        # Fallback without tracing
        try:
            use_case = CreateKnowledgeEntryUseCase(repository, event_publisher)
            entry_id = await use_case.execute(
                content=request.content,
                knowledge_type=request.knowledge_type,
                owning_character_id=request.owning_character_id,
                access_level=request.access_level,
                created_by=user_id,  # UPDATED
                allowed_roles=tuple(request.allowed_roles),
                allowed_character_ids=tuple(request.allowed_character_ids),
            )
            return CreateKnowledgeEntryResponse(entry_id=entry_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
```

**Update list_entries** (similar pattern):
```python
async def list_entries(
    knowledge_type: Optional[KnowledgeType] = None,
    owning_character_id: Optional[CharacterId] = None,
    repository: IKnowledgeRepository = Depends(get_repository),
    current_user: User = Depends(require_role(UserRole.ADMIN)),  # UPDATED
) -> List[KnowledgeEntryResponse]:
    ...
```

**Update get_entry**:
```python
async def get_entry(
    entry_id: UUID,
    repository: IKnowledgeRepository = Depends(get_repository),
    current_user: User = Depends(require_role(UserRole.ADMIN)),  # UPDATED
) -> KnowledgeEntryResponse:
    ...
```

**Update update_entry**:
```python
async def update_entry(
    entry_id: UUID,
    request: UpdateKnowledgeEntryRequest,
    repository: IKnowledgeRepository = Depends(get_repository),
    event_publisher: IEventPublisher = Depends(get_event_publisher),
    current_user: User = Depends(require_role(UserRole.ADMIN)),  # UPDATED
):
    user_id = current_user.user_id  # ADD THIS
    
    # ... OpenTelemetry span code ...
    
    use_case = UpdateKnowledgeEntryUseCase(repository, event_publisher)
    await use_case.execute(
        entry_id=str(entry_id),
        new_content=request.content,
        updated_by=user_id,  # UPDATED
    )
```

**Update delete_entry**:
```python
async def delete_entry(
    entry_id: UUID,
    repository: IKnowledgeRepository = Depends(get_repository),
    event_publisher: IEventPublisher = Depends(get_event_publisher),
    current_user: User = Depends(require_role(UserRole.ADMIN)),  # UPDATED
):
    user_id = current_user.user_id  # ADD THIS
    
    # ... OpenTelemetry span code ...
    
    use_case = DeleteKnowledgeEntryUseCase(repository, event_publisher)
    await use_case.execute(
        entry_id=str(entry_id),
        deleted_by=user_id,  # UPDATED
    )
```

---

## Testing Strategy

### Manual Testing

**Prerequisites**:
1. SecurityService initialized with database and secret key
2. User created with ADMIN role
3. JWT token obtained via login endpoint

**Test Cases**:

1. **Authenticated ADMIN user can create entry**:
```bash
curl -X POST http://localhost:8000/api/v1/knowledge/entries \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test", "knowledge_type": "world_lore", "access_level": "public"}'
```
Expected: 201 Created

2. **Unauthenticated request fails**:
```bash
curl -X POST http://localhost:8000/api/v1/knowledge/entries \
  -H "Content-Type: application/json" \
  -d '{"content": "Test", "knowledge_type": "world_lore", "access_level": "public"}'
```
Expected: 401 Unauthorized

3. **READER role cannot create entry**:
```bash
curl -X POST http://localhost:8000/api/v1/knowledge/entries \
  -H "Authorization: Bearer <reader_token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test", "knowledge_type": "world_lore", "access_level": "public"}'
```
Expected: 403 Forbidden

### Automated Testing

**Unit Tests** (tests/unit/knowledge/test_knowledge_api_auth.py):
```python
import pytest
from fastapi import HTTPException
from src.security.auth_system import User, UserRole

@pytest.mark.asyncio
async def test_create_entry_requires_admin_role():
    # Mock user without admin role
    reader_user = User(user_id="user-123", role=UserRole.READER, ...)
    
    # Attempt to create entry
    with pytest.raises(HTTPException) as exc:
        await create_entry(
            request=CreateKnowledgeEntryRequest(...),
            current_user=reader_user,
            ...
        )
    
    assert exc.value.status_code == 403
```

---

## Error Handling

### HTTP Status Codes

**401 Unauthorized**: Missing or invalid JWT token
- Message: "Could not validate credentials"
- Action: User needs to login

**403 Forbidden**: Valid token but insufficient permissions
- Message: "Insufficient permissions. Required role: admin"
- Action: Contact administrator for role upgrade

**500 Internal Server Error**: Authentication system failure
- Message: "Internal server error"
- Action: Check logs, verify SecurityService initialization

### Frontend Integration

**Update knowledgeApi.ts**:
```typescript
export class KnowledgeAPI {
  static async createEntry(request: CreateKnowledgeEntryRequest): Promise<string> {
    try {
      const response = await apiClient.post<{ entry_id: string }>(
        `${BASE_PATH}/entries`,
        request
      );
      return response.data.entry_id;
    } catch (error: any) {
      if (error.response?.status === 401) {
        // Redirect to login
        window.location.href = '/login';
        throw new Error('Authentication required. Please login.');
      } else if (error.response?.status === 403) {
        throw new Error('Insufficient permissions. Admin role required.');
      }
      console.error('[KnowledgeAPI] Failed to create entry:', error);
      throw new Error(
        error.response?.data?.detail || 'Failed to create knowledge entry'
      );
    }
  }
}
```

---

## Deployment Checklist

- [ ] Update src/api/knowledge_api.py imports
- [ ] Remove placeholder get_current_user function
- [ ] Update all 5 endpoint dependencies
- [ ] Extract user_id from User object in all endpoints
- [ ] Test with authenticated ADMIN user
- [ ] Test with unauthenticated request (expect 401)
- [ ] Test with non-ADMIN user (expect 403)
- [ ] Update frontend error handling
- [ ] Update API documentation (OpenAPI)
- [ ] Mark T008 and T043 as complete in tasks.md

---

## Constitution Compliance

### Article II (Hexagonal Architecture) ✅
- API layer depends on auth abstraction (SecurityService)
- No direct authentication logic in endpoints
- Clean separation of concerns

### Article VII (Observability) ✅
- User ID logged in OpenTelemetry spans
- Authentication failures logged
- Authorization violations tracked

---

## Alternative: Custom Middleware (Not Recommended for MVP)

**File**: backend/api/middleware/auth_middleware.py

```python
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.security.auth_system import get_security_service, UserRole

security = HTTPBearer()

async def knowledge_admin_middleware(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Middleware to enforce admin access for knowledge endpoints"""
    service = get_security_service()
    user = await service.get_current_user(credentials)
    
    # Check if user has admin role
    if user.role not in [UserRole.ADMIN, UserRole.CONTENT_CREATOR]:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. Admin or Content Creator role required."
        )
    
    request.state.user = user
    return user
```

**Not Recommended**: Adds unnecessary complexity, use `require_role` dependency instead

---

**Status**: Ready for implementation  
**Estimated Time**: 2-3 hours  
**Priority**: P0 (blocks User Story 1 completion)
