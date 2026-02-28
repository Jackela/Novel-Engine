## No Spec Changes Required

This is a pure refactoring change that modifies only internal code organization. No new capabilities are being added and no existing behavior is being modified.

### Requirement: Backward Compatibility Preserved

All existing imports SHALL continue to work after the refactoring.

#### Scenario: Import from schemas package
- **WHEN** code imports a schema using `from src.api.schemas import SchemaName`
- **THEN** the import succeeds without modification

#### Scenario: All schemas accessible
- **WHEN** any existing schema is referenced
- **THEN** it is available at the same import path as before
