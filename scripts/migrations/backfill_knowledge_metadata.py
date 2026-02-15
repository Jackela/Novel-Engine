#!/usr/bin/env python3
"""
Mock Migration Script: Backfill Knowledge Metadata

OPT-006: Domain: Structured Metadata Schema

This script demonstrates how to backfill missing KnowledgeMetadata fields
for existing vector documents. In a production environment, this would:

1. Connect to the vector store (ChromaDB, etc.)
2. Fetch all existing documents
3. Add default KnowledgeMetadata fields to documents missing them
4. Update the documents in the vector store

Usage:
    python scripts/migrations/backfill_knowledge_metadata.py [--dry-run] [--verbose]
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.contexts.knowledge.domain.models.knowledge_metadata import (
    ConfidentialityLevel,
)


# Mock vector document structure for demonstration
class MockVectorDocument:
    """Mock vector document for migration demonstration."""

    def __init__(
        self,
        id: str,
        content: str,
        metadata: dict[str, Any],
        embedding: list[float] | None = None,
    ):
        self.id = id
        self.content = content
        self.metadata = metadata
        self.embedding = embedding

    def needs_migration(self) -> bool:
        """Check if document needs KnowledgeMetadata backfill."""
        required_fields = ["world_version", "confidentiality_level", "source_version"]
        return not all(field in self.metadata for field in required_fields)

    def backfill_metadata(
        self,
        world_version: str = "1.0.0",
        confidentiality_level: ConfidentialityLevel = ConfidentialityLevel.PUBLIC,
    ) -> dict[str, Any]:
        """
        Generate backfilled metadata.

        Returns the updated metadata dictionary.
        """
        updated = self.metadata.copy()

        # Preserve existing values if present
        if "world_version" not in updated:
            updated["world_version"] = world_version
        if "confidentiality_level" not in updated:
            updated["confidentiality_level"] = confidentiality_level.value
        if "source_version" not in updated:
            updated["source_version"] = 1

        # Set last_accessed to None (never accessed) if not present
        if "last_accessed" not in updated:
            updated["last_accessed"] = None

        return updated


def create_mock_documents(count: int = 10) -> list[MockVectorDocument]:
    """
    Create mock vector documents for testing.

    Simulates documents from different world versions and with
    varying existing metadata structures.
    """
    docs: list[MockVectorDocument] = []

    # Documents with complete metadata (no migration needed)
    for i in range(2):
        docs.append(
            MockVectorDocument(
                id=f"doc-complete-{i}",
                content=f"Complete metadata document {i}",
                metadata={
                    "source_type": "LORE",
                    "source_id": f"lore-{i}",
                    "world_version": "1.2.0",
                    "confidentiality_level": "public",
                    "source_version": 2,
                    "last_accessed": datetime.now(timezone.utc).isoformat(),
                },
            )
        )

    # Documents missing KnowledgeMetadata (need migration)
    source_types = ["CHARACTER", "LORE", "SCENE", "ITEM", "LOCATION"]
    for i in range(count - 2):
        source_type = source_types[i % len(source_types)]
        docs.append(
            MockVectorDocument(
                id=f"doc-incomplete-{i}",
                content=f"Incomplete metadata document {i}",
                metadata={
                    "source_type": source_type,
                    "source_id": f"{source_type.lower()}-{i}",
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "word_count": 100 + i,
                    # Missing: world_version, confidentiality_level, source_version
                },
            )
        )

    return docs


def run_migration(
    documents: list[MockVectorDocument],
    dry_run: bool = True,
    world_version: str = "1.0.0",
    confidentiality_level: ConfidentialityLevel = ConfidentialityLevel.PUBLIC,
) -> dict[str, Any]:
    """
    Run the migration on a list of documents.

    Args:
        documents: List of vector documents to migrate
        dry_run: If True, don't actually update documents (just report)
        world_version: Default world version for backfill
        confidentiality_level: Default confidentiality level for backfill

    Returns:
        Dictionary with migration statistics
    """
    stats = {
        "total": len(documents),
        "needs_migration": 0,
        "already_compliant": 0,
        "migrated": 0,
        "skipped": 0,
        "errors": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    for doc in documents:
        try:
            if doc.needs_migration():
                stats["needs_migration"] += 1

                if not dry_run:
                    # Actually backfill the metadata
                    new_metadata = doc.backfill_metadata(
                        world_version, confidentiality_level
                    )
                    doc.metadata = new_metadata
                    stats["migrated"] += 1
                else:
                    # Dry run: just count
                    stats["migrated"] += 1
            else:
                stats["already_compliant"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"Error migrating document {doc.id}: {e}", file=sys.stderr)

    stats["skipped"] = stats["total"] - stats["migrated"] - stats["errors"]

    return stats


def print_report(
    docs: list[MockVectorDocument], stats: dict[str, Any], verbose: bool = False
) -> None:
    """Print migration report."""
    print("\n" + "=" * 60)
    print("Knowledge Metadata Backfill Report")
    print("=" * 60)
    print(f"Run at: {stats['timestamp']}")
    print(f"Total documents: {stats['total']}")
    print(f"Documents needing migration: {stats['needs_migration']}")
    print(f"Documents already compliant: {stats['already_compliant']}")
    print(f"Documents migrated: {stats['migrated']}")
    print(f"Errors: {stats['errors']}")
    print("=" * 60)

    if verbose:
        print("\nDetailed document status:")
        for doc in docs:
            status = "NEEDS MIGRATION" if doc.needs_migration() else "COMPLIANT"
            print(f"  [{status}] {doc.id}")
            print(f"    source_type: {doc.metadata.get('source_type', 'N/A')}")
            if doc.needs_migration():
                print(
                    f"    Missing: world_version, confidentiality_level, source_version"
                )
            else:
                print(f"    world_version: {doc.metadata.get('world_version', 'N/A')}")
                print("    confidentiality: [redacted]")
                print(
                    f"    source_version: {doc.metadata.get('source_version', 'N/A')}"
                )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill KnowledgeMetadata for existing vector documents"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without making changes (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply the migration (use with caution)",
    )
    parser.add_argument(
        "--world-version",
        default="1.0.0",
        help="Default world version for backfilled metadata (default: 1.0.0)",
    )
    parser.add_argument(
        "--confidentiality-level",
        default="public",
        choices=["public", "internal", "restricted", "sensitive"],
        help="Default confidentiality level for backfilled metadata (default: public)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed document status"
    )
    parser.add_argument(
        "--mock-count",
        type=int,
        default=10,
        help="Number of mock documents to generate for testing (default: 10)",
    )

    args = parser.parse_args()

    # Parse confidentiality level
    try:
        confidentiality = ConfidentialityLevel(args.confidentiality_level)
    except ValueError:
        print("Invalid confidentiality level provided.", file=sys.stderr)
        return 1

    dry_run = not args.apply

    if dry_run:
        print("Running in DRY RUN mode (no changes will be made)")
        print("Use --apply to actually perform the migration\n")

    # Create mock documents for demonstration
    print(f"Creating {args.mock_count} mock documents...")
    documents = create_mock_documents(args.mock_count)

    # Run migration
    stats = run_migration(
        documents=documents,
        dry_run=dry_run,
        world_version=args.world_version,
        confidentiality_level=confidentiality,
    )

    # Print report
    print_report(documents, stats, verbose=args.verbose)

    if dry_run:
        print("\nTo apply these changes, run with --apply flag")

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
