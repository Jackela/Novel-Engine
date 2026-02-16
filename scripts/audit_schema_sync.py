#!/usr/bin/env python3
"""
Schema Synchronization Audit Script

Compares Pydantic backend schemas (src/api/schemas.py) with Zod frontend schemas
(frontend/src/types/schemas.ts) to identify contract drift.
"""

import re
from pathlib import Path
from typing import Dict, List


def extract_pydantic_schemas(file_path: Path) -> Dict[str, Dict]:
    """Extract Pydantic schema definitions and their fields."""
    content = file_path.read_text()
    schemas = {}

    # Pattern to match class definitions
    class_pattern = re.compile(r"^class (\w+)\(BaseModel\):", re.MULTILINE)

    for match in class_pattern.finditer(content):
        class_name = match.group(1)
        start_pos = match.end()

        # Find the next class definition or end of file
        next_class = class_pattern.search(content, start_pos)
        end_pos = next_class.start() if next_class else len(content)

        class_body = content[start_pos:end_pos]

        # Extract fields from the class body
        fields = {}
        field_pattern = re.compile(
            r"^\s{4}(\w+):\s*(.+?)(?:\s*=\s*Field\((.*?)\))?$", re.MULTILINE
        )

        for field_match in field_pattern.finditer(class_body):
            field_name = field_match.group(1)
            field_type = field_match.group(2).strip()
            field_args = field_match.group(3) or ""

            # Extract validation constraints
            min_val = None
            max_val = None
            description = None

            if "min_length" in field_args or "ge=" in field_args:
                min_match = re.search(r"(?:min_length|ge)\s*=\s*(\d+)", field_args)
                if min_match:
                    min_val = int(min_match.group(1))

            if "max_length" in field_args or "le=" in field_args:
                max_match = re.search(r"(?:max_length|le)\s*=\s*(\d+)", field_args)
                if max_match:
                    max_val = int(max_match.group(1))

            if "description=" in field_args:
                desc_match = re.search(r'description\s*=\s*"([^"]*)"', field_args)
                if desc_match:
                    description = desc_match.group(1)

            fields[field_name] = {
                "type": field_type,
                "min": min_val,
                "max": max_val,
                "description": description,
            }

        schemas[class_name] = {"fields": fields}

    return schemas


def extract_zod_schemas(file_path: Path) -> Dict[str, Dict]:
    """Extract Zod schema definitions and their fields."""
    content = file_path.read_text()
    schemas = {}

    # Pattern to match Zod schema exports
    schema_pattern = re.compile(
        r"export\s+const\s+(\w+Schema)\s*=\s*z\.object\(\{", re.MULTILINE
    )

    for match in schema_pattern.finditer(content):
        schema_name = match.group(1).replace("Schema", "")
        start_pos = match.end()

        # Find matching closing brace (rough approximation)
        brace_count = 1
        end_pos = start_pos
        while end_pos < len(content) and brace_count > 0:
            if content[end_pos] == "{":
                brace_count += 1
            elif content[end_pos] == "}":
                brace_count -= 1
            end_pos += 1

        schema_body = content[start_pos : end_pos - 1]

        # Extract fields from the schema body
        fields = {}
        field_pattern = re.compile(
            r"(\w+):\s*z\.\w+\((.*?)\)(?:\.\s*\w+\((.*?)\))*", re.MULTILINE
        )

        for field_match in field_pattern.finditer(schema_body):
            field_name = field_match.group(1)
            zod_args = field_match.group(2) + " " + (field_match.group(3) or "")

            # Extract validation constraints
            min_val = None
            max_val = None

            # Match min(), max(), min_length(), max_length()
            min_match = re.search(r"\.(?:min|min_length)\((\d+)\)", zod_args)
            if min_match:
                min_val = int(min_match.group(1))

            max_match = re.search(r"\.(?:max|max_length)\((\d+)\)", zod_args)
            if max_match:
                max_val = int(max_match.group(1))

            # Extract type info
            zod_type = "unknown"
            if "z.string()" in zod_args or "z.string." in zod_args:
                zod_type = "string"
            elif "z.number()" in zod_args or "z.number." in zod_args:
                zod_type = "number"
            elif "z.boolean()" in zod_args:
                zod_type = "boolean"
            elif "z.array(" in zod_args:
                zod_type = "array"
            elif "z.record(" in zod_args:
                zod_type = "record"
            elif "z.object(" in zod_args:
                zod_type = "object"
            elif "z.enum(" in zod_args:
                zod_type = "enum"

            fields[field_name] = {
                "type": zod_type,
                "min": min_val,
                "max": max_val,
            }

        schemas[schema_name] = {"fields": fields}

    return schemas


