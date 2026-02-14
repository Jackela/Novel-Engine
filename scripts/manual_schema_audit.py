#!/usr/bin/env python3
"""
Manual Schema Synchronization Audit

Compares backend Pydantic schemas with frontend Zod schemas to identify:
1. Missing schemas
2. Field mismatches
3. Constraint differences
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def extract_class_names(file_path: Path) -> Set[str]:
    """Extract all Pydantic BaseModel class names."""
    content = file_path.read_text()
    pattern = r"^class (\w+)\(BaseModel\):"
    return set(re.findall(pattern, content, re.MULTILINE))


def extract_zod_schema_names(file_path: Path) -> Set[str]:
    """Extract all Zod schema names (without 'Schema' suffix)."""
    content = file_path.read_text()
    # Match patterns like: export const CharacterSchema = z.object({...})
    pattern = r"export const (\w+?)Schema\s*=\s*z\.object\("
    matches = set(re.findall(pattern, content))

    # Also match inline schemas like: InlineCharacterSchema
    inline_pattern = r"const (\w+?)Schema\s*=\s*z\.object\("
    matches.update(re.findall(inline_pattern, content))

    return matches


def get_schema_fields_pydantic(file_path: Path, class_name: str) -> Dict[str, str]:
    """Extract field names and types from a Pydantic class."""
    content = file_path.read_text()
    pattern = rf"^class {class_name}\(BaseModel\):.*?(?=^class |\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

    if not match:
        return {}

    class_body = match.group(0)
    # Extract field definitions (indented by 4 spaces)
    field_pattern = r"^    (\w+):\s*(.+?)(?:\s*=\s*Field\(|$)"
    fields = {}

    for field_match in re.finditer(field_pattern, class_body, re.MULTILINE):
        field_name = field_match.group(1)
        field_type = field_match.group(2).strip()
        # Clean up the type annotation
        field_type = re.sub(r"\s*=.*", "", field_type).strip()
        fields[field_name] = field_type

    return fields


def get_schema_fields_zod(file_path: Path, schema_name: str) -> Dict[str, str]:
    """Extract field names from a Zod schema."""
    content = file_path.read_text()
    # Look for the schema definition
    pattern = rf"export const {schema_name}Schema\s*=\s*z\.object\(\{{(.*?)\}}\)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        # Try inline schema
        pattern = rf"const {schema_name}Schema\s*=\s*z\.object\(\{{(.*?)\}}\)"
        match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {}

    schema_body = match.group(1)
    # Extract field names
    field_pattern = r"(\w+):\s*z\."
    fields = {}

    for field_match in re.finditer(field_pattern, schema_body):
        field_name = field_match.group(1)
        # Determine basic type from zod calls
        type_pattern = rf"{field_name}:\s*z\.(\w+)"
        type_match = re.search(type_pattern, schema_body)
        if type_match:
            zod_type = type_match.group(1)
            # Map zod types to Python types
            type_map = {
                "string": "str",
                "number": "int | float",
                "int": "int",
                "boolean": "bool",
                "array": "List",
                "object": "Dict",
                "record": "Dict",
                "enum": "Enum",
                "unknown": "Any",
            }
            fields[field_name] = type_map.get(zod_type, zod_type)
        else:
            fields[field_name] = "unknown"

    return fields


def compare_field_types(pydantic_type: str, zod_type: str) -> Tuple[bool, str]:
    """Compare field types and return (is_compatible, reason)."""
    # Normalize types
    py_type = (
        pydantic_type.lower().replace("optional", "").replace("list", "array").strip()
    )
    zd_type = zod_type.lower()

    # Handle type mappings
    if "str" in py_type and zd_type == "str":
        return True, ""
    if "int" in py_type and zd_type in ["int", "number"]:
        return True, ""
    if "float" in py_type and zd_type == "number":
        return True, ""
    if "bool" in py_type and zd_type == "bool":
        return True, ""
    if "list" in py_type or "array" in py_type.lower():
        if "array" in zd_type or "list" in zd_type:
            return True, ""
    if "dict" in py_type.lower() and ("record" in zd_type or "dict" in zd_type):
        return True, ""

    return False, f"Type mismatch: backend={pydantic_type}, frontend={zod_type}"


def main():
    """Run the manual schema audit."""
    project_root = Path(__file__).parent.parent
    pydantic_file = project_root / "src" / "api" / "schemas.py"
    zod_file = project_root / "frontend" / "src" / "types" / "schemas.ts"
    report_file = project_root / "docs" / "api" / "schema-drift-report.md"

    print("=" * 80)
    print("MANUAL SCHEMA SYNCHRONIZATION AUDIT")
    print("=" * 80)
    print()

    # Extract schema names
    pydantic_classes = extract_class_names(pydantic_file)
    zod_schemas = extract_zod_schema_names(zod_file)

    print(f"Backend Pydantic schemas:  {len(pydantic_classes)}")
    print(f"Frontend Zod schemas:      {len(zod_schemas)}")
    print()

    # Normalize names (remove Response/Request suffixes for comparison)
    def normalize_name(name: str) -> str:
        return re.sub(r"(Response|Request|Update|Create|Data)$", "", name)

    pydantic_normalized = {normalize_name(name): name for name in pydantic_classes}
    zod_normalized = {normalize_name(name): name for name in zod_schemas}

    # Find missing schemas
    missing_in_frontend = set(pydantic_normalized.keys()) - set(zod_normalized.keys())
    missing_in_backend = set(zod_normalized.keys()) - set(pydantic_normalized.keys())

    # Start report
    report_lines = [
        "# Schema Synchronization Audit Report\n",
        f"**Generated:** 2026-02-03",
        f"**Backend Schemas:** {len(pydantic_classes)}",
        f"**Frontend Schemas:** {len(zod_schemas)}",
        "",
        "## Summary\n",
    ]

    if not missing_in_frontend and not missing_in_backend:
        report_lines.append(
            "✅ **All schemas are synchronized between backend and frontend.**\n"
        )
    else:
        if missing_in_frontend:
            report_lines.append(
                f"### Missing in Frontend ({len(missing_in_frontend)})\n"
            )
            report_lines.append(
                "The following backend schemas have no corresponding frontend schema:\n"
            )
            for name in sorted(missing_in_frontend):
                original_name = pydantic_normalized[name]
                report_lines.append(f"- `{original_name}`\n")
            report_lines.append("\n")

        if missing_in_backend:
            report_lines.append(f"### Missing in Backend ({len(missing_in_backend)})\n")
            report_lines.append(
                "The following frontend schemas have no corresponding backend schema:\n"
            )
            for name in sorted(missing_in_backend):
                original_name = zod_normalized[name]
                report_lines.append(f"- `{original_name}`\n")
            report_lines.append("\n")

    # Check common schemas for field mismatches
    common_names = set(pydantic_normalized.keys()) & set(zod_normalized.keys())
    field_mismatches = []

    for normalized_name in sorted(common_names):
        pydantic_name = pydantic_normalized[normalized_name]
        zod_name = zod_normalized[normalized_name]

        pydantic_fields = get_schema_fields_pydantic(pydantic_file, pydantic_name)
        zod_fields = get_schema_fields_zod(zod_file, zod_name)

        if not pydantic_fields or not zod_fields:
            continue

        # Check for missing fields
        missing_in_zod = set(pydantic_fields.keys()) - set(zod_fields.keys())
        if missing_in_zod:
            field_mismatches.append(
                {
                    "schema": pydantic_name,
                    "severity": "HIGH",
                    "issue": "Fields missing in frontend",
                    "fields": list(missing_in_zod),
                }
            )

        missing_in_pydantic = set(zod_fields.keys()) - set(pydantic_fields.keys())
        if missing_in_pydantic:
            field_mismatches.append(
                {
                    "schema": pydantic_name,
                    "severity": "MEDIUM",
                    "issue": "Fields missing in backend",
                    "fields": list(missing_in_pydantic),
                }
            )

        # Check type mismatches for common fields
        common_fields = set(pydantic_fields.keys()) & set(zod_fields.keys())
        for field in common_fields:
            is_compatible, reason = compare_field_types(
                pydantic_fields[field], zod_fields[field]
            )
            if not is_compatible:
                field_mismatches.append(
                    {
                        "schema": pydantic_name,
                        "severity": "CRITICAL",
                        "issue": f"Type mismatch in field '{field}'",
                        "fields": [reason],
                    }
                )

    # Add field mismatches to report
    if field_mismatches:
        report_lines.append("\n## Field-Level Mismatches\n")

        # Group by severity
        by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": []}
        for mismatch in field_mismatches:
            by_severity[mismatch["severity"]].append(mismatch)

        for severity in ["CRITICAL", "HIGH", "MEDIUM"]:
            items = by_severity[severity]
            if items:
                report_lines.append(f"\n### {severity} Issues ({len(items)})\n")
                for item in items:
                    report_lines.append(f"#### `{item['schema']}`\n")
                    report_lines.append(f"- **Issue:** {item['issue']}\n")
                    for field in item["fields"]:
                        report_lines.append(f"  - {field}\n")
                    report_lines.append("\n")
    else:
        report_lines.append("\n## Field-Level Comparison\n")
        report_lines.append("✅ **No field mismatches found in common schemas.**\n")

    # Add recommendations
    report_lines.extend(
        [
            "\n## Recommendations\n",
            "\n### Priority Actions\n",
            "1. **Regenerate Frontend Schemas**: Run `python scripts/generate_openapi.py` and use the output to update `frontend/src/types/schemas.ts`\n",
            '2. **Add Missing Frontend Schemas**: Create Zod schemas for all backend schemas marked as "Missing in Frontend"\n',
            "3. **Fix Critical Type Mismatches**: Align field types between Pydantic and Zod schemas\n",
            '4. **Remove Unused Frontend Schemas**: Review schemas marked as "Missing in Backend" and remove if not needed\n',
            "\n### Process\n",
            "1. Update backend schema in `src/api/schemas.py`\n",
            "2. Run `python scripts/generate_openapi.py` to regenerate OpenAPI spec\n",
            "3. Use the OpenAPI spec to update `frontend/src/types/schemas.ts` (or use automation tools)\n",
            "4. Run `npm run type-check` to verify alignment\n",
            "\n### Verification\n",
            "Run these commands to verify schema synchronization:\n",
            "```bash\n",
            "# Backend\n",
            "python scripts/generate_openapi.py\n",
            "\n",
            "# Frontend\n",
            "npm run type-check\n",
            "npm run lint:all\n",
            "```\n",
        ]
    )

    # Write report
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("".join(report_lines))

    print("✅ Audit complete!")
    print(f"\n📄 Report saved to: {report_file}")

    # Print summary
    print(f"\n📊 Summary:")
    print(f"  Missing in frontend: {len(missing_in_frontend)}")
    print(f"  Missing in backend:  {len(missing_in_backend)}")
    print(f"  Field mismatches:    {len(field_mismatches)}")

    critical_count = len([m for m in field_mismatches if m["severity"] == "CRITICAL"])
    if critical_count > 0:
        print(f"\n❌ Found {critical_count} CRITICAL issues that must be fixed!")
        return 1
    elif missing_in_frontend or field_mismatches:
        print(f"\n⚠️  Found issues that should be reviewed.")
        return 0
    else:
        print(f"\n✅ All schemas are synchronized!")
        return 0


if __name__ == "__main__":
    exit(main())
