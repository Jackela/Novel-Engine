import type { TextGenerationTask } from "../../application/ports/text_generation.js";
import { taskWritingLanguage } from "./deterministic_task_language.js";

/**
 * The deterministic provider's non-prose steps (DR-023 split for the file-size
 * gate): dimensioned editorial findings and lore-extract placeholder
 * candidates, each with an en and a zh wording family. Both builders stay
 * pure and deterministic — the same task always yields the same payload.
 */

interface EditorialFinding {
  document_id: string;
  severity: "blocker" | "warning";
  dimension: "continuity" | "pacing";
  message: string;
  suggestion: string;
}

/**
 * Deterministic editorial findings for the review step. The studio layer
 * hands over an annotated chapter manifest (ids, word counts, and the thin
 * threshold) so this provider stays inside the ai leaf: an empty chapter is
 * a continuity blocker, a chapter under the handed threshold a pacing
 * warning. zh tasks report the same dimensions with Chinese messages.
 */
export function buildEditorialReview(task: TextGenerationTask): { findings: EditorialFinding[] } {
  const language = taskWritingLanguage(task);
  const documents = Array.isArray(task.metadata.documents) ? task.metadata.documents : [];
  const findings: EditorialFinding[] = [];
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
    const title = String(chapter.title ?? (language === "zh" ? "未命名章节" : "Untitled chapter"));
    if (chapter.empty === true) {
      findings.push({
        document_id: chapter.id,
        severity: "blocker",
        dimension: "continuity",
        message:
          language === "zh" ? `${title} 没有任何正文内容。` : `${title} has no manuscript content.`,
        suggestion:
          language === "zh"
            ? "先写下这一章的正文，再做审阅。"
            : "Draft the chapter before asking for an editorial pass.",
      });
    } else if (chapter.words < chapter.thin_below) {
      findings.push({
        document_id: chapter.id,
        severity: "warning",
        dimension: "pacing",
        message:
          language === "zh"
            ? `${title} 目前只有 ${chapter.words} 字。`
            : `${title} contains only ${chapter.words} words.`,
        suggestion:
          language === "zh"
            ? "补足场景转折、后果与感官细节。"
            : "Develop the scene turn, consequence, and sensory detail.",
      });
    }
  }
  return { findings };
}

/**
 * Deterministic placeholder candidates for the lore-extract step. The trial
 * provider is the default first-run experience (#615), so the wizard loop must
 * work end to end on it: every valid segment yields the same fixed candidate
 * set, and each summary labels itself with the same trial-provider wording
 * family so the author knows real extraction needs a configured provider. A
 * zh segment gets the Chinese wording family instead of the English one.
 */
export function buildLoreExtractCandidates(task: TextGenerationTask): { candidates: unknown[] } {
  if (taskWritingLanguage(task) === "zh") {
    const trialNote = "内置试用提供方的占位结果；接入真实提供方后即可从你的草稿中提取设定。";
    return {
      candidates: [
        {
          kind: "character",
          title: "占位角色",
          aliases: ["试用候选"],
          summary: `示例角色建议。${trialNote}`,
        },
        {
          kind: "world",
          title: "占位世界",
          aliases: ["试用设定"],
          summary: `示例世界建议。${trialNote}`,
        },
      ],
    };
  }
  const trialNote =
    "Built-in trial provider placeholder; connect a real provider to extract lore from your draft.";
  return {
    candidates: [
      {
        kind: "character",
        title: "Placeholder Character",
        aliases: ["Trial Candidate"],
        summary: `Sample character suggestion. ${trialNote}`,
      },
      {
        kind: "world",
        title: "Placeholder World",
        aliases: ["Trial Setting"],
        summary: `Sample world suggestion. ${trialNote}`,
      },
    ],
  };
}