def compare_schemas(pydantic_schemas: Dict, zod_schemas: Dict) -> List[Dict]:
    """Compare Pydantic and Zod schemas and identify discrepancies."""
    discrepancies = []

    # Check for schemas in Pydantic but not in Zod
    pydantic_names = set(pydantic_schemas.keys())
    zod_names = set(zod_schemas.keys())

    missing_in_zod = pydantic_names - zod_names
    for name in sorted(missing_in_zod):
        discrepancies.append(
            {
                "severity": "HIGH",
                "schema": name,
                "issue": "Missing in frontend",
                "details": "Schema exists in backend but not in frontend",
            }
        )

    # Check for schemas in Zod but not in Pydantic
    missing_in_pydantic = zod_names - pydantic_names
    for name in sorted(missing_in_pydantic):
        discrepancies.append(
            {
                "severity": "MEDIUM",
                "schema": name,
                "issue": "Missing in backend",
                "details": "Schema exists in frontend but not in backend",
            }
        )

    # Compare field-level constraints for common schemas
    common_names = pydantic_names & zod_names
    for name in sorted(common_names):
        pydantic_fields = pydantic_schemas[name]["fields"]
        zod_fields = zod_schemas[name]["fields"]

        # Check for missing fields
        pydantic_field_names = set(pydantic_fields.keys())
        zod_field_names = set(zod_fields.keys())

        missing_in_zod_fields = pydantic_field_names - zod_field_names
        for field in sorted(missing_in_zod_fields):
            discrepancies.append(
                {
                    "severity": "HIGH",
                    "schema": name,
                    "issue": "Field missing in frontend",
                    "details": f"Field '{field}' exists in backend but not in frontend",
                }
            )

        missing_in_pydantic_fields = zod_field_names - pydantic_field_names
        for field in sorted(missing_in_pydantic_fields):
            discrepancies.append(
                {
                    "severity": "MEDIUM",
                    "schema": name,
                    "issue": "Field missing in backend",
                    "details": f"Field '{field}' exists in frontend but not in backend",
                }
            )

        # Check constraint mismatches for common fields
        common_fields = pydantic_field_names & zod_field_names
        for field in sorted(common_fields):
            pydantic_field = pydantic_fields[field]
            zod_field = zod_fields[field]

            # Check min constraints
            if (
                pydantic_field.get("min") is not None
                and zod_field.get("min") is not None
            ):
                if pydantic_field["min"] != zod_field["min"]:
                    discrepancies.append(
                        {
                            "severity": "CRITICAL",
                            "schema": name,
                            "issue": "Min constraint mismatch",
                            "details": f"Field '{field}': backend min={pydantic_field['min']}, frontend min={zod_field['min']}",
                        }
                    )

            # Check max constraints
            if (
                pydantic_field.get("max") is not None
                and zod_field.get("max") is not None
            ):
                if pydantic_field["max"] != zod_field["max"]:
                    discrepancies.append(
                        {
                            "severity": "CRITICAL",
                            "schema": name,
                            "issue": "Max constraint mismatch",
                            "details": f"Field '{field}': backend max={pydantic_field['max']}, frontend max={zod_field['max']}",
                        }
                    )

            # Check type mismatches
            if pydantic_field.get("type") and zod_field.get("type"):
                pydantic_type = pydantic_field["type"].lower()
                zod_type = zod_field["type"]

                # Normalize type names for comparison
                type_map = {
                    "str": "string",
                    "int": "number",
                    "float": "number",
                    "bool": "boolean",
                    "list": "array",
                    "dict": "record",
                }

                for py_type, norm_type in type_map.items():
                    if py_type in pydantic_type:
                        pydantic_type = norm_type
                        break

                if pydantic_type != zod_type and not (
                    "optional" in pydantic_type
                    or "nullable" in pydantic_type
                    or "union" in pydantic_type
                    or "optional" in str(zod_field)
                ):
                    discrepancies.append(
                        {
                            "severity": "CRITICAL",
                            "schema": name,
                            "issue": "Type mismatch",
                            "details": f"Field '{field}': backend type={pydantic_field['type']}, frontend type={zod_field['type']}",
                        }
                    )

    return discrepancies


