"""Deterministic text generation provider for local development and tests."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderName,
    TextGenerationResult,
    TextGenerationTask,
)


class DeterministicTextGenerationProvider(TextGenerationProvider):
    """Deterministic provider that returns stable structured outputs."""

    def __init__(
        self,
        provider_name: TextGenerationProviderName = "mock",
        model: str = "deterministic-story-v1",
    ) -> None:
        self._provider_name = provider_name
        self._model = model

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        payload = self._build_payload(task)
        return TextGenerationResult(
            step=task.step,
            provider=self._provider_name,
            model=self._model,
            raw_text=json.dumps(payload, ensure_ascii=False),
            content=payload,
        )

    def _build_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        step = task.step.strip().lower()
        if step == "bible":
            return self._build_bible_payload(task)
        if step == "outline":
            return self._build_outline_payload(task)
        if step == "chapter_scenes":
            return self._build_scene_payload(task)
        if step == "semantic_review":
            return self._build_semantic_review_payload(task)
        if step == "revision":
            return self._build_revision_payload(task)
        if step == "terminal_arc_revision":
            return self._build_terminal_arc_revision_payload(task)
        return {"result": "ok", "step": task.step, "echo": task.metadata}

    def _build_bible_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        premise = str(task.metadata.get("premise", ""))
        genre = str(task.metadata.get("genre", "adventure"))
        tone = str(task.metadata.get("tone", "commercial web fiction"))
        fingerprint = self._fingerprint(premise, genre, tone)
        names = self._character_names(fingerprint)
        return {
            "world_bible": {
                "setting": f"{genre.title()} realm anchored by {fingerprint[:8]}",
                "core_rules": [
                    "Power has a measurable cost",
                    "Faction politics shape every major conflict",
                    "Public reputation impacts survival odds",
                ],
                "timeline_anchor": "Day 1",
                "tone": tone,
            },
            "character_bible": {
                "characters": [
                    {
                        "name": names[0],
                        "core_trait": "disciplined",
                        "motivation": "protect family",
                    },
                    {
                        "name": names[1],
                        "core_trait": "ambitious",
                        "motivation": "rise in faction rank",
                    },
                    {
                        "name": names[2],
                        "core_trait": "pragmatic",
                        "motivation": "uncover hidden truth",
                    },
                ]
            },
            "premise_summary": premise[:240],
        }

    def _build_outline_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        chapters_target = int(task.metadata.get("target_chapters", 12))
        chapters: list[dict[str, Any]] = []
        for chapter_number in range(1, max(1, chapters_target) + 1):
            chapters.append(
                {
                    "chapter_number": chapter_number,
                    "title": f"Chapter {chapter_number}: Escalation",
                    "summary": (
                        f"Day {chapter_number}: pressure rises and alliances shift."
                    ),
                    "hook": (
                        f"Who triggered the hidden trap at the end of chapter "
                        f"{chapter_number}?"
                    ),
                    "promise": f"Chapter {chapter_number} promises a sharper reveal.",
                    "pacing_phase": (
                        "setup"
                        if chapter_number <= 3
                        else "escalation"
                        if chapter_number <= max(4, chapters_target - 2)
                        else "payoff"
                    ),
                    "narrative_strand": (
                        "quest"
                        if chapter_number % 3 == 1
                        else "fire"
                        if chapter_number % 3 == 2
                        else "constellation"
                    ),
                    "chapter_objective": "force a costly decision",
                    "primary_strand": (
                        "quest"
                        if chapter_number % 3 == 1
                        else "fire"
                        if chapter_number % 3 == 2
                        else "constellation"
                    ),
                    "secondary_strand": (
                        "fire" if chapter_number % 2 == 0 else "constellation"
                    ),
                    "promised_payoff": (
                        f"Reveal the hidden cost seeded in chapter {chapter_number}."
                    ),
                    "hook_strength": 82 if chapter_number < chapters_target else 60,
                }
            )
        return {"chapters": chapters}

    def _build_scene_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        chapter_number = int(task.metadata.get("chapter_number", 1))
        chapter_title = str(task.metadata.get("chapter_title", f"Chapter {chapter_number}"))
        return {
            "scenes": [
                {
                    "scene_type": "opening",
                    "title": f"{chapter_title} - Opening Beat",
                    "content": (
                        f"Day {chapter_number}: the protagonist enters with a concrete goal."
                    ),
                },
                {
                    "scene_type": "dialogue",
                    "title": f"{chapter_title} - Pressure Test",
                    "content": (
                        "A tense negotiation exposes conflict and raises stakes."
                    ),
                },
                {
                    "scene_type": "ending",
                    "title": f"{chapter_title} - Hook",
                    "content": "A final twist lands as a cliffhanger?",
                },
            ]
        }

    def _build_revision_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        issues = task.metadata.get("issues", [])
        issue_count = len(issues) if isinstance(issues, list) else 0
        notes = [
            "Align chapter timeline markers so they never regress.",
            "Strengthen chapter-end hooks for non-final chapters.",
        ]
        if issue_count == 0:
            notes = ["No critical revisions required."]
        return {"revision_notes": notes}

    def _build_semantic_review_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        overdue_promise_count = int(task.metadata.get("overdue_promise_count", 0))
        unresolved_hook_count = int(task.metadata.get("unresolved_hook_count", 0))
        blocker = overdue_promise_count >= 4
        issues: list[dict[str, str]] = []
        if blocker:
            issues.append(
                {
                    "code": "promise_break",
                    "severity": "blocker",
                    "message": "Too many chapter promises remain unpaid.",
                    "location": "story",
                    "suggestion": "Resolve or escalate the oldest promise thread.",
                }
            )
        elif unresolved_hook_count >= 3:
            issues.append(
                {
                    "code": "weak_serial_pull",
                    "severity": "warning",
                    "message": "Recent hooks are not converting into enough forward pull.",
                    "location": "story",
                    "suggestion": "Sharpen the next chapter cliffhanger and payoff rhythm.",
                }
            )
        return {
            "semantic_score": 72 if blocker else 90,
            "reader_pull_score": 68 if unresolved_hook_count >= 3 else 88,
            "plot_clarity_score": 84,
            "ooc_risk_score": 18,
            "summary": (
                "Serial pull is under pressure from overdue promises."
                if blocker
                else "Semantic review sees stable reader pull and coherent progression."
            ),
            "repair_suggestions": [
                "兑现最老的一条承诺，避免章节债务继续堆积。",
                "下一章结尾给出更明确的追读钩子。",
            ],
            "issues": issues,
        }

    def _build_terminal_arc_revision_payload(
        self,
        task: TextGenerationTask,
    ) -> dict[str, Any]:
        target_chapters = int(task.metadata.get("target_chapters", 20))
        protagonist = str(task.metadata.get("protagonist", "the protagonist")).strip() or "the protagonist"
        primary_keeper = str(task.metadata.get("primary_keeper", "the keeper")).strip() or "the keeper"
        supporting_witness = (
            str(task.metadata.get("supporting_witness", "the witness")).strip()
            or "the witness"
        )
        public_witness = (
            str(task.metadata.get("public_witness", supporting_witness)).strip()
            or supporting_witness
        )
        continuity_anchor = (
            str(task.metadata.get("continuity_anchor", supporting_witness)).strip()
            or supporting_witness
        )
        vessel_label = (
            str(task.metadata.get("vessel_label", "the vessel")).strip() or "the vessel"
        )
        confirmation_trigger = (
            str(
                task.metadata.get(
                    "confirmation_trigger",
                    "the first physical confirmation from the old rule",
                )
            ).strip()
            or "the first physical confirmation from the old rule"
        )
        phases = {
            "sacrifice": max(1, target_chapters - 4),
            "aftermath": max(1, target_chapters - 3),
            "rule_revelation": max(1, target_chapters - 2),
            "public_reckoning": max(1, target_chapters - 1),
            "closure": max(1, target_chapters),
        }

        return {
            "revision_notes": [
                "Rebuilt the terminal arc around keeper-led agency, passive vessel logic, and clearer public cost.",
            ],
            "chapters": [
                {
                    "chapter_number": phases["sacrifice"],
                    "phase": "sacrifice",
                    "summary": (
                        f"{protagonist} makes a visible final choice while {continuity_anchor} witnesses the handoff that keeps the wider order alive, "
                        "knowing the decision closes every path back to ordinary agency."
                    ),
                    "objective": (
                        f"{protagonist} must choose the sacrifice in full view of {continuity_anchor} so the ending reads as a deliberate cost."
                    ),
                    "hook": (
                        f"{confirmation_trigger.capitalize()} proves the survivors now have to carry the new order without waiting for a miracle return."
                    ),
                    "focus_character": protagonist,
                    "relationship_target": continuity_anchor or primary_keeper,
                    "relationship_status": "last living handoff before the sacrifice closes",
                    "scene_brief": "Make the protagonist's final choice explicit and irreversible.",
                },
                {
                    "chapter_number": phases["aftermath"],
                    "phase": "aftermath",
                    "summary": (
                        f"{primary_keeper} tries once to draw an answer from {vessel_label}, fails in public as {continuity_anchor} watches, "
                        "and realizes the body is moving only through threaded memory rather than recovered feeling."
                    ),
                    "objective": (
                        f"{primary_keeper} must move from grief to duty through one failed action, while {vessel_label} remains passive and any motion reads as borrowed direction rather than instinct."
                    ),
                    "hook": "The first unanswered silence points toward a buried rule the living still do not understand.",
                    "focus_character": primary_keeper,
                    "relationship_target": vessel_label,
                    "relationship_status": "guardian of the irreversible cost",
                    "scene_brief": "Show grief breaking into duty without giving the vessel intentional action.",
                },
                {
                    "chapter_number": phases["rule_revelation"],
                    "phase": "rule_revelation",
                    "summary": (
                        f"A first public attempt fails in view before {primary_keeper}, {supporting_witness or continuity_anchor}, and {continuity_anchor} uncover proof that the old order hid its price in public records, "
                        f"while {vessel_label} only echoes the discovery through passive reaction."
                    ),
                    "objective": "Make the world rule legible through concrete evidence instead of explanation alone, and show why the first public response was not enough.",
                    "hook": "The proof shows that the final confession will cost the whole city, not only one household.",
                    "focus_character": primary_keeper,
                    "relationship_target": vessel_label,
                    "relationship_status": "keeper interpreting a passive remnant",
                    "scene_brief": "Keep the revelation physical and evidence-driven.",
                },
                {
                    "chapter_number": phases["public_reckoning"],
                    "phase": "public_reckoning",
                    "summary": (
                        f"The first public attempt nearly breaks under pressure, {public_witness} and {continuity_anchor} have to close the gap before the line scatters, "
                        "and the room learns through that near-break that the new cost can no longer stay abstract while the farewell finishes inside the same reckoning."
                    ),
                    "objective": (
                        f"Let living witnesses act before {primary_keeper} explains anything, give the line one near-break beat before it stabilizes, and turn the public cost into a visible danger."
                    ),
                    "hook": "If the line cannot carry the confession into daylight, the old silence will close over the city again.",
                    "focus_character": primary_keeper,
                    "relationship_target": vessel_label,
                    "relationship_status": "living line carrying borrowed cadence",
                    "scene_brief": "Keep two non-keeper witnesses active and let the vessel stay passive.",
                },
                {
                    "chapter_number": phases["closure"],
                    "phase": "closure",
                    "summary": (
                        f"{supporting_witness or continuity_anchor} names one concrete remembered detail from the life now gone, {public_witness} makes the first public move, "
                        f"and {primary_keeper} confirms the new order while {vessel_label} offers no answering voice or returning thought, a visible mark flashes, vanishes from sight, "
                        "and leaves a bodily aftereffect that proves the cost will continue."
                    ),
                    "objective": (
                        "Split the ending into private closure, public confession, and tangible aftermath without compressing them together or repeating the farewell beat, and make the vessel's silence explicit."
                    ),
                    "hook": "The city survives, but the daily public cost now belongs to the living.",
                    "focus_character": primary_keeper,
                    "relationship_target": vessel_label,
                    "relationship_status": "living keeper of a public debt",
                    "scene_brief": "Show a concrete public consequence and keep the vessel passive.",
                },
            ],
        }

    @staticmethod
    def _fingerprint(*parts: str) -> str:
        value = "|".join(part.strip().lower() for part in parts)
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _character_names(self, fingerprint: str) -> list[str]:
        pool = [
            "Ari",
            "Lian",
            "Kade",
            "Mira",
            "Ren",
            "Sora",
            "Vale",
            "Nox",
            "Tara",
            "Jin",
        ]
        start = int(fingerprint[:2], 16) % len(pool)
        return [pool[(start + offset) % len(pool)] for offset in range(3)]
