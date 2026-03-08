# Workspaces Module

## Purpose
Provides multi-tenant workspace isolation for the Novel Engine platform. Each workspace represents an isolated environment with its own:
- Characters
- Worlds
- Stories
- Knowledge bases
- Campaign data

Workspaces enable multiple users or projects to use the same Novel Engine instance while maintaining complete data separation.

## Components

### Workspace
Entity representing a workspace.

**Attributes:**
- `id`: Unique identifier (UUID)
- `root`: Filesystem path to workspace directory (Path)

### WorkspaceStore (Abstract)
Manages workspace lifecycle operations.

```python
from src.workspaces import WorkspaceStore

# Implementations provide:
store: WorkspaceStore

# Create new workspace
workspace = store.create()

# Get or create existing
workspace = store.get_or_create("workspace-id")

# Export to ZIP
zip_bytes = store.export_zip("workspace-id")

# Import from ZIP
workspace = store.import_zip(zip_bytes)
```

### CharacterStore (Abstract)
Manages character data within workspaces.

```python
from src.workspaces import CharacterStore

store: CharacterStore

# List character IDs
character_ids = store.list_ids("workspace-id")

# Get character data
character = store.get("workspace-id", "character-id")

# Create character
data = store.create("workspace-id", "character-id", payload)

# Update character
data = store.update("workspace-id", "character-id", updates)

# Delete character
store.delete("workspace-id", "character-id")
```

### RunStore (Abstract)
Manages simulation run data.

```python
from src.workspaces import RunStore

store: RunStore

# List run IDs
run_ids = store.list_ids("workspace-id")
```

## Implementations

### FilesystemWorkspaceStore
Filesystem-based workspace storage implementation.

**File:** `src/workspaces/filesystem.py`

Features:
- Directory-based workspace isolation
- JSON file storage for entities
- ZIP export/import support
- Automatic directory creation

### GuestSession
Temporary workspace for unauthenticated users.

**File:** `src/workspaces/guest_session.py`

Features:
- Time-limited access
- Automatic cleanup
- Limited quota enforcement

## Usage

```python
from src.workspaces import WorkspaceStore, CharacterStore
from src.workspaces.filesystem import FilesystemWorkspaceStore

# Initialize stores
workspace_store = FilesystemWorkspaceStore(base_path=Path("./workspaces"))

# Create workspace
workspace = workspace_store.create()
print(f"Created workspace: {workspace.id}")

# Use with character store
character_store = SomeCharacterStoreImplementation()
character_data = {
    "name": "Hero",
    "class": "Fighter",
    "level": 1
}
character = character_store.create(workspace.id, "hero-001", character_data)

# Export workspace
zip_data = workspace_store.export_zip(workspace.id)
with open("backup.zip", "wb") as f:
    f.write(zip_data)

# Import workspace
restored = workspace_store.import_zip(zip_data)
```

## Testing

```bash
pytest tests/workspaces/ -v
```

## Security

- Workspaces are strictly isolated at the filesystem level
- Cross-workspace access is prohibited by interface design
- Sensitive data should be encrypted at rest
- Workspace IDs are UUIDs to prevent enumeration attacks

## Integration

This module is used by:
- API layer for request isolation
- All context repositories for data separation
- Import/export functionality for backup/restore

## Future Enhancements

- Cloud storage backends (S3, GCS)
- Workspace sharing and permissions
- Workspace templates
- Automatic archival for inactive workspaces
