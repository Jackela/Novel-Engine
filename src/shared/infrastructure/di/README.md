# Dependency Injection (DI) Container

This module provides a professional dependency injection container for Novel Engine using the `dependency-injector` library.

## Features

- **Automatic Dependency Resolution**: Dependencies are automatically injected into services
- **Lifecycle Management**: Support for Singleton, Transient (Factory), and Scoped lifetimes
- **Circular Dependency Detection**: Built-in validation to detect circular dependency chains
- **FastAPI Integration**: Ready-to-use dependency providers for FastAPI endpoints
- **Modular Architecture**: Organized by bounded contexts (Identity, Knowledge, World, Narrative)

## Quick Start

### 1. Using the Container

```python
from src.shared.infrastructure.di import get_container, container_lifespan

# Get the global container
container = get_container()

# Configure with settings
container.config.from_dict({
    "database": {
        "url": "postgresql://user:pass@localhost/db",
        "max_connections": 20
    },
    "security": {
        "secret_key": "your-secret-key-32-chars-minimum!!",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30
    }
})

# Resolve dependencies
jwt_manager = container.core.jwt_manager()
auth_service = container.identity.authentication_service()
```

### 2. FastAPI Integration

```python
from fastapi import FastAPI, Depends
from src.shared.infrastructure.di import (
    container_lifespan,
    get_authentication_service,
    get_current_user
)
from src.contexts.identity.application.services import AuthenticationService

# Create app with container lifespan
app = FastAPI(lifespan=container_lifespan)

@app.post("/login")
async def login(
    auth_service: AuthenticationService = Depends(get_authentication_service)
):
    # Use auth_service
    pass

@app.get("/profile")
async def profile(user: dict = Depends(get_current_user)):
    return user
```

### 3. Lifecycle Management

```python
from src.shared.infrastructure.di import initialize_container, shutdown_container

# Startup
container = await initialize_container()

# Application runs...

# Shutdown
await shutdown_container()
```

## Container Structure

```
ApplicationContainer
├── core: CoreContainer
│   ├── db_pool (Singleton) - Database connection pool
│   ├── jwt_manager (Singleton) - JWT token manager
│   └── honcho_client (Singleton) - Honcho memory client
├── identity: IdentityContainer
│   ├── user_repository (Factory) - User data access
│   └── authentication_service (Factory) - Authentication logic
├── knowledge: KnowledgeContainer
│   └── knowledge_service (Factory) - Knowledge base operations
├── world: WorldContainer
│   └── (World state management services)
└── narrative: NarrativeContainer
    └── (Story/chapter/scene management)
```

## Provider Types

- **Singleton**: Created once and reused (e.g., `db_pool`, `jwt_manager`)
- **Factory**: Created fresh each time (e.g., `user_repository`, services)
- **Configuration**: Injected from settings

## Validation

```python
from src.shared.infrastructure.di import validate_container, check_circular_dependencies

# Validate container configuration
results = validate_container(container)
print(f"Valid: {results['is_valid']}")
print(f"Errors: {results['errors']}")
print(f"Warnings: {results['warnings']}")

# Check for circular dependencies
circular = check_circular_dependencies(container)
if circular:
    print(f"Found cycles: {circular}")
```

## Testing

```python
import pytest
from src.shared.infrastructure.di import get_container, reset_container

@pytest.fixture
def test_container():
    reset_container()
    container = get_container()
    container.config.from_dict({
        "database": {"url": "postgresql://test:test@localhost/test"},
        "security": {"secret_key": "test-key-32-characters-long!!!"}
    })
    yield container
    reset_container()

def test_jwt_manager(test_container):
    jwt_manager = test_container.core.jwt_manager()
    assert jwt_manager is not None
```

## Configuration Options

The container supports configuration from:
- Python dictionaries: `container.config.from_dict({...})`
- YAML files: `container.config.from_yaml('config.yaml')`
- Environment variables: `container.config.from_env()`
- pydantic-settings: Automatically loads from `get_settings()`

## Migration from Manual DI

### Before (Manual)
```python
# Global singletons
_db_pool = None
_jwt_manager = None

def get_db_pool():
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabaseConnectionPool(...)
    return _db_pool

def get_jwt_manager():
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager(...)
    return _jwt_manager
```

### After (DI Container)
```python
from src.shared.infrastructure.di import get_container

container = get_container()
db_pool = container.core.db_pool()  # Singleton, auto-managed
jwt_manager = container.core.jwt_manager()  # Singleton, auto-managed
```

## Benefits

1. **Testability**: Easy to mock dependencies in tests
2. **Decoupling**: Services depend on abstractions, not concrete implementations
3. **Lifecycle Management**: Automatic resource cleanup
4. **Configuration**: Centralized, environment-aware configuration
5. **Validation**: Detect issues at startup, not runtime
6. **Documentation**: Self-documenting dependency graph

## Best Practices

1. Use **Singleton** for stateless, expensive-to-create services (db pool, http clients)
2. Use **Factory** for stateful or request-scoped services (repositories, application services)
3. Always configure the container before resolving dependencies
4. Use `container_lifespan` for proper resource cleanup in FastAPI
5. Validate container in CI/CD pipelines
6. Mock the container in unit tests for isolation
