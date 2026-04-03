from __future__ import annotations

from typing import Any, cast

from scripts.uat.run_dashscope_longform_uat import (
    ChapterAudit,
    EditorialFinding,
    LongformUatReport,
    build_editorial_findings,
    render_markdown_report,
    validate_report,
)


def _build_export_payload(chapter_count: int) -> dict[str, Any]:
    chapters = []
    outline_chapters = []
    for chapter_number in range(1, chapter_count + 1):
        chapters.append(
            {
                "chapter_number": chapter_number,
                "title": f"Chapter {chapter_number}",
                "scenes": [
                    {
                        "content": " ".join(["serial"] * 320),
                    }
                ],
            }
        )
        outline_chapters.append(
            {
                "chapter_number": chapter_number,
                "hook": f"Hook {chapter_number}",
            }
        )

    return {
        "story": {
            "chapters": chapters,
        },
        "outline": {
            "chapters": outline_chapters,
        },
    }


def test_build_editorial_findings_surfaces_review_issues_and_underlength_chapters() -> None:
    payload = _build_export_payload(20)
    story = cast(dict[str, Any], payload["story"])
    outline = cast(dict[str, Any], payload["outline"])
    story["chapters"][2]["scenes"][0]["content"] = "too short"
    outline["chapters"][3]["hook"] = ""
    review = {
        "issues": [
            {
                "code": "relationship_drift",
                "severity": "blocker",
                "location": "chapter-7",
                "message": "Chapter 7 breaks the established alliance trajectory.",
                "suggestion": "Restore the turning beat before release.",
            }
        ]
    }

    chapter_audit, findings = build_editorial_findings(payload, review, target_chapters=20)

    assert len(chapter_audit) == 20
    assert any(finding.area == "system review" for finding in findings)
    assert any(finding.area == "chapter density" for finding in findings)
    assert any(finding.area == "hook architecture" for finding in findings)


def test_validate_report_rejects_missing_chapter_coverage() -> None:
    report = LongformUatReport(
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:10:00+00:00",
        base_url="http://127.0.0.1:8000",
        story_id="story-1",
        workspace_id="user-operator",
        story_title="Story",
        provider="dashscope",
        model="qwen3.5-flash",
        review_provider="dashscope",
        review_model="qwen3.5-flash",
        target_chapters=20,
        drafted_chapters=19,
        published=False,
        publish_outcome="blocked",
        publish_failure_code="QUALITY_GATE_FAILED",
        quality_score=86,
        continuity_score=88,
        pacing_score=83,
        reader_pull_score=82,
        plot_clarity_score=80,
        ooc_risk_score=12,
        structural_gate_passed=False,
        semantic_gate_passed=True,
        publish_gate_passed=False,
        issue_codes=["quality_gate_failed"],
        run_ids=[],
        artifact_kinds=[],
        revision_notes=[],
        request_trace=[],
        chapter_audit=[],
        editorial_findings=[],
    )

    try:
        validate_report(report)
    except ValueError as exc:
        assert "Expected at least 20 drafted chapters" in str(exc)
    else:
        raise AssertionError("validate_report should reject missing chapter coverage")


def test_validate_report_rejects_blocked_publish_outcome() -> None:
    report = LongformUatReport(
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:10:00+00:00",
        base_url="http://127.0.0.1:8000",
        story_id="story-1",
        workspace_id="user-operator",
        story_title="Story",
        provider="dashscope",
        model="qwen3.5-flash",
        review_provider="dashscope",
        review_model="qwen3.5-flash",
        target_chapters=20,
        drafted_chapters=20,
        published=False,
        publish_outcome="blocked",
        publish_failure_code="QUALITY_GATE_FAILED",
        quality_score=86,
        continuity_score=88,
        pacing_score=83,
        reader_pull_score=82,
        plot_clarity_score=80,
        ooc_risk_score=12,
        structural_gate_passed=False,
        semantic_gate_passed=True,
        publish_gate_passed=False,
        issue_codes=["quality_gate_failed"],
        run_ids=[],
        artifact_kinds=[],
        revision_notes=[],
        request_trace=[],
        chapter_audit=[
            ChapterAudit(
                chapter_number=chapter_number,
                title=f"Chapter {chapter_number}",
                scenes=3,
                word_count=900,
                hook=f"Hook {chapter_number}",
            )
            for chapter_number in range(1, 21)
        ],
        editorial_findings=[],
    )

    try:
        validate_report(report)
    except ValueError as exc:
        assert "did not reach a successful publish outcome" in str(exc)
    else:
        raise AssertionError("validate_report should reject blocked publish outcomes")


def test_render_markdown_report_includes_editorial_findings_and_trace() -> None:
    report = LongformUatReport(
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:10:00+00:00",
        base_url="http://127.0.0.1:8000",
        story_id="story-1",
        workspace_id="user-operator",
        story_title="Story",
        provider="dashscope",
        model="qwen3.5-flash",
        review_provider="dashscope",
        review_model="qwen3.5-flash",
        target_chapters=20,
        drafted_chapters=20,
        published=False,
        publish_outcome="blocked",
        publish_failure_code="QUALITY_GATE_FAILED",
        quality_score=86,
        continuity_score=88,
        pacing_score=83,
        reader_pull_score=82,
        plot_clarity_score=80,
        ooc_risk_score=12,
        structural_gate_passed=False,
        semantic_gate_passed=True,
        publish_gate_passed=False,
        issue_codes=["relationship_drift"],
        run_ids=["run-1"],
        artifact_kinds=["outline", "review"],
        revision_notes=["Repair chapter 7."],
        request_trace=[],
        chapter_audit=[
            ChapterAudit(
                chapter_number=1,
                title="Chapter 1",
                scenes=3,
                word_count=900,
                hook="A better hook",
            )
        ]
        * 20,
        editorial_findings=[
            EditorialFinding(
                severity="critical",
                area="system review",
                chapter=7,
                summary="Alliance break lands without setup.",
                recommendation="Restore the missing setup beat.",
            )
        ],
    )

    markdown = render_markdown_report(report)

    assert "DashScope 20-Chapter Live Evidence" in markdown
    assert "Alliance break lands without setup." in markdown
    assert "Machine Evidence" in markdown
