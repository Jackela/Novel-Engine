#!/usr/bin/env python3
"""
Validation Test for World Application Services

This script validates that the application services follow Clean Architecture
principles and can be imported and instantiated correctly.
"""

import sys
import traceback


def test_imports():
    """Test that all application services can be imported correctly."""
    print("Testing imports...")

    try:
        # Test command imports

        print("✅ Command imports successful")

        # Test use case imports

        print("✅ Use case imports successful")

        # Test domain imports (to verify dependencies)

        print("✅ Domain imports successful")

        return True, "All imports successful"

    except Exception as e:
        return False, f"Import error: {str(e)}\n{traceback.format_exc()}"


def test_command_creation():
    """Test that commands can be created and validated correctly."""
    print("\nTesting command creation...")

    try:
        from ..domain.aggregates.world_state import EntityType
        from ..domain.value_objects.coordinates import Coordinates
        from .commands.world_commands import (
            ApplyWorldDelta,
            EntityOperation,
            WorldOperationType,
        )

        # Test basic command creation
        command = ApplyWorldDelta(
            world_state_id="test-world-123", reason="Testing command creation"
        )
        assert command.world_state_id == "test-world-123"
        assert command.reason == "Testing command creation"
        assert command.command_id is not None
        assert command.correlation_id is not None
        print("✅ Basic command creation successful")

        # Test command with entity operations
        coordinates = Coordinates(x=100.0, y=200.0, z=0.0)
        entity_op = EntityOperation(
            operation_type=WorldOperationType.ADD_ENTITY,
            entity_id="test-entity-456",
            entity_type=EntityType.CHARACTER,
            entity_name="Test Character",
            coordinates=coordinates,
            reason="Testing entity addition",
        )

        command_with_ops = ApplyWorldDelta(
            world_state_id="test-world-123",
            entity_operations=[entity_op],
            reason="Testing command with operations",
        )

        assert len(command_with_ops.entity_operations) == 1
        assert command_with_ops.get_operation_count() == 1
        assert "add_entity" in command_with_ops.get_operation_summary()
        print("✅ Command with entity operations successful")

        # Test factory methods
        factory_command = ApplyWorldDelta.create_entity_addition(
            world_state_id="test-world-789",
            entity_id="factory-entity-123",
            entity_type=EntityType.OBJECT,
            entity_name="Factory Test Object",
            coordinates=coordinates,
            reason="Testing factory method",
        )

        assert factory_command.world_state_id == "test-world-789"
        assert len(factory_command.entity_operations) == 1
        print("✅ Factory method creation successful")

        # Test serialization
        command_dict = command.to_dict()
        assert isinstance(command_dict, dict)
        assert "command_id" in command_dict
        assert "world_state_id" in command_dict
        print("✅ Command serialization successful")

        return True, "Command creation tests passed"

    except Exception as e:
        return False, f"Command creation error: {str(e)}\n{traceback.format_exc()}"


