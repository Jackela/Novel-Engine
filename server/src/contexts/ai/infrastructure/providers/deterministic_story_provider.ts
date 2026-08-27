import { HARD_DEFAULT_MODELS } from "../../application/model_resolution.js";
import {
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationResult,
  type TextGenerationTask,
  type TextProviderName,
} from "../../application/ports/text_generation.js";

const CAST_OPTIONS = [
  ["Mira", "Tomas", "station", "ledger page"],
  ["Ilen", "Rook", "archive stair", "sealed index card"],
  ["Sera", "Vale", "flood market", "brass token"],
  ["Niko", "Adra", "observatory roof", "blackout map"],
] as const;

const PRESSURE_OPTIONS = [
  "a debt that names its collector before the victim",
  "a record filed tomorrow with today's blood still wet",
  "a signal that arrives before the machine is built",
  "a bargain everyone remembers except the person who signed it",
] as const;

const TURN_OPTIONS = [
  "chooses to keep the evidence instead of handing it over",
  "lies once, then has to defend the lie with a true confession",
  "breaks the safest rule in the room to protect a weaker witness",
  "refuses the obvious escape because it would abandon the only proof",
] as const;

const DRAFT_TITLES = [
  "The First Cost",
  "A Record Filed Early",
  "The Witness Under Glass",
  "The Door That Answers Back",
  "Terms Written in Rain",
] as const;

function metadataString(metadata: Record<string, unknown>, key: string, fallback: string): string {
  const value = metadata[key];
  return typeof value === "string" && value.trim() !== "" ? value.trim() : fallback;
}

function metadataNumber(metadata: Record<string, unknown>, key: string): number {
  const value = metadata[key];
  return typeof value === "number" && Number.isFinite(value) && value >= 1 ? Math.floor(value) : 1;
}

function buildChapterDraft(task: TextGenerationTask): string {
  const chapterNumber = metadataNumber(task.metadata, "chapter_number");
  const title = metadataString(task.metadata, "title", "Untitled Story");
  const genre = metadataString(task.metadata, "genre", "fantasy");
  const premise = metadataString(task.metadata, "premise", "a rumor nobody wanted to own");
  const index = (chapterNumber - 1) % CAST_OPTIONS.length;
  const [protagonist, confidant, setting, objectName] = CAST_OPTIONS[index] ?? CAST_OPTIONS[0];
  const pressure =
    PRESSURE_OPTIONS[(chapterNumber - 1) % PRESSURE_OPTIONS.length] ?? PRESSURE_OPTIONS[0];
  const turn = TURN_OPTIONS[(chapterNumber - 1) % TURN_OPTIONS.length] ?? TURN_OPTIONS[0];
  const chapterTitle = DRAFT_TITLES[(chapterNumber - 1) % DRAFT_TITLES.length] ?? DRAFT_TITLES[0];
  return [
    `# Chapter ${chapterNumber}: ${chapterTitle}`,
    "",
    `The ${setting} had a way of making every private fear sound public. ${protagonist} noticed it in the scrape of shoes, in the hush after doors opened, and in the way the ${genre} city seemed to lean closer whenever someone pretended not to listen.`,
    "",
    `The first pressure in ${title} arrives quietly, before anyone can name it as danger. The trail began with ${premise}, but no trail stayed harmless after midnight. Tonight it had narrowed to ${objectName}, wrapped in plain paper and left where only a frightened friend would think to look.`,
    "",
    `"You should have burned it," ${confidant} said.`,
    "",
    `"You should have warned me before it learned my name," ${protagonist} answered.`,
    "",
    `That made ${confidant} go still. The silence was useful because it showed where the truth pressed hardest. ${protagonist} opened the packet and found one sentence waiting inside it: ${pressure}. The sentence did not behave like a message. It behaved like a door.`,
    "",
    `A vendor shouted two streets away. A lamp failed above them. For a moment the whole district seemed to inhale through the same narrow crack. ${confidant} reached for the packet, but ${protagonist} moved first and ${turn}.`,
    "",
    `That choice changed the room more than the evidence did. People who had looked bored now looked careful. The exit behind ${confidant} filled with someone's shadow, too patient to be an accident.`,
    "",
    `${protagonist} folded the ${objectName} into an inside pocket. "If this is a trap, we spring it where we can see the teeth."`,
    "",
    `The shadow at the exit shifted. ${confidant} did not run. That was the first honest thing either of them had done all night, and it cost them their last quiet minute.`,
  ].join("\n");
}

