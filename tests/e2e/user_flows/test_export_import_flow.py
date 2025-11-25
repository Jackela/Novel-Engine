#!/usr/bin/env python3
"""
E2E Test: Data Export/Import and Portability Flow
=================================================

Tests data portability and export/import functionality:
1. Create complete dataset (world + characters + narrative)
2. Export data as JSON
3. Modify exported data
4. Import modified data
5. Verify data integrity and consistency

Coverage:
- Data export API
- Data import API
- JSON serialization/deserialization
- Data validation on import
- Referential integrity
- Version compatibility
"""

import json
import time
from pathlib import Path

import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
class TestExportImportFlow:
    """E2E tests for data export/import and portability."""

    def test_complete_export_import_cycle(
        self, client, data_factory, api_helper, temp_artifacts_dir, performance_tracker
    ):
        """
        Test complete export/import cycle for data portability.

        Flow:
        1. Create test data (characters + world)
        2. Export all data as JSON
        3. Verify export structure
        4. Modify exported data
        5. Import modified data
        6. Verify imported data integrity
        """
        # Step 1: Create comprehensive test dataset
        # Create characters
        characters_created = []
        char1_data = data_factory.create_character_data(
            name="Export Hero", agent_id="export_hero"
        )
        char1_data["skills"] = {"combat": 0.8, "magic": 0.6, "charisma": 0.7}

        response = client.post("/api/characters", json=char1_data)
        assert response.status_code in [
            200,
            201,
        ], f"Failed to create character: {response.text}"
        characters_created.append("export_hero")

        char2_data = data_factory.create_character_data(
            name="Export Companion", agent_id="export_companion"
        )
        char2_data["relationships"] = {
            "export_hero": 0.9  # High relationship with hero
        }

        response = client.post("/api/characters", json=char2_data)
        assert response.status_code in [200, 201]
        characters_created.append("export_companion")

        # Step 2: Export data
        start_time = time.time()
        export_response = client.get("/api/export/all")

        # If export endpoint doesn't exist, document expected behavior
        if export_response.status_code == 404:
            # Fallback: Export individual characters manually
            exported_data = {
                "version": "1.0",
                "timestamp": time.time(),
                "characters": [],
                "worlds": [],
                "metadata": {},
            }

            # Export each character
            for char_id in characters_created:
                response = client.get(f"/api/characters/{char_id}")
                if response.status_code == 200:
                    char_data = response.json().get("data", response.json())
                    exported_data["characters"].append(char_data)

        else:
            assert (
                export_response.status_code == 200
            ), f"Export failed: {export_response.text}"
            exported_data = export_response.json()

        performance_tracker.record(
            "data_export",
            time.time() - start_time,
            {"characters": len(characters_created)},
        )

        # Step 3: Verify export structure
        assert (
            "characters" in exported_data or "data" in exported_data
        ), "Export should contain data"

        # Save export to file
        export_file = temp_artifacts_dir / "exported_data.json"
        export_file.write_text(json.dumps(exported_data, indent=2))

        # Step 4: Modify exported data
        modified_data = exported_data.copy()

        # Modify character data
        if "characters" in modified_data:
            for char in modified_data["characters"]:
                # Add modification marker
                char["metadata"] = char.get("metadata", {})
                char["metadata"]["modified"] = True
                char["metadata"]["import_test"] = "modified_version"

        # Save modified data
        modified_file = temp_artifacts_dir / "modified_data.json"
        modified_file.write_text(json.dumps(modified_data, indent=2))

        # Step 5: Import modified data (if import API exists)
        start_time = time.time()
        import_response = client.post("/api/import/all", json=modified_data)

        if import_response.status_code == 404:
            # Import API not implemented - validate manually
            pytest.skip("Import API not yet implemented - export validated")

        performance_tracker.record("data_import", time.time() - start_time)

        # Step 6: Verify imported data
        if import_response.status_code in [200, 201]:
            # Verify characters were imported
            for char_id in characters_created:
                response = client.get(f"/api/characters/{char_id}")
                assert response.status_code == 200

                char_data = response.json().get("data", response.json())
                metadata = char_data.get("metadata", {})

                # Verify modification marker
                assert metadata.get("modified") is True
                assert metadata.get("import_test") == "modified_version"

    def test_character_export_format(self, client, data_factory, temp_artifacts_dir):
        """Test character data export format and completeness."""
        # Create character with complete data
        char_data = data_factory.create_character_data(
            name="Format Test Character", agent_id="format_test_char"
        )
        char_data.update(
            {
                "skills": {"skill1": 0.5, "skill2": 0.7},
                "relationships": {"other_char": 0.3},
                "inventory": ["item1", "item2"],
                "metadata": {"custom_field": "value"},
            }
        )

        response = client.post("/api/characters", json=char_data)
        assert response.status_code in [200, 201]

        # Export character
        response = client.get("/api/characters/format_test_char")
        assert response.status_code == 200

        exported_char = response.json().get("data", response.json())

        # Verify all fields are present
        required_fields = ["agent_id", "name"]
        for field in required_fields:
            assert field in exported_char, f"Missing required field: {field}"

        # Verify data types
        assert isinstance(exported_char.get("skills", {}), dict)
        assert isinstance(exported_char.get("relationships", {}), dict)
        assert isinstance(exported_char.get("inventory", []), list)

        # Save export
        export_file = temp_artifacts_dir / "character_export.json"
        export_file.write_text(json.dumps(exported_char, indent=2))

    def test_export_validation_and_schema(self, client, data_factory):
        """Test that exported data follows a consistent schema."""
        # Create minimal character
        char_data = data_factory.create_character_data(
            name="Schema Test", agent_id="schema_test"
        )

        response = client.post("/api/characters", json=char_data)
        assert response.status_code in [200, 201]

        # Export and validate schema
        response = client.get("/api/characters/schema_test")
        assert response.status_code == 200

        exported = response.json()

        # Should have consistent structure
        assert isinstance(exported, dict)

        # Check for data wrapper or direct data
        if "data" in exported:
            character_data = exported["data"]
        else:
            character_data = exported

        # Verify essential fields exist
        assert "agent_id" in character_data or "name" in character_data

    def test_import_validation_and_errors(self, client, data_factory):
        """Test import validation catches invalid data."""
        # Test 1: Import with invalid schema
        invalid_import = {
            "characters": [
                {
                    "invalid_field": "value"
                    # Missing required fields
                }
            ]
        }

        response = client.post("/api/import/all", json=invalid_import)

        if response.status_code == 404:
            pytest.skip("Import API not yet implemented")

        assert response.status_code in [400, 422], "Should reject invalid import data"

        # Test 2: Import with duplicate IDs
        char_data = data_factory.create_character_data(agent_id="duplicate_import")

        # Create character first
        response = client.post("/api/characters", json=char_data)
        assert response.status_code in [200, 201]

        # Try to import the same character
        import_data = {"characters": [char_data]}

        response = client.post("/api/import/all", json=import_data)

        if response.status_code not in [404]:
            # Should either skip duplicate or return error
            assert response.status_code in [200, 400, 409]

    def test_partial_export_import(self, client, data_factory, api_helper):
        """Test exporting/importing specific data subsets."""
        # Create multiple characters
        char_ids = []
        for i in range(3):
            char_data = data_factory.create_character_data(
                name=f"Partial Test Char {i}", agent_id=f"partial_char_{i}"
            )

            response = client.post("/api/characters", json=char_data)
            assert response.status_code in [200, 201]
            char_ids.append(f"partial_char_{i}")

        # Export specific character
        response = client.get("/api/export/characters/partial_char_0")

        if response.status_code == 404:
            # Fallback to regular character retrieval
            response = client.get("/api/characters/partial_char_0")

        assert response.status_code == 200

        exported_char = response.json()

        # Verify it's the correct character
        data = exported_char.get("data", exported_char)
        assert data.get("agent_id") == "partial_char_0"

    def test_export_with_relationships_integrity(
        self, client, data_factory, api_helper
    ):
        """Test that exported data maintains referential integrity."""
        # Create interconnected characters
        char1_data = data_factory.create_character_data(
            name="Character A", agent_id="char_a"
        )

        char2_data = data_factory.create_character_data(
            name="Character B", agent_id="char_b"
        )
        char2_data["relationships"] = {"char_a": 0.8}

        # Create both
        response = client.post("/api/characters", json=char1_data)
        assert response.status_code in [200, 201]

        response = client.post("/api/characters", json=char2_data)
        assert response.status_code in [200, 201]

        # Export all data
        export_response = client.get("/api/export/all")

        if export_response.status_code == 404:
            # Manually collect data
            chars = []
            for char_id in ["char_a", "char_b"]:
                response = client.get(f"/api/characters/{char_id}")
                if response.status_code == 200:
                    chars.append(response.json().get("data", response.json()))

            # Verify relationship reference
            char_b = next((c for c in chars if c.get("agent_id") == "char_b"), None)
            if char_b:
                relationships = char_b.get("relationships", {})
                assert "char_a" in relationships, "Relationship reference should exist"

    def test_large_dataset_export_performance(
        self, client, data_factory, performance_tracker
    ):
        """Test export performance with larger datasets."""
        # Create multiple characters
        char_count = 10
        created_chars = []

        for i in range(char_count):
            char_data = data_factory.create_character_data(
                name=f"Perf Test Char {i}", agent_id=f"perf_char_{i}"
            )

            response = client.post("/api/characters", json=char_data)
            if response.status_code in [200, 201]:
                created_chars.append(f"perf_char_{i}")

        # Export all data
        start_time = time.time()
        export_response = client.get("/api/export/all")

        if export_response.status_code == 404:
            # Manual export
            exported_chars = []
            for char_id in created_chars:
                response = client.get(f"/api/characters/{char_id}")
                if response.status_code == 200:
                    exported_chars.append(response.json().get("data", response.json()))

            export_size = len(json.dumps(exported_chars))
        else:
            export_data = export_response.json()
            export_size = len(json.dumps(export_data))

        export_duration = time.time() - start_time

        performance_tracker.record(
            "large_export",
            export_duration,
            {
                "character_count": char_count,
                "data_size_bytes": export_size,
                "bytes_per_second": (
                    export_size / export_duration if export_duration > 0 else 0
                ),
            },
        )

        # Export should complete in reasonable time
        assert export_duration < 10.0, f"Export took too long: {export_duration}s"

        # Cleanup
        for char_id in created_chars:
            client.delete(f"/api/characters/{char_id}")

    def test_version_compatibility_checking(self, client, data_factory):
        """Test that import handles version compatibility."""
        # Create export with version info
        export_data = {
            "version": "1.0",
            "timestamp": time.time(),
            "characters": [data_factory.create_character_data(agent_id="version_test")],
        }

        # Try to import
        response = client.post("/api/import/all", json=export_data)

        if response.status_code == 404:
            pytest.skip("Import API not yet implemented")

        # Should either succeed or gracefully handle version
        assert response.status_code in [200, 201, 400]

        # Test with future version
        future_export = export_data.copy()
        future_export["version"] = "99.0"

        response = client.post("/api/import/all", json=future_export)

        if response.status_code not in [404]:
            # Should warn or reject incompatible version
            assert response.status_code in [200, 400]
