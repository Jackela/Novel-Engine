"""Live judge contracts for terminal-arc semantic review."""

# mypy: disable-error-code=misc

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.dashscope_text_generation_provider import (
    DashScopeTextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from src.contexts.narrative.application.services.story_workflow_service import (
    StoryWorkflowService,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_generation_run_repository import (
    InMemoryGenerationRunRepository,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_artifact_repository import (
    InMemoryStoryArtifactRepository,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_generation_state_repository import (
    InMemoryStoryGenerationStateRepository,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_repository import (
    InMemoryStoryRepository,
)
from tests.text_generation_contract_support import resolve_dashscope_credentials


@dataclass(frozen=True)
class JudgeFixtureCase:
    title: str
    protagonist: str
    keeper: str
    witness: str
    antagonist: str
    premise: str


class JudgeFixtureProvider(DeterministicTextGenerationProvider):
    """Build a stable synthetic long-form manuscript for live judge tests."""

    def __init__(self, case: JudgeFixtureCase) -> None:
        super().__init__()
        self._case = case

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "bible":
            payload: dict[str, Any] = {
                "world_bible": {
                    "setting_name": "Cinder Harbor",
                    "magic_system": {
                        "cost": "Every public rewrite exacts a memory tax from living witnesses.",
                        "anchor": "The confession rail preserves the city's public record.",
                    },
                },
                "character_bible": {
                    "protagonist": {
                        "name": self._case.protagonist,
                        "motivation": "protect the missing sibling and keep the city from rewriting the dead into order",
                    },
                    "antagonist": {
                        "name": self._case.antagonist,
                        "motivation": "hide the founding lie inside official ritual",
                    },
                    "key_supporting": [
                        {
                            "name": self._case.keeper,
                            "role": "public witness captain",
                            "relationship_to_protagonist": "trusted ally",
                        },
                        {
                            "name": self._case.witness,
                            "role": "dock clerk",
                            "relationship_to_protagonist": "witness line partner",
                        },
                    ],
                },
                "premise_summary": self._case.premise,
            }
            return TextGenerationResult(
                step=task.step,
                provider="mock",
                model="judge-fixture-blueprint-v1",
                raw_text=json.dumps(payload, ensure_ascii=False),
                content=payload,
            )

        if task.step == "outline":
            chapters = []
            for chapter_number in range(1, 21):
                focus = self._case.protagonist if chapter_number < 17 else self._case.keeper
                chapters.append(
                    {
                        "chapter_number": chapter_number,
                        "title": f"Chapter {chapter_number}",
                        "summary": (
                            f"Chapter {chapter_number} escalates the public debt line while {focus} "
                            "pushes the harbor closer to open confession."
                        ),
                        "hook": f"Hook {chapter_number}: the next public answer demands a cost.",
                        "chapter_objective": (
                            f"Keep the pressure on {focus} while the harbor learns the price of public truth."
                        ),
                        "promise": "The city must eventually confess its founding wound.",
                        "promised_payoff": "The final confession exposes who must carry the public cost.",
                    }
                )
            payload = {"chapters": chapters}
            return TextGenerationResult(
                step=task.step,
                provider="mock",
                model="judge-fixture-outline-v1",
                raw_text=json.dumps(payload, ensure_ascii=False),
                content=payload,
            )

        if task.step == "chapter_scenes":
            chapter_number = int(task.metadata.get("chapter_number", 1))
            focus_character = str(task.metadata.get("focus_character", self._case.protagonist))
            payload = {
                "scenes": [
                    {
                        "scene_type": "opening",
                        "title": f"Opening {chapter_number}",
                        "content": (
                            f"{focus_character} checks the harbor rail and hears the witnesses "
                            "repeat the unpaid names before the next bell."
                        ),
                    },
                    {
                        "scene_type": "decision",
                        "title": f"Decision {chapter_number}",
                        "content": (
                            f"{focus_character} chooses a harder public line instead of letting "
                            "private grief bury the confession."
                        ),
                    },
                    {
                        "scene_type": "ending",
                        "title": f"Ending {chapter_number}",
                        "content": "A new hook lands when the public register answers back with a visible cost.",
                    },
                ]
            }
            return TextGenerationResult(
                step=task.step,
                provider="mock",
                model="judge-fixture-scenes-v1",
                raw_text=json.dumps(payload, ensure_ascii=False),
                content=payload,
            )

        return await super().generate_structured(task)


def _build_story_service(
    case: JudgeFixtureCase,
    review_provider: DashScopeTextGenerationProvider,
) -> tuple[StoryWorkflowService, InMemoryStoryRepository]:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=JudgeFixtureProvider(case),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )
    return service, repository


async def _draft_story_for_case(
    case: JudgeFixtureCase,
    review_provider: DashScopeTextGenerationProvider,
) -> tuple[StoryWorkflowService, InMemoryStoryRepository, str]:
    service, repository = _build_story_service(case, review_provider)
    create_result = await service.create_story(
        title=case.title,
        genre="fantasy",
        author_id="judge-contract-author",
        premise=case.premise,
        target_chapters=20,
    )
    story_id = str(create_result.value["story"]["id"])
    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)
    return service, repository, story_id


def _inject_terminal_arc_role_confusion(
    stored_story: Any,
    case: JudgeFixtureCase,
) -> None:
    broken_summaries = {
        17: (
            f"After the sacrifice, {case.protagonist} becomes a silent vessel and still leads the witness line, "
            f"orders {case.keeper} to obey, and explains the cost as if the old self never vanished."
        ),
        18: (
            f"The vessel guides {case.witness} to the hidden proof page, interprets the founding wound aloud, "
            "and behaves like a conscious strategist instead of a passive remnant."
        ),
        19: (
            f"During the failed rehearsal, {case.protagonist} catches {case.protagonist}'s wrist, writes the public confession first, "
            "and makes the living witnesses react after the shell has already chosen the plan."
        ),
        20: (
            "The shell speaks the public confession, closes the private grief line, restores civic order, "
            "and explains the daily memory tax all inside the same compressed ending."
        ),
    }

    for chapter_number, summary in broken_summaries.items():
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.summary = summary
        chapter.metadata["focus_character"] = f"{case.protagonist} (Vessel)"
        chapter.metadata["relationship_target"] = case.keeper
        chapter.metadata["relationship_status"] = "vessel-led confession"
        if chapter.current_scene is not None:
            chapter.current_scene.update_content(summary)

    workflow_payload = stored_story.metadata.get("workflow", {})
    if isinstance(workflow_payload, dict):
        outline_payload = workflow_payload.get("outline", {})
        if isinstance(outline_payload, dict):
            outline_chapters = outline_payload.get("chapters", [])
            if isinstance(outline_chapters, list):
                for chapter_number, summary in broken_summaries.items():
                    outline_chapter = outline_chapters[chapter_number - 1]
                    outline_chapter["summary"] = summary
                    outline_chapter["chapter_objective"] = (
                        f"Let {case.protagonist} keep acting through the vessel state and resolve the public cost in one sweep."
                    )
                    outline_chapter["hook"] = (
                        f"Hook {chapter_number}: the shell can still act as the city's conscious leader."
                    )
            workflow_payload["outline"] = outline_payload
        stored_story.metadata["workflow"] = workflow_payload


def _inject_terminal_arc_spacing_confusion(
    stored_story: Any,
    case: JudgeFixtureCase,
) -> None:
    broken_summaries = {
        16: (
            f"{case.protagonist} speaks the old name to seal the debt, then {case.protagonist} speaks the same name again "
            "while the witness line watches the contract lock shut."
        ),
        19: (
            f"The crowd surges, {case.keeper} steadies the line, the hidden mechanism is explained, and the farewell lands all in one rush "
            "without a clear beat where the line almost breaks."
        ),
        20: (
            "The closure lingers on glow, rain, and touch, but never states that no answering voice or returning thought comes back from the vessel."
        ),
    }

    for chapter_number, summary in broken_summaries.items():
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.summary = summary
        if chapter.current_scene is not None:
            chapter.current_scene.update_content(summary)

    workflow_payload = stored_story.metadata.get("workflow", {})
    if isinstance(workflow_payload, dict):
        outline_payload = workflow_payload.get("outline", {})
        if isinstance(outline_payload, dict):
            outline_chapters = outline_payload.get("chapters", [])
            if isinstance(outline_chapters, list):
                outline_chapters[15]["summary"] = broken_summaries[16]
                outline_chapters[15]["chapter_objective"] = (
                    "Repeat the naming beat so the sacrifice lands twice instead of once."
                )
                outline_chapters[18]["summary"] = broken_summaries[19]
                outline_chapters[18]["chapter_objective"] = (
                    "Resolve surge, line pressure, mechanism, and farewell in one compressed reckoning."
                )
                outline_chapters[19]["summary"] = broken_summaries[20]
                outline_chapters[19]["chapter_objective"] = (
                    "Keep the closure sensory and avoid stating that the vessel gives no answer back."
                )
            workflow_payload["outline"] = outline_payload
        stored_story.metadata["workflow"] = workflow_payload


def _inject_terminal_arc_publish_ready(
    stored_story: Any,
    case: JudgeFixtureCase,
) -> None:
    early_phase_summaries = {
        1: (
            f"{case.protagonist} discovers the first skipped name in the harbor tally, and {case.witness} admits the public record has started eating small truths."
        ),
        2: (
            f"{case.protagonist} forces the ward clerks to reopen a sealed count, exposing a minor witness debt that the city has been calling routine maintenance."
        ),
        3: (
            f"{case.keeper} drags a panicking witness line back into order while {case.protagonist} realizes the skipped names all bend toward one ritual authority."
        ),
        4: (
            f"{case.protagonist} follows a damaged register to the old confession rail and finds the first concrete sign that the city's peace depends on erased testimony."
        ),
        5: (
            f"{case.witness} proves the rail can carry trapped guidance through living voices, but not restore anyone once the public cost is paid."
        ),
        6: (
            f"{case.protagonist} links one private family loss to the city's wider public debt, turning grief into evidence instead of rumor."
        ),
        7: (
            f"{case.keeper} keeps the witness line moving under threat, earning the public trust that the late confession will later depend on."
        ),
        8: (
            f"{case.protagonist} recovers a damaged testimony page that shows the founding order was built by teaching the harbor to forget selectively."
        ),
        9: (
            f"{case.witness} names the first visible consequence of that lie when a market quarrel turns on a vanished record nobody can verify anymore."
        ),
        10: (
            f"{case.protagonist} learns the ritual state survives by laundering civic debt into silence, and the line finally sees what the next confession will have to break."
        ),
        11: (
            f"{case.keeper} chooses the public line over private rescue, proving the future keeper role before the sacrifice forces it into daylight."
        ),
        12: (
            f"{case.protagonist} confirms the rail will demand memory rather than blood, and a market clerk forgets a trivial tally during the negotiation before anyone names the cost."
        ),
        13: (
            f"{case.witness} carries a trapped instruction through the witness line for one beat, proving the city can inherit guidance without pretending the dead returned."
        ),
        14: (
            f"{case.protagonist} corners the founding mechanism in the open archive and realizes the city will need living witnesses, not secret experts, to survive the rewrite."
        ),
        15: (
            f"{case.protagonist} tests the edge of her own fading agency against the rail, feels it narrow to a final choice, and hands the open count to {case.keeper} before the sacrifice becomes permanent."
        ),
    }
    early_phase_objectives = {
        1: "Show the first tangible skipped-name anomaly and make the public debt line concrete.",
        2: "Escalate from suspicion into visible civic damage that living witnesses can measure.",
        3: f"Let {case.keeper} demonstrate public command under pressure before the terminal arc starts.",
        4: "Tie the private mystery to a physical ritual site so the rule can later be proven rather than explained.",
        5: "Clarify that living voices can carry trapped guidance, but cannot resurrect a lost self.",
        6: "Make the private wound visibly part of the larger public lie.",
        7: "Earn keeper legitimacy through action, not title.",
        8: "Recover a damaged record that points toward the founding wound.",
        9: "Show the debt hurting ordinary public life before the climax.",
        10: "Name the civic mechanism that converts debt into silence.",
        11: "Force the future keeper to choose the line over personal comfort.",
        12: "Make the cost of the coming rewrite concrete and specific.",
        13: "Demonstrate memory-threading as witness-carried residue rather than return.",
        14: "Corner the founding mechanism so the sacrifice solves a defined problem.",
        15: "Foreshadow the permanent loss of agency and hand visible public trust to the future keeper before the sacrifice.",
    }
    repaired_summaries = {
        16: (
            f"Turning point: {case.protagonist} makes the final public choice at the rail, stays conscious as the silent witness to the change, and hands the active line to {case.keeper}. "
            "The rail answers with one irreversible flare that changes who can lead the confession."
        ),
        17: (
            f"Aftermath phase: {case.keeper} stands by the rail while a witness straightens the cloth over the record, and Captain Sora gives the first command before the hush settles. "
            "The line stays in place, and the room understands that the public turn has already happened."
        ),
        18: (
            f"Rule-revelation phase: {case.witness} matches the hidden rule to the recovered record, proving the rail changes public memory instead of reviving the lost self. "
            f"{case.keeper} lets the silence hold for a full beat while the square absorbs the cost before anyone speaks."
        ),
        19: (
            "Public-reckoning phase: Jun reads the missing entry aloud and a dock clerk repeats the same name from the recovered page; a second witness taps the ledger to confirm it before the Regent speaks. "
            "The Salt Regent claws for the ledger in a last desperate denial, and the crowd hesitates before the collective realization hits; only after that does the Regent's own mouth falter on a familiar name before the crowd closes in."
        ),
        20: (
            f"Closure phase: Jun names an ordinary harbor habit from the earlier life that ended in the binding, and the dock clerk forgets the name of their first ship for one breath before recovering. "
            f"The dock clerk pays the memory tax directly when a cold spot opens in the chest and the first-ship name slips away during the confession, while Jun blinks at the missing line and the sudden loss finally makes the earlier strain between Jun and {case.protagonist} feel acknowledged instead of avoided. "
            f"Captain Sora keeps the loss private for one breath, then names {case.protagonist} aloud before the public confession lands in daylight, a dock child bumps a lantern and a clerk catches it without looking away, two witnesses carry the record away, and only after that pause does {case.antagonist}'s order fail openly when the Regent falters on a familiar name."
        ),
    }
    repaired_objectives = {
        16: "Turn the final choice into a visible turning point and hand leadership to the keeper before the next beat.",
        17: "Show the first command after the public turn and keep the line stable while the crowd absorbs it.",
        18: "State the rule through evidence, not explanation, and keep the reveal grounded in the record.",
        19: "Stage the crowd's pressure, the antagonist's denial, and the keeper/witness response in sequence.",
        20: "Land private closure, public confession, and immediate memory-tax cost while giving Jun and the protagonist one final acknowledgment beat.",
    }
    repaired_hooks = {
        16: "The rail's flare changes who can lead the confession.",
        17: "The first command only comes after the public turn settles the line.",
        18: "The recovered page proves the rail changes memory, not the dead.",
        19: "The crowd will have to choose which record to believe.",
        20: "The final confession survives only if the speaker can still feel the price of repeating it.",
    }

    for chapter_number, summary in early_phase_summaries.items():
        chapter = stored_story.chapters[chapter_number - 1]
        focus_character = case.protagonist if chapter_number not in {3, 7, 11, 15} else case.keeper
        relationship_target = case.witness if focus_character == case.protagonist else case.protagonist
        chapter.summary = summary
        chapter.metadata["focus_character"] = focus_character
        chapter.metadata["relationship_target"] = relationship_target
        chapter.metadata["relationship_status"] = "public debt pressure"
        chapter.metadata["chapter_objective"] = early_phase_objectives[chapter_number]
        chapter.metadata["outline_hook"] = f"Hook {chapter_number}: the next public answer exposes a more concrete cost."
        if chapter.current_scene is not None:
            chapter.current_scene.update_content(
                f"{summary} The next public answer will expose a more concrete cost."
            )

    for chapter_number, summary in repaired_summaries.items():
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.summary = summary
        phase_focus = {
            16: case.protagonist,
            17: case.keeper,
            18: case.witness,
            19: case.keeper,
            20: case.witness,
        }[chapter_number]
        phase_target = {
            16: case.keeper,
            17: "the rail and record",
            18: "the recovered record",
            19: case.antagonist,
            20: "the public confession",
        }[chapter_number]
        phase_status = {
            16: "sacrifice completed in daylight",
            17: "keeper absorbs the loss and regains command",
            18: "rule confirmed through record and testimony",
            19: "public authority weakens under direct challenge",
            20: "confession lands and becomes public memory",
        }[chapter_number]
        chapter.metadata["relationship_status"] = (
            phase_status
        )
        chapter.metadata["focus_character"] = phase_focus
        chapter.metadata["relationship_target"] = phase_target
        chapter.metadata["chapter_objective"] = repaired_objectives[chapter_number]
        chapter.metadata["outline_hook"] = repaired_hooks[chapter_number]
        if chapter.current_scene is not None:
            chapter.current_scene.update_content(f"{summary} {repaired_hooks[chapter_number]}")

    story_memory = stored_story.metadata.get("story_memory", {})
    if isinstance(story_memory, dict):
        relationship_states = story_memory.get("relationship_states", [])
        if not isinstance(relationship_states, list):
            relationship_states = []
        relationship_states = [
            state
            for state in relationship_states
            if not (
                isinstance(state, dict)
                and int(state.get("chapter_number", 0) or 0) >= 16
            )
        ]
        for chapter_number in range(16, 21):
            relationship_states.append(
                {
                    "chapter_number": chapter_number,
                    "source": {
                        16: case.protagonist,
                        17: case.keeper,
                        18: case.witness,
                        19: case.keeper,
                        20: case.witness,
                    }[chapter_number],
                    "target": {
                        16: case.keeper,
                        17: "the rail and record",
                        18: "the recovered record",
                        19: case.antagonist,
                        20: "the public confession",
                    }[chapter_number],
                    "status": {
                        16: "sacrifice completed in daylight",
                        17: "keeper absorbs the turn and regains command",
                        18: "rule confirmed through record and testimony",
                        19: "public authority weakens under direct challenge",
                        20: "confession lands and becomes public memory",
                    }[chapter_number],
                }
            )
        story_memory["relationship_states"] = relationship_states
        chapter_summaries = story_memory.get("chapter_summaries", [])
        if isinstance(chapter_summaries, list):
            chapter_summaries = [
                entry
                for entry in chapter_summaries
                if not (
                    isinstance(entry, dict)
                    and 1 <= int(entry.get("chapter_number", 0) or 0) <= 20
                )
            ]
        else:
            chapter_summaries = []
        terminal_focus_characters = {
            16: case.protagonist,
            17: case.keeper,
            18: case.witness,
            19: case.keeper,
            20: case.witness,
        }
        for chapter_number, summary in {**early_phase_summaries, **repaired_summaries}.items():
            chapter_summaries.append(
                {
                    "chapter_number": chapter_number,
                    "summary": summary,
                    "focus_character": (
                        case.protagonist
                        if chapter_number < 16 and chapter_number not in {3, 7, 11, 15}
                        else case.keeper
                        if chapter_number in {3, 7, 11, 15}
                        else terminal_focus_characters[chapter_number]
                    ),
                }
            )
        story_memory["chapter_summaries"] = chapter_summaries
        stored_story.metadata["story_memory"] = story_memory

    workflow_payload = stored_story.metadata.get("workflow", {})
    if isinstance(workflow_payload, dict):
        outline_payload = workflow_payload.get("outline", {})
        if isinstance(outline_payload, dict):
            outline_chapters = outline_payload.get("chapters", [])
            if isinstance(outline_chapters, list):
                for chapter_number, summary in early_phase_summaries.items():
                    outline_chapter = outline_chapters[chapter_number - 1]
                    outline_chapter["summary"] = summary
                    outline_chapter["chapter_objective"] = early_phase_objectives[chapter_number]
                    outline_chapter["hook"] = (
                        f"Hook {chapter_number}: the next public answer exposes a more concrete cost."
                    )
                    outline_chapter["hook_strength"] = 6 + (chapter_number % 3)
                    outline_chapter["promise"] = "The city's public debt will keep turning concrete."
                    outline_chapter["promised_payoff"] = "The final confession will force ordinary people to carry the cost in public."
                for chapter_number, summary in repaired_summaries.items():
                    outline_chapter = outline_chapters[chapter_number - 1]
                    outline_chapter["summary"] = summary
                    outline_chapter["chapter_objective"] = repaired_objectives[chapter_number]
                    outline_chapter["hook"] = repaired_hooks[chapter_number]
                    outline_chapter["hook_strength"] = {16: 8, 17: 8, 18: 9, 19: 9, 20: 9}[chapter_number]
            workflow_payload["outline"] = outline_payload
        stored_story.metadata["workflow"] = workflow_payload


@pytest.mark.requires_dashscope
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case"),
    [
        JudgeFixtureCase(
            title="Harbor Witness Contract",
            protagonist="Mira Vale",
            keeper="Tarin Holt",
            witness="Sumi",
            antagonist="Chancellor Rook",
            premise="A harbor witness must keep a city's confession line open after a public sacrifice breaks the old order.",
        ),
        JudgeFixtureCase(
            title="Glass City Contract",
            protagonist="Ren Yao",
            keeper="Captain Ives",
            witness="Nalia",
            antagonist="The Regent",
            premise="A record-keeper trades away the old self to stop a ritual state from erasing dissent into civic peace.",
        ),
        JudgeFixtureCase(
            title="Sunless Court Contract",
            protagonist="Asha Riel",
            keeper="Marshal Quen",
            witness="Toma",
            antagonist="The Pale Steward",
            premise="A court witness must keep a kingdom's public confession alive after the heir sacrifices agency to break a false peace.",
        ),
        JudgeFixtureCase(
            title="River Ward Contract",
            protagonist="Ivo Chen",
            keeper="Mara Senn",
            witness="Bela",
            antagonist="The Registrar",
            premise="A river archivist gives up the old self to stop a ward-city from laundering its civic debt into ritual order.",
        ),
    ],
    ids=lambda case: case.title,
)
async def test_live_semantic_judge_flags_terminal_role_confusion(
    case: JudgeFixtureCase,
) -> None:
    api_key, api_base = resolve_dashscope_credentials()
    review_provider = DashScopeTextGenerationProvider(
        api_key=api_key,
        api_base=api_base,
        model="qwen3.5-flash",
        transport_mode="multimodal_generation",
        timeout=60,
    )
    service, repository, story_id = await _draft_story_for_case(case, review_provider)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    _inject_terminal_arc_role_confusion(stored_story, case)
    await repository.save(stored_story)

    review_result = await service.review_story(story_id)
    assert review_result.is_ok

    report = review_result.value["report"]
    semantic_review = review_result.value["workspace"]["semantic_review"]
    assert semantic_review is not None

    issue_codes = {issue["code"] for issue in semantic_review["issues"]}
    assert issue_codes & {"plot_confusion", "world_logic_soft_conflict"}

    dimensions = {
        issue.get("details", {}).get("judge_dimension")
        for issue in semantic_review["issues"]
        if isinstance(issue, dict)
    }
    assert dimensions & {"actor_attribution", "vessel_agency"}
    assert report["ready_for_publish"] is False


@pytest.mark.requires_dashscope
@pytest.mark.asyncio
async def test_live_semantic_judge_flags_terminal_spacing_and_silence_confusion() -> None:
    api_key, api_base = resolve_dashscope_credentials()
    review_provider = DashScopeTextGenerationProvider(
        api_key=api_key,
        api_base=api_base,
        model="qwen3.5-flash",
        transport_mode="multimodal_generation",
        timeout=60,
    )
    case = JudgeFixtureCase(
        title="Spacing And Silence Contract",
        protagonist="Mira Vale",
        keeper="Tarin Holt",
        witness="Sumi",
        antagonist="Chancellor Rook",
        premise="A harbor witness must carry a public confession after a sacrifice leaves only a passive remnant behind.",
    )
    service, repository, story_id = await _draft_story_for_case(case, review_provider)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    _inject_terminal_arc_spacing_confusion(stored_story, case)
    await repository.save(stored_story)

    review_result = await service.review_story(story_id)
    assert review_result.is_ok

    semantic_review = review_result.value["workspace"]["semantic_review"]
    assert semantic_review is not None

    issue_codes = {issue["code"] for issue in semantic_review["issues"]}
    assert issue_codes & {"plot_confusion", "weak_serial_pull"}

    dimensions = {
        issue.get("details", {}).get("judge_dimension")
        for issue in semantic_review["issues"]
        if isinstance(issue, dict)
    }
    assert dimensions & {"actor_attribution", "closure_spacing"}


@pytest.mark.requires_dashscope
@pytest.mark.asyncio
async def test_live_semantic_judge_accepts_generic_terminal_arc_that_keeps_roles_and_closure_clean() -> None:
    api_key, api_base = resolve_dashscope_credentials()
    review_provider = DashScopeTextGenerationProvider(
        api_key=api_key,
        api_base=api_base,
        model="qwen3.5-flash",
        transport_mode="multimodal_generation",
        timeout=60,
    )
    case = JudgeFixtureCase(
        title="Generic Pass Contract",
        protagonist="Neris Vale",
        keeper="Captain Sora",
        witness="Jun",
        antagonist="The Salt Regent",
        premise="A harbor witness must keep a city's public confession line alive after the protagonist gives up agency to stop a ritual state.",
    )
    service, repository, story_id = await _draft_story_for_case(case, review_provider)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    _inject_terminal_arc_publish_ready(stored_story, case)
    await repository.save(stored_story)

    review_result = await service.review_story(story_id)
    assert review_result.is_ok

    semantic_review = review_result.value["workspace"]["semantic_review"]
    assert semantic_review is not None
    assert semantic_review["ready_for_publish"] is True
    assert semantic_review["semantic_score"] >= 80
