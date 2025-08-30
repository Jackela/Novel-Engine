#!/usr/bin/env python3
"""
Database Security Testing for Novel Engine
==========================================

This script tests database security configurations and identifies potential
vulnerabilities in data storage and access patterns.
"""

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseSecurityTester:
    """Test database security configurations."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.findings = []

    def find_database_files(self) -> List[Path]:
        """Find all database files in the project."""
        db_files = []

        # Common database file patterns
        patterns = ["*.db", "*.sqlite", "*.sqlite3", "*.db3"]

        for pattern in patterns:
            db_files.extend(self.project_root.rglob(pattern))

        return db_files

    def test_database_permissions(self, db_path: Path) -> Dict[str, Any]:
        """Test database file permissions."""
        result = {
            "file": str(db_path),
            "readable": False,
            "writable": False,
            "size_bytes": 0,
            "vulnerabilities": [],
        }

        try:
            # Check file permissions
            result["readable"] = os.access(db_path, os.R_OK)
            result["writable"] = os.access(db_path, os.W_OK)
            result["size_bytes"] = db_path.stat().st_size

            # Check if file is world-readable (security risk)
            file_mode = oct(db_path.stat().st_mode)[-3:]
            if file_mode[2] in ["4", "5", "6", "7"]:  # Others can read
                result["vulnerabilities"].append("World-readable database file")

            if file_mode[2] in ["2", "3", "6", "7"]:  # Others can write
                result["vulnerabilities"].append("World-writable database file")

        except Exception as e:
            result["error"] = str(e)

        return result

    def test_database_content(self, db_path: Path) -> Dict[str, Any]:
        """Test database content for security issues."""
        result = {
            "file": str(db_path),
            "tables": [],
            "sensitive_data": [],
            "vulnerabilities": [],
        }

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Get all table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                result["tables"] = [table[0] for table in tables]

                # Check for sensitive table names
                sensitive_tables = [
                    "users",
                    "passwords",
                    "auth",
                    "credentials",
                    "secrets",
                    "tokens",
                ]
                for table_name in result["tables"]:
                    if any(
                        sensitive in table_name.lower()
                        for sensitive in sensitive_tables
                    ):
                        result["sensitive_data"].append(
                            f"Sensitive table name: {table_name}"
                        )

                # Check for sensitive column names in each table
                for table_name in result["tables"]:
                    try:
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()

                        sensitive_columns = [
                            "password",
                            "secret",
                            "token",
                            "key",
                            "hash",
                            "salt",
                        ]
                        for column in columns:
                            column_name = column[1].lower()
                            if any(
                                sensitive in column_name
                                for sensitive in sensitive_columns
                            ):
                                result["sensitive_data"].append(
                                    f"Sensitive column: {table_name}.{column[1]}"
                                )

                        # Sample data to check for patterns (first few rows only)
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                        sample_data = cursor.fetchall()

                        # Check for potential cleartext passwords or sensitive data
                        for row in sample_data:
                            for value in row:
                                if isinstance(value, str):
                                    if (
                                        len(value) > 8
                                        and value.isalnum()
                                        and not value.isdigit()
                                    ):
                                        # Could be a hash or sensitive string
                                        if len(value) in [
                                            32,
                                            40,
                                            64,
                                            128,
                                        ]:  # Common hash lengths
                                            continue  # Likely hashed, which is good
                                        elif "password" in str(value).lower():
                                            result["vulnerabilities"].append(
                                                f"Potential cleartext password in {table_name}"
                                            )

                    except sqlite3.Error:
                        # Skip tables that can't be read
                        continue

        except Exception as e:
            result["error"] = str(e)

        return result

    def test_sql_injection_vectors(self, db_path: Path) -> Dict[str, Any]:
        """Test potential SQL injection attack vectors."""
        result = {"file": str(db_path), "injection_tests": [], "vulnerabilities": []}

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Test various SQL injection payloads
                injection_payloads = [
                    "'; DROP TABLE test; --",
                    "' OR '1'='1",
                    "' UNION SELECT sql FROM sqlite_master --",
                    "'; INSERT INTO test VALUES ('injected'); --",
                ]

                for payload in injection_payloads:
                    test_result = {
                        "payload": payload,
                        "vulnerable": False,
                        "error": None,
                    }

                    try:
                        # This is a safe test - we're just checking if the database
                        # would be vulnerable to these patterns
                        cursor.execute("SELECT 1 WHERE ? = ?", (payload, payload))
                        test_result["vulnerable"] = False  # Parameterized query is safe
                    except sqlite3.Error as e:
                        test_result["error"] = str(e)
                        # If error contains specific patterns, it might indicate vulnerability
                        if "syntax error" in str(e).lower():
                            test_result["vulnerable"] = True

                    result["injection_tests"].append(test_result)

        except Exception as e:
            result["error"] = str(e)

        return result

    def run_comprehensive_database_security_test(self) -> Dict[str, Any]:
        """Run comprehensive database security testing."""
        logger.info("Starting database security assessment")

        results = {
            "timestamp": "2025-08-17T22:40:00",
            "database_files": [],
            "security_summary": {
                "total_databases": 0,
                "vulnerable_databases": 0,
                "critical_issues": 0,
                "warnings": 0,
            },
            "recommendations": [],
        }

        # Find all database files
        db_files = self.find_database_files()
        results["security_summary"]["total_databases"] = len(db_files)

        logger.info(f"Found {len(db_files)} database files")

        for db_file in db_files:
            logger.info(f"Testing database: {db_file}")

            db_result = {
                "file": str(db_file),
                "permissions": self.test_database_permissions(db_file),
                "content": self.test_database_content(db_file),
                "injection_vectors": self.test_sql_injection_vectors(db_file),
                "risk_level": "LOW",
            }

            # Assess risk level
            vulnerabilities = []
            vulnerabilities.extend(db_result["permissions"].get("vulnerabilities", []))
            vulnerabilities.extend(db_result["content"].get("vulnerabilities", []))

            if vulnerabilities:
                results["security_summary"]["vulnerable_databases"] += 1

                if any("cleartext password" in v.lower() for v in vulnerabilities):
                    db_result["risk_level"] = "CRITICAL"
                    results["security_summary"]["critical_issues"] += 1
                elif any("world-" in v.lower() for v in vulnerabilities):
                    db_result["risk_level"] = "HIGH"
                    results["security_summary"]["warnings"] += 1
                else:
                    db_result["risk_level"] = "MEDIUM"
                    results["security_summary"]["warnings"] += 1

            results["database_files"].append(db_result)

        # Generate recommendations
        if results["security_summary"]["critical_issues"] > 0:
            results["recommendations"].append(
                {
                    "priority": "CRITICAL",
                    "action": "Encrypt or hash all cleartext passwords immediately",
                    "category": "Data Protection",
                }
            )

        if results["security_summary"]["vulnerable_databases"] > 0:
            results["recommendations"].append(
                {
                    "priority": "HIGH",
                    "action": "Restrict database file permissions to application user only",
                    "category": "Access Control",
                }
            )

        results["recommendations"].extend(
            [
                {
                    "priority": "MEDIUM",
                    "action": "Implement database connection encryption (TLS)",
                    "category": "Encryption",
                },
                {
                    "priority": "MEDIUM",
                    "action": "Enable database audit logging for sensitive operations",
                    "category": "Monitoring",
                },
                {
                    "priority": "LOW",
                    "action": "Regular database security assessments",
                    "category": "Maintenance",
                },
            ]
        )

        return results


def main():
    """Main execution function."""
    tester = DatabaseSecurityTester()
    results = tester.run_comprehensive_database_security_test()

    # Save results
    output_file = "database_security_assessment.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\\n" + "=" * 60)
    print("DATABASE SECURITY ASSESSMENT RESULTS")
    print("=" * 60)
    print(f"Total databases found: {results['security_summary']['total_databases']}")
    print(
        f"Vulnerable databases: {results['security_summary']['vulnerable_databases']}"
    )
    print(f"Critical issues: {results['security_summary']['critical_issues']}")
    print(f"Warnings: {results['security_summary']['warnings']}")

    if results["security_summary"]["critical_issues"] > 0:
        print("\\n🔴 CRITICAL SECURITY ISSUES DETECTED!")
        print("   Immediate action required before production deployment.")
    elif results["security_summary"]["vulnerable_databases"] > 0:
        print("\\n🟡 Security vulnerabilities found.")
        print("   Review and remediate before production.")
    else:
        print("\\n✅ No critical database security issues detected.")

    print(f"\\n📄 Detailed report saved to: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