function buildChapterRevision(task: TextGenerationTask): string {
  const chapterNumber = metadataNumber(task.metadata, "chapter_number");
  const title = metadataString(task.metadata, "title", "Untitled Story");
  return [
    `# Chapter ${chapterNumber}: The Debt in the Rain`,
    "",
    `Mira waited until the platform emptied before she opened the parcel again. The page still carried the heading ${title}, though the words beneath it had begun to argue with each other. The danger had sounded tidy in Tomas's mouth, as if fear could be catalogued and shelved. It could not. The page trembled whenever she breathed on it, and each tremor pulled another memory loose: her father's sleeve dark with rain, her mother refusing to answer the door, Tomas pretending not to know which name had been crossed out first.`,
    "",
    '"Say it plainly," she told him.',
    "",
    'Tomas looked at the tunnel instead. "Plainly gets people killed."',
    "",
    '"So does ornament."',
    "",
    "That made him face her. Something changed there, not on the page: he stopped performing caution and let the old grief show. When the train arrived, neither of them boarded. They stayed beside the wet rail until the city moved around them, and the ledger page named the next cost in a line too sharp to mistake for metaphor.",
    "",
    "The bell struck again. This time the name it carried was hers, and every lamp along the platform leaned toward the sound.",
  ].join("\n");
}

/**
 * Deterministic editorial findings for the review step. The studio layer
 * hands over an annotated chapter manifest (ids, word counts, and the thin
 * threshold) so this provider stays inside the ai leaf: an empty chapter is
 * a continuity blocker, a chapter under the handed threshold a pacing
 * warning.
 */
function buildEditorialReview(task: TextGenerationTask): {
  findings: Array<{
    document_id: string;
    severity: "blocker" | "warning";
    dimension: "continuity" | "pacing";
    message: string;
    suggestion: string;
  }>;
} {
  const documents = Array.isArray(task.metadata.documents) ? task.metadata.documents : [];
  const findings: ReturnType<typeof buildEditorialReview>["findings"] = [];
  for (const entry of documents) {
    const chapter = entry as {
      id?: unknown;
      title?: unknown;
      words?: unknown;
      empty?: unknown;
      thin_below?: unknown;
    };
    if (
      typeof chapter.id !== "string" ||
      typeof chapter.words !== "number" ||
      typeof chapter.thin_below !== "number"
    ) {
      continue;
    }
    if (chapter.empty === true) {
      findings.push({
        document_id: chapter.id,
        severity: "blocker",
        dimension: "continuity",
        message: `${String(chapter.title ?? "Untitled chapter")} has no manuscript content.`,
        suggestion: "Draft the chapter before asking for an editorial pass.",
      });
    } else if (chapter.words < chapter.thin_below) {
      findings.push({
        document_id: chapter.id,
        severity: "warning",
        dimension: "pacing",
        message: `${String(chapter.title ?? "Untitled chapter")} contains only ${chapter.words} words.`,
        suggestion: "Develop the scene turn, consequence, and sensory detail.",
      });
    }
  }
  return { findings };
}

/**
 * The deterministic (mock) provider: real prose for the chapter steps and
 * deterministic dimensioned findings for the review step, so the offline
 * default experience yields manuscripts and reviews without network. Any
 * step outside its supported set fails with a provider error — an unknown
 * step is never echoed back as a placeholder payload.
 */
export class DeterministicStoryProvider implements TextGenerationProvider {
  private readonly providerName: TextProviderName;
  private readonly model: string;

  constructor(providerName: TextProviderName = "mock", model: string = HARD_DEFAULT_MODELS.mock) {
    this.providerName = providerName;
    this.model = model;
  }

  async generateStructured(task: TextGenerationTask): Promise<TextGenerationResult> {
    const step = task.step.trim().toLowerCase();
    if (step === "editorial_review") {
      const findings = buildEditorialReview(task);
      const rawText = JSON.stringify(findings);
      return {
        step: task.step,
        provider: this.providerName,
        model: this.model,
        rawText,
        content: findings,
        promptTokens: null,
        completionTokens: null,
      };
    }
    let markdown: string;
    if (step === "chapter_draft") {
      markdown = buildChapterDraft(task);
    } else if (step === "chapter_revision") {
      markdown = buildChapterRevision(task);
    } else {
      throw new TextGenerationProviderError(`Unsupported generation step: ${task.step}`);
    }
    return {
      step: task.step,
      provider: this.providerName,
      model: this.model,
      rawText: markdown,
      content: { chapter_markdown: markdown },
      promptTokens: null,
      completionTokens: null,
    };
  }
}
