#!/usr/bin/env python3
"""
Test migration utilities

Utilities to help migrate tests from the current structure to the new
organized structure based on the comprehensive audit.
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class TestMigrationUtilities:
    """Utilities for test migration and organization."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"

        # Migration mapping based on audit results
        self.migration_map = {
            "api": {
                "target": "tests/integration/api",
                "patterns": ["api", "server", "endpoint", "fastapi"],
                "files": [
                    "test_api_comprehensive.py",
                    "test_api_endpoints.py",
                    "test_api_final_comprehensive.py",
                    "test_api_server.py",
                    "test_api_startup.py",
                    "test_api_startup_debug.py",
                    "test_api_startup_full.py",
                    "test_legacy_endpoints.py",
                    "test_api_endpoints_comprehensive.py",
                    "test_api_functionality.py",
                    "test_api_simple.py",
                    "test_fixed_api.py",
                    "test_unit_api_server.py",
                ],
            },
            "agents": {
                "target": "tests/integration/agents",
                "patterns": ["agent", "persona", "director"],
                "files": [
                    "test_director_agent.py",
                    "test_persona_agent.py",
                    "test_director_agent_advanced.py",
                    "test_director_agent_comprehensive.py",
                    "test_persona_agent_comprehensive.py",
                    "test_persona_agent_methods.py",
                    "test_persona_agent_modular.py",
                    "test_persona_agent_refactored.py",
                    "test_director_refactored.py",
                    "test_unit_director_agent.py",
                    "test_unit_chronicler_agent.py",
                ],
            },
            "core": {
                "target": "tests/integration/core",
                "patterns": [
                    "config",
                    "integration",
                    "foundation",
                    "event",
                    "logging",
                    "data_models",
                ],
                "files": [
                    "test_config_integration.py",
                    "test_integration.py",
                    "test_integration_complete.py",
                    "test_integration_comprehensive.py",
                    "test_foundation.py",
                    "test_event_bus.py",
                    "test_event_integration.py",
                    "test_logging_system.py",
                    "test_data_models.py",
                    "test_core_systems.py",
                    "test_simple_integration.py",
                ],
            },
            "bridges": {
                "target": "tests/integration/bridges",
                "patterns": ["bridge", "llm", "multi_agent"],
                "files": [
                    "test_enhanced_bridge.py",
                    "test_llm_integration.py",
                    "test_bridge_components_simple.py",
                    "test_bridge_core_only.py",
                    "test_enhanced_multi_agent_bridge_modular.py",
                    "test_llm_specific_functionality.py",
                ],
            },
            "interactions": {
                "target": "tests/integration/interactions",
                "patterns": ["interaction", "equipment", "character"],
                "files": [
                    "test_interaction_engine_comprehensive.py",
                    "test_interaction_engine_simple.py",
                    "test_interaction_engine_system_comprehensive.py",
                    "test_dynamic_equipment_system_modular.py",
                    "test_equipment_system_simple.py",
                    "test_character_decisions.py",
                    "test_character_name_fix.py",
                    "test_character_system_comprehensive.py",
                ],
            },
            "performance": {
                "target": "tests/performance",
                "patterns": [
                    "performance",
                    "optimization",
                    "async",
                    "memory",
                    "cache",
                ],
                "files": [
                    "test_performance_optimizations.py",
                    "test_async_llm_performance.py",
                    "test_async_processing_improvements.py",
                    "test_director_agent_loop_optimization.py",
                    "test_intelligent_caching_system.py",
                    "test_memory_leak_fixes.py",
                    "test_memory_optimization_gc.py",
                ],
            },
            "frontend": {
                "target": "tests/integration/frontend",
                "patterns": ["frontend", "ui"],
                "files": [
                    "test_frontend_comprehensive.js",
                    "test_ui_functionality.py",
                    "test_ui_simple.py",
                ],
            },
            "quality": {
                "target": "tests/unit/quality",
                "patterns": ["quality", "testing", "code_quality"],
                "files": [
                    "test_quality_framework.py",
                    "test_code_quality_analyzer.py",
                ],
            },
            "security": {
                "target": "tests/security",  # Keep existing security location
                "patterns": ["security"],
                "files": [
                    "test_comprehensive_security.py",
                    "test_security_framework.py",
                ],
            },
            "specialized": {
                "target": "tests/integration/components",
                "patterns": [
                    "ai_intelligence",
                    "story",
                    "narrative",
                    "chronicler",
                ],
                "files": [
                    "test_ai_intelligence_integration.py",
                    "test_story_generation_comprehensive.py",
                    "test_story_quality.py",
                    "test_narrative_engine.py",
                    "test_chronicler_agent.py",
                ],
            },
        }

    def analyze_file_content(self, file_path: Path) -> Dict[str, any]:
        """Analyze test file content to help determine correct location."""
        try:
            content = file_path.read_text(encoding="utf-8")

            analysis = {
                "imports": [],
                "test_classes": [],
                "test_functions": [],
                "markers": [],
                "keywords": [],
                "complexity": "simple",
            }

            # Find imports
            import_matches = re.findall(
                r"^(?:from|import)\s+([^\s#]+)", content, re.MULTILINE
            )
            analysis["imports"] = import_matches

            # Find test classes
            class_matches = re.findall(
                r"^class\s+(Test\w+)", content, re.MULTILINE
            )
            analysis["test_classes"] = class_matches

            # Find test functions
            func_matches = re.findall(
                r"^\s*def\s+(test_\w+)", content, re.MULTILINE
            )
            analysis["test_functions"] = func_matches

            # Find pytest markers
            marker_matches = re.findall(r"@pytest\.mark\.(\w+)", content)
            analysis["markers"] = list(set(marker_matches))

            # Analyze keywords
            keywords = []
            content_lower = content.lower()
            keyword_patterns = [
                "api",
                "server",
                "endpoint",
                "fastapi",
                "uvicorn",
                "agent",
                "persona",
                "director",
                "character",
                "integration",
                "config",
                "event",
                "logging",
                "bridge",
                "llm",
                "multi_agent",
                "interaction",
                "equipment",
                "dynamic",
                "performance",
                "optimization",
                "async",
                "cache",
                "frontend",
                "ui",
                "browser",
                "playwright",
                "quality",
                "security",
                "narrative",
                "story",
            ]

            for keyword in keyword_patterns:
                if keyword in content_lower:
                    keywords.append(keyword)

            analysis["keywords"] = keywords

            # Determine complexity
            num_classes = len(analysis["test_classes"])
            num_functions = len(analysis["test_functions"])

            if num_classes > 3 or num_functions > 20:
                analysis["complexity"] = "complex"
            elif num_classes > 1 or num_functions > 10:
                analysis["complexity"] = "moderate"

            return analysis

        except Exception as e:
            return {"error": str(e)}

    def classify_test_file(self, file_path: Path) -> Tuple[str, float]:
        """Classify test file and return category with confidence score."""
        filename = file_path.name.lower()
        analysis = self.analyze_file_content(file_path)

        scores = {}

        # Score by filename patterns
        for category, config in self.migration_map.items():
            score = 0.0

            # Check if file is explicitly listed
            if file_path.name in config["files"]:
                score += 0.8

            # Check filename patterns
            for pattern in config["patterns"]:
                if pattern in filename:
                    score += 0.3

            # Check content keywords
            if "keywords" in analysis:
                for keyword in analysis["keywords"]:
                    if keyword in config["patterns"]:
                        score += 0.2

            scores[category] = min(score, 1.0)

        # Find best match
        if scores:
            best_category = max(scores.items(), key=lambda x: x[1])
            if best_category[1] > 0.3:  # Minimum confidence threshold
                return best_category

        # Fallback classification
        if "unit" in str(file_path):
            return ("unit", 0.5)
        elif "integration" in str(file_path):
            return ("core", 0.5)
        else:
            return ("unclassified", 0.0)

    def get_migration_plan(self) -> Dict[str, List[Dict]]:
        """Generate complete migration plan."""
        plan = {
            "files_to_migrate": [],
            "directories_to_create": [],
            "conflicts": [],
            "statistics": {},
        }

        # Scan all test files
        all_test_files = list(self.tests_dir.rglob("test_*.py"))

        # Classify each file
        for test_file in all_test_files:
            # Skip files already in new structure
            if any(
                part in str(test_file)
                for part in [
                    "integration/api",
                    "integration/core",
                    "integration/bridges",
                    "integration/frontend",
                    "integration/interactions",
                    "integration/agents",
                    "integration/components",
                    "unit/agents",
                    "unit/interactions",
                    "unit/quality",
                ]
            ):
                continue

            category, confidence = self.classify_test_file(test_file)

            migration_info = {
                "source": str(test_file.relative_to(self.project_root)),
                "category": category,
                "confidence": confidence,
                "target": None,
                "analysis": self.analyze_file_content(test_file),
            }

            if category in self.migration_map:
                migration_info["target"] = self.migration_map[category][
                    "target"
                ]

            plan["files_to_migrate"].append(migration_info)

        # Check for target directories that need creation
        for category, config in self.migration_map.items():
            target_dir = self.project_root / config["target"]
            if not target_dir.exists():
                plan["directories_to_create"].append(config["target"])

        # Generate statistics
        plan["statistics"] = {
            "total_files": len(plan["files_to_migrate"]),
            "high_confidence": len(
                [f for f in plan["files_to_migrate"] if f["confidence"] > 0.7]
            ),
            "medium_confidence": len(
                [
                    f
                    for f in plan["files_to_migrate"]
                    if 0.3 <= f["confidence"] <= 0.7
                ]
            ),
            "low_confidence": len(
                [f for f in plan["files_to_migrate"] if f["confidence"] < 0.3]
            ),
            "categories": {},
        }

        for migration in plan["files_to_migrate"]:
            category = migration["category"]
            if category not in plan["statistics"]["categories"]:
                plan["statistics"]["categories"][category] = 0
            plan["statistics"]["categories"][category] += 1

        return plan

    def save_migration_plan(self, plan: Dict, output_file: str = None) -> Path:
        """Save migration plan to file."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"test_migration_plan_{timestamp}.json"

        output_path = self.project_root / "validation_reports" / output_file
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(plan, f, indent=2)

        return output_path

    def execute_migration(
        self, plan: Dict, dry_run: bool = True
    ) -> Dict[str, any]:
        """Execute the migration plan."""
        results = {
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "actions_taken": [],
            "errors": [],
            "statistics": {
                "files_migrated": 0,
                "directories_created": 0,
                "errors_encountered": 0,
            },
        }

        try:
            # Create directories
            for dir_path in plan["directories_to_create"]:
                full_path = self.project_root / dir_path
                if not dry_run:
                    full_path.mkdir(parents=True, exist_ok=True)
                    results["actions_taken"].append(
                        f"Created directory: {dir_path}"
                    )
                else:
                    results["actions_taken"].append(
                        f"[DRY RUN] Would create directory: {dir_path}"
                    )
                results["statistics"]["directories_created"] += 1

            # Migrate files
            for migration in plan["files_to_migrate"]:
                if migration["target"] and migration["confidence"] > 0.3:
                    source_path = self.project_root / migration["source"]
                    target_dir = self.project_root / migration["target"]
                    target_path = target_dir / source_path.name

                    if source_path.exists():
                        if not dry_run:
                            target_path.parent.mkdir(
                                parents=True, exist_ok=True
                            )
                            shutil.copy2(source_path, target_path)
                            results["actions_taken"].append(
                                f"Migrated: {migration['source']} -> {migration['target']}"
                            )
                        else:
                            results["actions_taken"].append(
                                f"[DRY RUN] Would migrate: {migration['source']} -> {migration['target']}"
                            )
                        results["statistics"]["files_migrated"] += 1
                    else:
                        error_msg = (
                            f"Source file not found: {migration['source']}"
                        )
                        results["errors"].append(error_msg)
                        results["statistics"]["errors_encountered"] += 1

        except Exception as e:
            results["errors"].append(f"Migration error: {str(e)}")
            results["statistics"]["errors_encountered"] += 1

        return results

    def print_migration_plan(self, plan: Dict):
        """Print migration plan summary."""
        print("\n" + "=" * 80)
        print("📋 TEST MIGRATION PLAN SUMMARY")
        print("=" * 80)

        stats = plan["statistics"]
        print(f"Total files to migrate: {stats['total_files']}")
        print(f"High confidence: {stats['high_confidence']}")
        print(f"Medium confidence: {stats['medium_confidence']}")
        print(f"Low confidence: {stats['low_confidence']}")

        print("\n📊 BY CATEGORY:")
        for category, count in stats["categories"].items():
            print(f"  {category}: {count} files")

        print("\n📁 DIRECTORIES TO CREATE:")
        for dir_path in plan["directories_to_create"]:
            print(f"  {dir_path}")

        print("\n🔄 HIGH CONFIDENCE MIGRATIONS:")
        high_conf_files = [
            f for f in plan["files_to_migrate"] if f["confidence"] > 0.7
        ]
        for migration in high_conf_files[:10]:  # Show first 10
            print(
                f"  {migration['source']} -> {migration['target']} ({migration['confidence']:.2f})"
            )

        if len(high_conf_files) > 10:
            print(f"  ... and {len(high_conf_files) - 10} more")

        print("\n" + "=" * 80)


def main():
    """Main function for migration utilities."""
    utils = TestMigrationUtilities()

    print("🔄 Generating test migration plan...")
    plan = utils.get_migration_plan()

    utils.print_migration_plan(plan)

    # Save plan
    plan_file = utils.save_migration_plan(plan)
    print(f"\n📄 Migration plan saved to: {plan_file}")

    return plan


if __name__ == "__main__":
    main()