def main():
    """Run the schema synchronization audit."""
    project_root = Path(__file__).parent.parent
    pydantic_file = project_root / "src" / "api" / "schemas.py"
    zod_file = project_root / "frontend" / "src" / "types" / "schemas.ts"

    print("=" * 80)
    print("SCHEMA SYNCHRONIZATION AUDIT")
    print("=" * 80)
    print()

    print(f"Backend schemas:  {pydantic_file}")
    print(f"Frontend schemas: {zod_file}")
    print()

    # Extract schemas
    print("Extracting Pydantic schemas...")
    pydantic_schemas = extract_pydantic_schemas(pydantic_file)
    print(f"  Found {len(pydantic_schemas)} Pydantic schemas")

    print("Extracting Zod schemas...")
    zod_schemas = extract_zod_schemas(zod_file)
    print(f"  Found {len(zod_schemas)} Zod schemas")
    print()

    # Compare schemas
    print("Comparing schemas...")
    discrepancies = compare_schemas(pydantic_schemas, zod_schemas)

    # Initialize by_severity at function scope for use in both printing and report
    by_severity: Dict[str, List[Dict]] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}

    if not discrepancies:
        print("  No discrepancies found! Schemas are synchronized.")
    else:
        print(f"  Found {len(discrepancies)} discrepancies")
        print()

        # Group by severity
        for d in discrepancies:
            by_severity[d["severity"]].append(d)

        # Print discrepancies
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            items = by_severity[severity]
            if items:
                print(f"\n{severity} ISSUES ({len(items)}):")
                print("-" * 80)
                for item in items:
                    print(f"  Schema: {item['schema']}")
                    print(f"  Issue:  {item['issue']}")
                    print(f"  Details: {item['details']}")
                    print()

    # Generate report file
    report_path = project_root / "docs" / "api" / "schema-drift-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        f.write("# Schema Drift Report\n\n")
        f.write(f"**Generated:** {Path(__file__).stat().st_mtime}\n\n")
        f.write(f"**Backend Schemas:** {len(pydantic_schemas)}\n")
        f.write(f"**Frontend Schemas:** {len(zod_schemas)}\n")
        f.write(f"**Discrepancies Found:** {len(discrepancies)}\n\n")

        if discrepancies:
            # Reuse already populated by_severity (populated above)
            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                items = by_severity[severity]
                if items:
                    f.write(f"## {severity} Issues ({len(items)})\n\n")
                    for item in items:
                        f.write(f"### Schema: {item['schema']}\n\n")
                        f.write(f"- **Issue:** {item['issue']}\n")
                        f.write(f"- **Details:** {item['details']}\n\n")

    print(f"\nReport saved to: {report_path}")

    # Exit with error code if critical issues found
    critical_count = len(by_severity.get("CRITICAL", []))
    if critical_count > 0:
        print(f"\n❌ Found {critical_count} CRITICAL issues that must be fixed!")
        return 1
    elif discrepancies:
        print(
            f"\n⚠️  Found {len(discrepancies)} non-critical issues that should be reviewed."
        )
        return 0
    else:
        print("\n✅ All schemas are synchronized!")
        return 0


if __name__ == "__main__":
    exit(main())
