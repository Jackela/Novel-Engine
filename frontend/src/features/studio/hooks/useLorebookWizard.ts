import { useCallback, useMemo, useRef, useState } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { LoreExtractCandidate } from "@/app/types/lore";
import type { DocumentSummary } from "@/app/types/studio";
import { confirmLoreCandidate, type LoreConfirmResult, writeLoreAliases } from "./lorebookConfirm";
import { type MergedLoreCandidate, mergeLoreCandidates } from "./loreCandidateMerge";
import { toErrorMessage } from "./toErrorMessage";

/** One wizard input segment's session state; the job evidence stays server-side. */
export interface LoreSegmentState {
  readonly id: string;
  readonly label: string;
  /** The submitted text; kept so a failed paste segment can be recovered. */
  readonly text: string;
  /** The document this segment was read from, when it was picked, not pasted. */
  readonly documentId: string | null;
  readonly status: "running" | "completed" | "failed";
  readonly error: string | null;
  readonly candidates: readonly LoreExtractCandidate[];
}

/**
 * The lorebook initialization wizard's session state (#614): input segments
 * are submitted one extraction Job each with per-segment busy/error state,
 * completed segments fold into one merged candidate list, and confirmation
 * runs the two existing steps per selected candidate (`lorebookConfirm.ts`).
 * Candidates live only in this session; `reset` abandons the wizard and
 * leaves the project untouched, while `clearResults` starts a new run over
 * the same extracted segments.
 */
