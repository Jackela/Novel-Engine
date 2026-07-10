from __future__ import annotations

import json
from typing import Any

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderName,
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.deterministic_editorial_review import (
    build_editorial_review_payload,
)


class DeterministicTextGenerationProvider(TextGenerationProvider):
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
        if step == "chapter_draft":
            return self._build_chapter_payload(task)
        if step == "chapter_revision":
            return self._build_revision_payload(task)
        if step == "editorial_review":
            return build_editorial_review_payload(task)
        return {"result": "ok", "step": task.step, "echo": task.metadata}

    def _build_chapter_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        chapter_number = int(task.metadata.get("chapter_number", 1))
        title = str(task.metadata.get("title", "Untitled Story")).strip()
        genre = str(task.metadata.get("genre", "fantasy")).strip()
        premise = str(task.metadata.get("premise", "")).strip()
        tone = str(task.metadata.get("tone", "immersive serial fiction")).strip()
        previous_summaries = task.metadata.get("previous_summaries", [])
        unresolved_promises = task.metadata.get("unresolved_promises", [])
        cast_options = [
            ("Mira", "Tomas", "station", "ledger page"),
            ("Ilen", "Rook", "archive stair", "sealed index card"),
            ("Sera", "Vale", "flood market", "brass token"),
            ("Niko", "Adra", "observatory roof", "blackout map"),
        ]
        pressure_options = [
            "a debt that names its collector before the victim",
            "a record filed tomorrow with today's blood still wet",
            "a signal that arrives before the machine is built",
            "a bargain everyone remembers except the person who signed it",
        ]
        turn_options = [
            "chooses to keep the evidence instead of handing it over",
            "lies once, then has to defend the lie with a true confession",
            "breaks the safest rule in the room to protect a weaker witness",
            "refuses the obvious escape because it would abandon the only proof",
        ]
        protagonist, confidant, setting, object_name = cast_options[
            (chapter_number - 1) % len(cast_options)
        ]
        pressure = pressure_options[(chapter_number - 1) % len(pressure_options)]
        turn = turn_options[(chapter_number - 1) % len(turn_options)]
        continuity_note = (
            f"What happened before leaves {protagonist} watching for the cost "
            "inside ordinary gestures."
            if previous_summaries
            else f"The first pressure in {title} arrives quietly, before anyone can "
            "name it as danger."
        )
        promise_note = (
            str(unresolved_promises[-1])
            if isinstance(unresolved_promises, list) and unresolved_promises
            else pressure
        )
        premise_note = premise or "a rumor nobody wanted to own"
        chapter_titles = [
            "The First Cost",
            "A Record Filed Early",
            "The Witness Under Glass",
            "The Door That Answers Back",
            "Terms Written in Rain",
        ]
        chapter_title = chapter_titles[(chapter_number - 1) % len(chapter_titles)]
        chapter_markdown = (
            f"# Chapter {chapter_number}: {chapter_title}\n\n"
            f"The {setting} had a way of making every private fear sound public. "
            f"{protagonist} noticed it in the scrape of shoes, in the hush after "
            f"doors opened, and in the way the {genre} city seemed to lean closer "
            f"whenever someone pretended not to listen.\n\n"
            f"{continuity_note} The trail began with {premise_note}, but no trail "
            f"stayed harmless after midnight. Tonight it had narrowed to {object_name}, "
            f"wrapped in plain paper and left where only a frightened friend would "
            f"think to look.\n\n"
            f'"You should have burned it," {confidant} said.\n\n'
            f'"You should have warned me before it learned my name," {protagonist} '
            f"answered.\n\n"
            f"That made {confidant} go still. The silence was useful because it showed "
            f"where the truth pressed hardest. {protagonist} opened the packet and found "
            f"one sentence waiting inside it: {promise_note}. The sentence did not behave "
            f"like a message. It behaved like a door.\n\n"
            f"A vendor shouted two streets away. A lamp failed above them. For a moment "
            f"the whole district seemed to inhale through the same narrow crack. "
            f"{confidant} reached for the packet, but {protagonist} moved first and "
            f"{turn}.\n\n"
            f"That choice changed the room more than the evidence did. People who had "
            f"looked bored now looked careful. The exit behind {confidant} filled with "
            f"someone's shadow, too patient to be an accident.\n\n"
            f'{protagonist} folded the {object_name} into an inside pocket. "If this '
            f'is a trap, we spring it where we can see the teeth."\n\n'
            f"The shadow at the exit shifted. {confidant} did not run. That was the "
            f"first honest thing either of them had done all night, and it cost them "
            f"their last quiet minute."
        )
        return {
            "chapter_markdown": chapter_markdown,
            "sidecar_metadata": {
                "summary": (
                    f"Chapter {chapter_number} follows {protagonist} and {confidant} "
                    f"as {object_name} turns a private warning into public pressure."
                ),
                "characters": [protagonist, confidant],
                "promises": [
                    {
                        "text": f"The promise around {object_name} must force a visible consequence.",
                        "status": "open",
                        "chapter_number": chapter_number,
                    }
                ],
                "continuity_changes": [
                    f"{protagonist} keeps {object_name} instead of surrendering it.",
                    f"{confidant} stays after the exit is watched.",
                ],
                "style_notes": [
                    f"Tone target: {tone}",
                    "Complete chapter prose is authoritative; metadata is sidecar only.",
                ],
            },
        }

    def _build_revision_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        chapter_number = int(task.metadata.get("chapter_number", 1))
        chapter_markdown = (
            f"# Chapter {chapter_number}: The Debt in the Rain\n\n"
            "Mira waited until the platform emptied before she opened the parcel again. "
            "The danger had sounded tidy in Tomas's mouth, as if fear could be "
            "catalogued and shelved. It could not. The page trembled whenever she "
            "breathed on it, and each tremor pulled another memory loose: her "
            "father's sleeve dark with rain, her mother refusing to answer the door, "
            "Tomas pretending not to know which name had been crossed out first.\n\n"
            '"Say it plainly," she told him.\n\n'
            'Tomas looked at the tunnel instead. "Plainly gets people killed."\n\n'
            '"So does ornament."\n\n'
            "That made him face her. Something changed there, not on the page: he "
            "stopped performing caution and let the old grief show. When the train "
            "arrived, neither of them boarded. They stayed beside the wet rail until "
            "the city moved around them, and the ledger page named the next cost in a "
            "line too sharp to mistake for metaphor.\n\n"
            "The bell struck again. This time the name it carried was hers, and every "
            "lamp along the platform leaned toward the sound."
        )
        return {
            "chapter_markdown": chapter_markdown,
            "sidecar_metadata": {
                "summary": (
                    f"Chapter {chapter_number} is rewritten around a clearer emotional "
                    "choice and a more concrete ledger threat."
                ),
                "characters": ["Mira", "Tomas"],
                "promises": [
                    {
                        "text": "The next ledger cost must force a public consequence.",
                        "status": "open",
                        "chapter_number": chapter_number,
                    }
                ],
                "continuity_changes": [
                    "The chapter is handled as a full rewrite, not a patch.",
                ],
                "style_notes": [
                    "Avoids mechanical repair language and metadata exposition.",
                ],
            },
        }
