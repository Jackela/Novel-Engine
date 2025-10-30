#!/usr/bin/env python3
"""
Print to Logging Migration Script for Novel-Engine.

This script automatically migrates print() statements to proper Python logging.
It analyzes context to determine appropriate logging levels and preserves
formatting while ensuring proper logging infrastructure is in place.

Features:
- Intelligent logging level detection based on context
- Automatic import and logger setup
- Dry-run mode for safe preview
- Detailed migration report
- Preserves f-strings and formatting
- Handles edge cases and special contexts

Usage:
    python scripts/migrate_print_to_logging.py --dry-run  # Preview changes
    python scripts/migrate_print_to_logging.py            # Apply changes
    python scripts/migrate_print_to_logging.py --file src/core/types.py  # Single file
"""

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class PrintStatement:
    """Represents a print() statement found in code."""

    line_number: int
    content: str
    indentation: str
    suggested_level: str
    reason: str


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""

    file_path: Path
    has_logging_import: bool
    has_logger_setup: bool
    print_statements: List[PrintStatement] = field(default_factory=list)
    import_section_end: int = 0
    first_code_line: int = 0


@dataclass
class MigrationReport:
    """Overall migration report."""

    files_analyzed: int = 0
    files_modified: int = 0
    print_statements_found: int = 0
    print_statements_migrated: int = 0
    errors: List[str] = field(default_factory=list)
    level_distribution: Dict[str, int] = field(
        default_factory=lambda: {"debug": 0, "info": 0, "warning": 0, "error": 0}
    )


