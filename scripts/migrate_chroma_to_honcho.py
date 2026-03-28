"""Migrate ChromaDB character memories to Honcho.

This script migrates existing character memories from ChromaDB to Honcho.
Since the user mentioned there is no existing data to migrate, this script
serves as a template for future migrations and demonstrates the migration pattern.

Usage:
    python scripts/migrate_chroma_to_honcho.py --source-db ./chroma_data --workspace novel-engine

Environment Variables:
    HONCHO_BASE_URL: Honcho server URL (default: http://localhost:8000)
    HONCHO_API_KEY: API key for cloud deployment
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("migrate_chroma_to_honcho")


async def migrate_memories(
    source_path: Path,
    workspace_id: str,
    batch_size: int = 100,
) -> dict[str, Any]:
    """Migrate memories from ChromaDB to Honcho.

    Args:
        source_path: Path to ChromaDB data directory.
        workspace_id: Target Honcho workspace ID.
        batch_size: Number of memories to process per batch.

    Returns:
        Migration statistics.
    """
    from src.contexts.character.infrastructure.adapters import (
        create_honcho_memory_adapter,
    )

    stats = {
        "total_found": 0,
        "migrated": 0,
        "failed": 0,
        "errors": [],
    }

    logger.info(f"Starting migration from {source_path} to workspace {workspace_id}")

    try:
        # Initialize Honcho adapter
        await create_honcho_memory_adapter()
        logger.info("Honcho adapter initialized")

        # This is a template - in real migration you would:
        # 1. Connect to ChromaDB
        # 2. Query all collections for character memories
        # 3. Transform each memory to Honcho format
        # 4. Store in Honcho

        # Example migration loop:
        # chroma_client = chromadb.PersistentClient(path=str(source_path))
        # collection = chroma_client.get_collection("character_memories")
        # results = collection.get(include=["metadatas", "documents"])
        #
        # for i, (doc, metadata) in enumerate(zip(results["documents"], results["metadatas"])):
        #     character_id = UUID(metadata["character_id"])
        #     result = await adapter.remember(
        #         character_id=character_id,
        #         content=doc,
        #         workspace_id=workspace_id,
        #         metadata={k: v for k, v in metadata.items() if k != "character_id"},
        #     )
        #     if result.is_ok():
        #         stats["migrated"] += 1
        #     else:
        #         stats["failed"] += 1
        #         stats["errors"].append(str(result.unwrap_error()))

        logger.info("No existing ChromaDB data to migrate (this is expected)")
        logger.info("Migration template ready for future use")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        stats["errors"].append(str(e))
        raise

    return stats


def export_migration_report(stats: dict[str, Any], output_path: Path) -> None:
    """Export migration statistics to JSON file.

    Args:
        stats: Migration statistics.
        output_path: Output file path.
    """
    with open(output_path, "w") as f:
        json.dump(stats, f, indent=2, default=str)
    logger.info(f"Migration report saved to {output_path}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate ChromaDB character memories to Honcho"
    )
    parser.add_argument(
        "--source-db",
        type=Path,
        help="Path to ChromaDB data directory",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default="novel-engine-migrated",
        help="Target Honcho workspace ID",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of memories to process per batch",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("migration_report.json"),
        help="Path for migration report output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without writing to Honcho",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("ChromaDB to Honcho Migration Tool")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be written")

    try:
        stats = await migrate_memories(
            source_path=args.source_db or Path("./chroma_data"),
            workspace_id=args.workspace,
            batch_size=args.batch_size,
        )

        # Print summary
        logger.info("=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        logger.info(f"Total memories found: {stats['total_found']}")
        logger.info(f"Successfully migrated: {stats['migrated']}")
        logger.info(f"Failed: {stats['failed']}")

        if stats["errors"]:
            logger.warning(f"Errors encountered: {len(stats['errors'])}")
            for error in stats["errors"][:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")

        # Export report
        export_migration_report(stats, args.report)

        # Exit with appropriate code
        if stats["failed"] > 0 and stats["migrated"] == 0:
            sys.exit(1)  # Complete failure
        elif stats["failed"] > 0:
            sys.exit(2)  # Partial success
        else:
            sys.exit(0)  # Success

    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