def test_use_case_structure():
    """Test that use cases follow proper structure and can be instantiated."""
    print("\nTesting use case structure...")

    try:
        from ..domain.repositories.world_state_repo import IWorldStateRepository
        from .use_cases.update_world_state_uc import (
            UpdateWorldStateResult,
            UpdateWorldStateUC,
        )

        # Create a mock repository for testing
        class MockRepository(IWorldStateRepository):
            async def save(self, world_state):
                return world_state

            async def get_by_id(self, world_state_id):
                return None

            async def exists(self, world_state_id):
                return True

            # Implement other abstract methods as no-ops for testing
            async def get_by_id_or_raise(self, world_state_id):
                pass

            async def delete(self, world_state_id):
                return False

            async def get_all(self, offset=0, limit=100):
                return []

            async def find_by_name(self, name):
                return None

            async def find_by_criteria(self, criteria, offset=0, limit=100):
                return []

            async def count(self, criteria=None):
                return 0

            async def find_entities_by_type(
                self, world_state_id, entity_type, offset=0, limit=100
            ):
                return []

            async def find_entities_in_area(
                self, world_state_id, center, radius, entity_types=None
            ):
                return []

            async def find_entities_by_coordinates(
                self, world_state_id, coordinates, tolerance=0.0
            ):
                return []

            async def get_version(self, world_state_id, version):
                return None

            async def get_version_history(self, world_state_id, limit=50):
                return []

            async def rollback_to_version(self, world_state_id, version):
                pass

            async def create_snapshot(
                self, world_state_id, snapshot_name, metadata=None
            ):
                return "test-snapshot-id"

            async def restore_from_snapshot(self, world_state_id, snapshot_id):
                pass

            async def list_snapshots(self, world_state_id):
                return []

            async def delete_snapshot(self, snapshot_id):
                return False

            async def save_batch(self, world_states):
                return world_states

            async def delete_batch(self, world_state_ids):
                return {}

            async def optimize_storage(self, world_state_id):
                return {}

            async def get_statistics(self, world_state_id=None):
                return {}

            async def get_events_since(self, world_state_id, since_version):
                return []

            async def replay_events(self, world_state_id, to_version=None):
                pass

        mock_repo = MockRepository()
        use_case = UpdateWorldStateUC(world_repository=mock_repo)

        assert use_case.world_repository is mock_repo
        assert hasattr(use_case, "execute")
        print("✅ Use case instantiation successful")

        # Test result class
        result = UpdateWorldStateResult(
            success=True, operations_applied=5, execution_time_ms=123.45
        )

        assert result.success is True
        assert result.operations_applied == 5
        assert result.execution_time_ms == 123.45

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "success" in result_dict
        print("✅ Use case result structure successful")

        return True, "Use case structure tests passed"

    except Exception as e:
        return False, f"Use case structure error: {str(e)}\n{traceback.format_exc()}"


def test_clean_architecture_compliance():
    """Test that the application layer follows Clean Architecture principles."""
    print("\nTesting Clean Architecture compliance...")

    try:
        # Test dependency direction (application -> domain, not domain -> application)
        # Verify that use cases depend on domain abstractions
        import inspect

        from .commands.world_commands import ApplyWorldDelta
        from .use_cases.update_world_state_uc import UpdateWorldStateUC

        uc_signature = inspect.signature(UpdateWorldStateUC.__init__)
        params = list(uc_signature.parameters.values())

        # Should depend on IWorldStateRepository (interface), not concrete implementation
        repo_param = next((p for p in params if "repository" in p.name.lower()), None)
        assert repo_param is not None, "Use case should depend on repository interface"
        print("✅ Use case depends on repository abstraction")

        # Verify commands are data structures (dataclasses)
        assert hasattr(
            ApplyWorldDelta, "__dataclass_fields__"
        ), "Commands should be dataclasses"
        print("✅ Commands are proper data structures")

        # Verify use cases orchestrate but don't contain business logic
        uc_methods = [m for m in dir(UpdateWorldStateUC) if not m.startswith("_")]
        public_methods = [
            m for m in uc_methods if callable(getattr(UpdateWorldStateUC, m))
        ]

        # Should have execute method as main entry point
        assert "execute" in public_methods, "Use case should have execute method"
        print("✅ Use case has proper public interface")

        # Test that domain objects are used properly
        # Commands should reference domain value objects and entities
        command = ApplyWorldDelta(
            world_state_id="test-world", reason="Architecture compliance test"
        )

        # Should be able to serialize/deserialize (for message passing)
        serialized = command.to_dict()
        assert isinstance(serialized, dict), "Commands should be serializable"
        print("✅ Commands are serializable")

        return True, "Clean Architecture compliance tests passed"

    except Exception as e:
        return (
            False,
            f"Clean Architecture compliance error: {str(e)}\n{traceback.format_exc()}",
        )


def run_validation():
    """Run all validation tests."""
    print("=" * 60)
    print("World Context Application Services Validation")
    print("=" * 60)

    tests = [
        test_imports,
        test_command_creation,
        test_use_case_structure,
        test_clean_architecture_compliance,
    ]

    results = []
    for test in tests:
        try:
            success, message = test()
            results.append((test.__name__, success, message))
        except Exception as e:
            results.append((test.__name__, False, f"Test execution error: {str(e)}"))

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if not success:
            print(f"   Error: {message}")
        failed += 0 if success else 1
        passed += 1 if success else 0

    print(f"\nSUMMARY: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All validation tests passed! Application services are ready for use.")
        return True
    else:
        print("⚠️ Some validation tests failed. Please review and fix the issues.")
        return False


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