class PrintToLoggingMigrator:
    """Migrates print() statements to logging calls."""

    # Patterns for detecting logging levels
    ERROR_PATTERNS = [
        r"error",
        r"exception",
        r"fail(ed)?",
        r"critical",
        r"fatal",
        r"❌",
        r"FAILED",
        r"ERROR",
    ]

    WARNING_PATTERNS = [
        r"warn(ing)?",
        r"caution",
        r"deprecat",
        r"⚠️",
        r"WARNING",
    ]

    INFO_PATTERNS = [
        r"start(ing|ed)?",
        r"running",
        r"complet(ed|ing)",
        r"finish(ed)?",
        r"success",
        r"✅",
        r"🚀",
        r"📋",
        r"📊",
        r"PASSED",
        r"TESTING",
        r"Summary",
    ]

    DEBUG_PATTERNS = [
        r"debug",
        r"verbose",
        r"trace",
        r"detail",
    ]

    def __init__(self, src_dir: Path, dry_run: bool = False):
        """
        Initialize the migrator.

        Args:
            src_dir: Source directory to process
            dry_run: If True, only preview changes without modifying files
        """
        self.src_dir = src_dir
        self.dry_run = dry_run
        self.report = MigrationReport()

    def find_python_files(self, single_file: Optional[Path] = None) -> List[Path]:
        """
        Find all Python files to process.

        Args:
            single_file: If provided, process only this file

        Returns:
            List of Python file paths
        """
        if single_file:
            if single_file.suffix == ".py":
                return [single_file]
            return []

        python_files = []
        for root, _, files in os.walk(self.src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)
        return python_files

    def analyze_file(self, file_path: Path) -> Optional[FileAnalysis]:
        """
        Analyze a Python file for print statements and logging setup.

        Args:
            file_path: Path to the Python file

        Returns:
            FileAnalysis object or None if file cannot be read
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            self.report.errors.append(f"Error reading {file_path}: {e}")
            return None

        analysis = FileAnalysis(
            file_path=file_path,
            has_logging_import=False,
            has_logger_setup=False,
        )

        # Check for existing logging infrastructure
        in_imports = True
        import_end = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track import section
            if stripped and not stripped.startswith("#"):
                if not (
                    stripped.startswith("import ")
                    or stripped.startswith("from ")
                    or stripped.startswith('"""')
                    or stripped.startswith("'''")
                ):
                    if in_imports:
                        import_end = i - 1
                        in_imports = False
                        analysis.first_code_line = i

            # Check for logging import
            if re.match(r"^import\s+logging\b", stripped) or re.match(
                r"^from\s+logging\s+import", stripped
            ):
                analysis.has_logging_import = True

            # Check for logger setup
            if re.match(r"^logger\s*=\s*logging\.getLogger", stripped):
                analysis.has_logger_setup = True

            # Find print statements
            if "print(" in line:
                # Extract indentation
                indentation = line[: len(line) - len(line.lstrip())]

                # Determine logging level
                level, reason = self._determine_logging_level(line)

                print_stmt = PrintStatement(
                    line_number=i,
                    content=line.rstrip(),
                    indentation=indentation,
                    suggested_level=level,
                    reason=reason,
                )
                analysis.print_statements.append(print_stmt)

        analysis.import_section_end = import_end if import_end > 0 else 10

        return analysis

    def _determine_logging_level(self, line: str) -> Tuple[str, str]:
        """
        Determine appropriate logging level based on line content.

        Args:
            line: Line containing print statement

        Returns:
            Tuple of (level, reason)
        """
        line_lower = line.lower()

        # Check for error patterns
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return "error", f"Contains error indicator: {pattern}"

        # Check for warning patterns
        for pattern in self.WARNING_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return "warning", f"Contains warning indicator: {pattern}"

        # Check for info patterns
        for pattern in self.INFO_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return "info", f"Contains info indicator: {pattern}"

        # Check for debug patterns
        for pattern in self.DEBUG_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return "debug", f"Contains debug indicator: {pattern}"

        # Default to info for general output
        return "info", "Default level for general output"

    def _convert_print_to_logging(self, print_stmt: PrintStatement) -> str:
        """
        Convert a print statement to logging call.

        Args:
            print_stmt: PrintStatement to convert

        Returns:
            Converted logging statement
        """
        content = print_stmt.content.strip()

        # Extract the content inside print()
        match = re.match(r"print\((.*)\)\s*$", content)
        if not match:
            return content  # Can't parse, return as-is

        print_args = match.group(1)

        # Handle f-strings, regular strings, and expressions
        # Keep the formatting intact
        level = print_stmt.suggested_level
        new_line = f"{print_stmt.indentation}logger.{level}({print_args})"

        return new_line

    def migrate_file(self, analysis: FileAnalysis) -> bool:
        """
        Migrate a single file from print to logging.

        Args:
            analysis: FileAnalysis object with migration details

        Returns:
            True if file was modified, False otherwise
        """
        if not analysis.print_statements:
            return False

        try:
            with open(analysis.file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            self.report.errors.append(f"Error reading {analysis.file_path}: {e}")
            return False

        # Track modifications
        modified = False
        lines_to_insert = []

        # Add logging import if needed
        if not analysis.has_logging_import:
            insert_pos = analysis.import_section_end
            if insert_pos == 0:
                # Find first non-docstring, non-shebang line
                insert_pos = 0
                for i, line in enumerate(lines):
                    if (
                        not line.strip().startswith("#")
                        and not line.strip().startswith('"""')
                        and not line.strip().startswith("'''")
                        and line.strip()
                    ):
                        insert_pos = i
                        break

            lines_to_insert.append((insert_pos, "import logging\n"))
            modified = True

        # Add logger setup if needed
        if not analysis.has_logger_setup:
            # Find position after imports
            logger_pos = analysis.import_section_end + 1

            # Add blank line before logger if not present
            logger_lines = ["\n", "logger = logging.getLogger(__name__)\n"]
            for i, logger_line in enumerate(logger_lines):
                lines_to_insert.append((logger_pos + i, logger_line))
            modified = True

        # Sort insert positions in reverse to maintain line numbers
        lines_to_insert.sort(reverse=True)

        # Insert new lines
        for pos, line in lines_to_insert:
            if pos < len(lines):
                lines.insert(pos, line)
            else:
                lines.append(line)

        # Replace print statements
        for print_stmt in analysis.print_statements:
            # Account for inserted lines
            offset = sum(
                1 for pos, _ in lines_to_insert if pos < print_stmt.line_number
            )
            actual_line_num = print_stmt.line_number - 1 + offset

            if actual_line_num < len(lines):
                new_line = self._convert_print_to_logging(print_stmt)
                lines[actual_line_num] = new_line + "\n"
                modified = True
                self.report.level_distribution[print_stmt.suggested_level] += 1

        # Write modified content
        if modified and not self.dry_run:
            try:
                with open(analysis.file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            except Exception as e:
                self.report.errors.append(f"Error writing {analysis.file_path}: {e}")
                return False

        return modified

    def run(self, single_file: Optional[Path] = None) -> MigrationReport:
        """
        Run the migration process.

        Args:
            single_file: Optional single file to process

        Returns:
            MigrationReport with results
        """
        print("🔍 Print to Logging Migration Tool")
        print("=" * 70)
        print(
            f"Mode: {'DRY RUN (preview only)' if self.dry_run else 'LIVE (will modify files)'}"
        )
        print(f"Source Directory: {self.src_dir}")
        print()

        # Find files
        files = self.find_python_files(single_file)
        print(f"📁 Found {len(files)} Python files to analyze")
        print()

        # Process each file
        for file_path in files:
            analysis = self.analyze_file(file_path)
            if not analysis:
                continue

            self.report.files_analyzed += 1

            if analysis.print_statements:
                print(f"\n📄 {file_path.relative_to(self.src_dir)}")
                print(f"   Found {len(analysis.print_statements)} print statement(s)")

                for stmt in analysis.print_statements:
                    print(f"   Line {stmt.line_number}: {stmt.suggested_level.upper()}")
                    print(f"      Reason: {stmt.reason}")
                    print(f"      Before: {stmt.content.strip()}")
                    print(f"      After:  {self._convert_print_to_logging(stmt)}")

                self.report.print_statements_found += len(analysis.print_statements)

                # Migrate file
                if self.migrate_file(analysis):
                    self.report.files_modified += 1
                    self.report.print_statements_migrated += len(
                        analysis.print_statements
                    )
                    if not self.dry_run:
                        print(f"   ✅ Migrated successfully")
                    else:
                        print(f"   📋 Would be migrated (dry-run)")

        # Print summary
        self._print_summary()

        return self.report

    def _print_summary(self):
        """Print migration summary report."""
        print("\n" + "=" * 70)
        print("📊 Migration Summary")
        print("=" * 70)
        print(f"Files Analyzed:            {self.report.files_analyzed}")
        print(f"Files Modified:            {self.report.files_modified}")
        print(f"Print Statements Found:    {self.report.print_statements_found}")
        print(f"Print Statements Migrated: {self.report.print_statements_migrated}")
        print()
        print("Logging Level Distribution:")
        for level, count in sorted(self.report.level_distribution.items()):
            if count > 0:
                print(f"  {level.upper():8s}: {count:3d} statements")

        if self.report.errors:
            print("\n⚠️  Errors Encountered:")
            for error in self.report.errors:
                print(f"  - {error}")

        if self.dry_run:
            print("\n💡 This was a DRY RUN. No files were modified.")
            print("   Run without --dry-run to apply changes.")
        else:
            print("\n✅ Migration completed successfully!")
            print("   Please review the changes and run tests to ensure correctness.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate print() statements to logging in Novel-Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without modifying files
  python scripts/migrate_print_to_logging.py --dry-run

  # Apply migration to all files
  python scripts/migrate_print_to_logging.py

  # Migrate a single file
  python scripts/migrate_print_to_logging.py --file src/core/types.py

  # Migrate with custom source directory
  python scripts/migrate_print_to_logging.py --src-dir custom/path
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )

    parser.add_argument(
        "--src-dir",
        type=Path,
        default=Path("src"),
        help="Source directory to process (default: src)",
    )

    parser.add_argument(
        "--file",
        type=Path,
        help="Process only this specific file",
    )

    args = parser.parse_args()

    # Resolve paths
    src_dir = args.src_dir.resolve()
    single_file = args.file.resolve() if args.file else None

    # Validate paths
    if not src_dir.exists():
        print(f"❌ Error: Source directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    if single_file and not single_file.exists():
        print(f"❌ Error: File not found: {single_file}", file=sys.stderr)
        sys.exit(1)

    # Run migration
    migrator = PrintToLoggingMigrator(src_dir, dry_run=args.dry_run)
    report = migrator.run(single_file)

    # Exit with error code if there were errors
    if report.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
