import json

import pytest

from src.workspaces.filesystem import FilesystemCharacterStore, FilesystemWorkspaceStore

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_workspace_manifest_created(tmp_path):
    store = FilesystemWorkspaceStore(tmp_path / "workspaces")
    workspace = store.create()

    manifest_path = workspace.root / "manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schemaVersion"] == 1
    assert manifest["createdAt"]
    assert manifest["lastAccessedAt"]


@pytest.mark.unit
def test_character_store_rejects_path_traversal_ids(tmp_path):
    ws_store = FilesystemWorkspaceStore(tmp_path / "workspaces")
    character_store = FilesystemCharacterStore(ws_store)
    workspace = ws_store.create()

    with pytest.raises(ValueError):
        character_store.create(workspace.id, "../evil", {"name": "Bad"})

    with pytest.raises(ValueError):
        character_store.get(workspace.id, "..\\evil")


@pytest.mark.unit
def test_character_store_atomic_write_leaves_no_tmp_files(tmp_path):
    ws_store = FilesystemWorkspaceStore(tmp_path / "workspaces")
    character_store = FilesystemCharacterStore(ws_store)
    workspace = ws_store.create()

    character_store.create(workspace.id, "char_1", {"name": "Alice"})
    character_store.update(workspace.id, "char_1", {"background_summary": "Updated"})

    tmp_files = list((workspace.root / "characters").glob(".char_1.json.tmp.*"))
    assert tmp_files == []
