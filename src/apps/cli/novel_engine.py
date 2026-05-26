"""Command line entry point for the local-first Novel Engine runtime."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Sequence, cast

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderName,
)
from src.contexts.ai.infrastructure.providers import create_text_generation_provider
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from src.contexts.narrative.application.services.local_writing_engine import (
    LocalDraftingEngine,
    LocalExporter,
    LocalReviewer,
    NovelWorkspace,
    ReviewIssue,
    StoryConfig,
)
from src.shared.infrastructure.config.settings import get_settings


def _build_provider(provider_name: str) -> TextGenerationProvider:
    if provider_name == "mock":
        return DeterministicTextGenerationProvider()
    if provider_name in {"dashscope", "openai_compatible"}:
        settings = get_settings()
        return create_text_generation_provider(
            settings,
            provider_name=cast(TextGenerationProviderName, provider_name),
        )
    raise ValueError(f"Unsupported provider: {provider_name}")


def _build_review_provider(provider_name: str) -> TextGenerationProvider:
    if provider_name == "mock":
        return DeterministicTextGenerationProvider()
    if provider_name not in {"dashscope", "openai_compatible"}:
        raise ValueError(f"Unsupported provider: {provider_name}")
    return _build_provider(provider_name)


async def _cmd_init(args: argparse.Namespace) -> int:
    config = StoryConfig(
        title=args.title,
        genre=args.genre,
        premise=args.premise,
        target_chapters=args.target_chapters,
        tone=args.tone,
        target_audience=args.target_audience,
        themes=list(args.theme or []),
        style_profile={
            "chapter_shape": "complete prose chapter",
            "voice": "specific, concrete, non-template prose",
        },
    )
    workspace = NovelWorkspace.create(Path(args.workspace), config, overwrite=args.force)
    print(f"Initialized workspace: {workspace.root}")
    return 0


async def _cmd_draft(args: argparse.Namespace) -> int:
    workspace = NovelWorkspace(Path(args.workspace))
    engine = LocalDraftingEngine(_build_provider(args.provider))
    artifact = await engine.draft_chapter(
        workspace,
        int(args.chapter),
        force=bool(args.force),
    )
    print(
        f"Drafted chapter {artifact.chapter_number:03d}: "
        f"{workspace.chapter_path(artifact.chapter_number)}"
    )
    return 0


async def _cmd_run(args: argparse.Namespace) -> int:
    workspace = NovelWorkspace(Path(args.workspace))
    engine = LocalDraftingEngine(_build_provider(args.provider))
    target = int(args.target_chapters or workspace.load_config().target_chapters)
    with workspace.acquire_lock(operation="run"):
        run_dir = workspace.start_run("run")
        try:
            for chapter_number in range(1, target + 1):
                await engine.draft_chapter(
                    workspace,
                    chapter_number,
                    force=False,
                    run_dir=run_dir,
                )
            report = await LocalReviewer(
                _build_review_provider(args.provider)
            ).review_async(workspace)
            review_path = run_dir / "review-report.json"
            review_path.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            workspace.append_event(
                run_dir,
                "review",
                "completed",
                {
                    "blockers": len(report.blockers),
                    "warnings": len(report.warnings),
                    "review_report_relative_path": workspace.relative_path(review_path),
                },
            )
        except Exception as exc:
            workspace.append_event(run_dir, "run", "failed", {"error": str(exc)})
            raise
        workspace.append_event(
            run_dir,
            "run",
            "completed",
            {"target_chapters": target, "export_blocked": report.export_blocked},
        )
    print(
        f"Run completed: {len(workspace.list_chapters())} chapters, "
        f"{len(report.blockers)} blocker(s), {len(report.warnings)} warning(s)"
    )
    return 1 if report.export_blocked else 0


async def _cmd_review(args: argparse.Namespace) -> int:
    workspace = NovelWorkspace(Path(args.workspace))
    report = await LocalReviewer(_build_review_provider(args.provider)).review_async(
        workspace
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 1 if report.export_blocked else 0


async def _cmd_revise(args: argparse.Namespace) -> int:
    workspace = NovelWorkspace(Path(args.workspace))
    report = workspace.latest_review() or await LocalReviewer(
        _build_review_provider(args.provider)
    ).review_async(workspace)
    chapter_number = args.chapter
    if chapter_number is None:
        chapter_number = (
            _chapter_from_issue(report.blockers) or workspace.latest_chapter_number()
        )
    if not chapter_number:
        raise ValueError("No chapter available to revise")
    engine = LocalDraftingEngine(_build_provider(args.provider))
    await engine.revise_chapter(workspace, int(chapter_number), report)
    print(f"Revised chapter {int(chapter_number):03d}")
    return 0


async def _cmd_status(args: argparse.Namespace) -> int:
    workspace = NovelWorkspace(Path(args.workspace))
    config = workspace.load_config()
    review = workspace.latest_review()
    payload = {
        "title": config.title,
        "target_chapters": config.target_chapters,
        "chapter_count": len(workspace.list_chapters()),
        "latest_chapter": workspace.latest_chapter_number(),
        "latest_review": review.to_dict() if review else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


async def _cmd_export(args: argparse.Namespace) -> int:
    workspace = NovelWorkspace(Path(args.workspace))
    output = Path(args.output) if args.output else None
    exported = LocalExporter().export_markdown(workspace, output)
    print(f"Exported manuscript: {exported}")
    return 0


def _chapter_from_issue(issues: list[ReviewIssue]) -> int | None:
    for issue in issues:
        marker = issue.location.rsplit("-", 1)[-1]
        try:
            return int(marker)
        except ValueError:
            continue
    return None


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(prog="novel-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--workspace", required=True)
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--genre", required=True)
    init_parser.add_argument("--premise", required=True)
    init_parser.add_argument("--target-chapters", type=int, default=12)
    init_parser.add_argument("--tone", default="immersive serial fiction")
    init_parser.add_argument("--target-audience")
    init_parser.add_argument("--theme", action="append")
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(handler=_cmd_init)

    draft_parser = subparsers.add_parser("draft")
    draft_parser.add_argument("--workspace", required=True)
    draft_parser.add_argument("--chapter", type=int, required=True)
    draft_parser.add_argument("--provider", default="mock")
    draft_parser.add_argument("--force", action="store_true")
    draft_parser.set_defaults(handler=_cmd_draft)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--workspace", required=True)
    run_parser.add_argument("--target-chapters", type=int)
    run_parser.add_argument("--provider", default="mock")
    run_parser.set_defaults(handler=_cmd_run)

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--workspace", required=True)
    review_parser.add_argument("--provider", default="mock")
    review_parser.set_defaults(handler=_cmd_review)

    revise_parser = subparsers.add_parser("revise")
    revise_parser.add_argument("--workspace", required=True)
    revise_parser.add_argument("--chapter", type=int)
    revise_parser.add_argument("--provider", default="mock")
    revise_parser.set_defaults(handler=_cmd_revise)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--workspace", required=True)
    status_parser.set_defaults(handler=_cmd_status)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--workspace", required=True)
    export_parser.add_argument("--output")
    export_parser.set_defaults(handler=_cmd_export)
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    """Async CLI entry point."""
    args = build_parser().parse_args(argv)
    handler = cast(Any, args.handler)
    return int(await handler(args))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    return asyncio.run(async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["build_parser", "main"]