export function useLorebookWizard(projectId: string, provider: string) {
  const [segments, setSegments] = useState<LoreSegmentState[]>([]);
  const [deselected, setDeselected] = useState<ReadonlySet<string>>(new Set());
  const [aliasDrafts, setAliasDrafts] = useState<Record<string, string>>({});
  const [results, setResults] = useState<LoreConfirmResult[]>([]);
  const [isConfirming, setIsConfirming] = useState(false);
  const runningTextsRef = useRef<ReadonlySet<string>>(new Set());
  const runningDocumentIdsRef = useRef<ReadonlySet<string>>(new Set());

  const resolveSegment = useCallback((id: string, next: Partial<LoreSegmentState>) => {
    setSegments((current) =>
      current.map((segment) => (segment.id === id ? { ...segment, ...next } : segment)),
    );
  }, []);

  const extractText = useCallback(
    async (segment: LoreSegmentState) => {
      try {
        const job = await api.extractLore(projectId, segment.text, provider);
        if (job.status === "failed") {
          resolveSegment(segment.id, {
            status: "failed",
            error: job.error ?? translateActive("lore.error.extract"),
            candidates: [],
          });
          return;
        }
        resolveSegment(segment.id, {
          status: "completed",
          error: null,
          candidates: job.result.candidates ?? [],
        });
      } catch (reason) {
        resolveSegment(segment.id, {
          status: "failed",
          error: toErrorMessage(reason, translateActive("lore.error.extract")),
          candidates: [],
        });
      }
    },
    [projectId, provider, resolveSegment],
  );

  /** Submit one pasted segment as its own extraction Job; an identical in-flight paste is a no-op. */
  const submitSegment = useCallback(
    async (text: string, label: string) => {
      const trimmed = text.trim();
      if (trimmed === "" || runningTextsRef.current.has(trimmed)) return;
      runningTextsRef.current = new Set([...runningTextsRef.current, trimmed]);
      const segment: LoreSegmentState = {
        id: nextSegmentId(),
        label,
        text: trimmed,
        documentId: null,
        status: "running",
        error: null,
        candidates: [],
      };
      setSegments((current) => [...current, segment]);
      try {
        await extractText(segment);
      } finally {
        runningTextsRef.current = new Set(
          [...runningTextsRef.current].filter((entry) => entry !== trimmed),
        );
      }
    },
    [extractText],
  );

  /** Read one existing document's current content and extract it as a new segment; a document already being extracted is a no-op. */
  const submitDocumentSegment = useCallback(
    async (document: Pick<DocumentSummary, "id" | "title">) => {
      if (runningDocumentIdsRef.current.has(document.id)) return;
      runningDocumentIdsRef.current = new Set([...runningDocumentIdsRef.current, document.id]);
      try {
        const loaded = await api.document(projectId, document.id);
        const segment: LoreSegmentState = {
          id: nextSegmentId(),
          label: document.title,
          text: loaded.content_markdown,
          documentId: document.id,
          status: "running",
          error: null,
          candidates: [],
        };
        setSegments((current) => [...current, segment]);
        await extractText(segment);
      } catch (reason) {
        const segment: LoreSegmentState = {
          id: nextSegmentId(),
          label: document.title,
          text: "",
          documentId: document.id,
          status: "failed",
          error: toErrorMessage(reason, translateActive("lore.error.extract")),
          candidates: [],
        };
        setSegments((current) => [...current, segment]);
      } finally {
        runningDocumentIdsRef.current = new Set(
          [...runningDocumentIdsRef.current].filter((entry) => entry !== document.id),
        );
      }
    },
    [extractText, projectId],
  );

  /** Recover a failed segment in place on its own row; a picked document's content is re-read first. */
  const retrySegment = useCallback(
    async (segmentId: string) => {
      const segment = segments.find((entry) => entry.id === segmentId);
      if (segment === undefined || segment.status !== "failed") return;
      resolveSegment(segmentId, { status: "running", error: null });
      if (segment.documentId === null) {
        await extractText({ ...segment, status: "running" });
        return;
      }
      try {
        const loaded = await api.document(projectId, segment.documentId);
        resolveSegment(segmentId, { text: loaded.content_markdown });
        await extractText({ ...segment, text: loaded.content_markdown, status: "running" });
      } catch (reason) {
        resolveSegment(segmentId, {
          status: "failed",
          error: toErrorMessage(reason, translateActive("lore.error.extract")),
        });
      }
    },
    [extractText, projectId, resolveSegment, segments],
  );

  const candidates = useMemo(() => {
    const completed: Array<{ segmentId: string; candidates: readonly LoreExtractCandidate[] }> = [];
    for (const segment of segments) {
      if (segment.status === "completed") {
        completed.push({ segmentId: segment.id, candidates: segment.candidates });
      }
    }
    return mergeLoreCandidates(completed);
  }, [segments]);

  const toggleCandidate = useCallback((key: string) => {
    setDeselected((current) => {
      const next = new Set(current);
      if (current.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const setAliasDraft = useCallback((key: string, value: string) => {
    setAliasDrafts((current) => ({ ...current, [key]: value }));
  }, []);

  /** The candidate's effective aliases: the edited draft when present, else the merged union. */
  const aliasesFor = useCallback(
    (candidate: MergedLoreCandidate): string[] => {
      const draft = aliasDrafts[candidate.key]?.trim();
      if (draft === undefined) return candidate.aliases;
      return draft
        .split(",")
        .map((alias) => alias.trim())
        .filter((alias) => alias !== "");
    },
    [aliasDrafts],
  );

  const selectedCandidates = useMemo(
    () => candidates.filter((candidate) => !deselected.has(candidate.key)),
    [candidates, deselected],
  );

  /**
   * Confirm every selected candidate. The per-candidate steps (creation then
   * alias write) stay ordered inside `confirmLoreCandidate`; the candidates
   * run concurrently and settle into `results` in the presented order.
   */
  const confirmSelected = useCallback(async () => {
    if (isConfirming || selectedCandidates.length === 0) return;
    setIsConfirming(true);
    try {
      const settled = await Promise.all(
        selectedCandidates.map((candidate) =>
          confirmLoreCandidate(projectId, candidate, aliasesFor(candidate)),
        ),
      );
      setResults(settled);
    } finally {
      setIsConfirming(false);
    }
  }, [aliasesFor, isConfirming, projectId, selectedCandidates]);

  /** Retry one candidate's alias write after a created-with-failed-aliases outcome. */
  const retryAliases = useCallback(
    async (key: string) => {
      const result = results.find((entry) => entry.key === key);
      if (result === undefined || result.documentId === null) return;
      const attempt = await writeLoreAliases(projectId, result.documentId, result.aliases);
      setResults((current) =>
        current.map((entry) =>
          entry.key === key
            ? {
                ...entry,
                outcome: attempt.ok ? "created" : entry.outcome,
                error: attempt.ok ? null : attempt.error,
              }
            : entry,
        ),
      );
    },
    [projectId, results],
  );

  /** Start a new run over the same extracted segments: only the confirmation results clear. */
  const clearResults = useCallback(() => {
    setResults([]);
    setIsConfirming(false);
  }, []);

  /** Abandon the wizard session: candidates and results cease to exist. */
  const reset = useCallback(() => {
    runningTextsRef.current = new Set();
    runningDocumentIdsRef.current = new Set();
    setSegments([]);
    setDeselected(new Set());
    setAliasDrafts({});
    setResults([]);
    setIsConfirming(false);
  }, []);

  return {
    segments,
    candidates,
    selectedCandidates,
    deselected,
    aliasDrafts,
    results,
    isConfirming,
    submitSegment,
    submitDocumentSegment,
    retrySegment,
    toggleCandidate,
    setAliasDraft,
    aliasesFor,
    confirmSelected,
    retryAliases,
    clearResults,
    reset,
  };
}

let segmentCounter = 0;
function nextSegmentId(): string {
  segmentCounter += 1;
  return `lore-segment-${segmentCounter}`;
}

export type LorebookWizardModel = ReturnType<typeof useLorebookWizard>;
