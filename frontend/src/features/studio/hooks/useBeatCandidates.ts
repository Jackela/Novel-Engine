import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import type { BeatCandidate, BeatOutlineAuthority } from "@/app/beatContract";
import { translateActive } from "@/app/i18n/translate";
import { toErrorMessage } from "./toErrorMessage";

interface BeatCandidatesState {
  readonly documentId: string;
  readonly candidates: BeatCandidate[];
  readonly outline: BeatOutlineAuthority | null;
  readonly isLoading: boolean;
  readonly error: string | null;
}

/**
 * DR-043: loads the outline beat catalog for the active chapter so the
 * association control can offer the beats instead of demanding they be typed
 * from memory. The catalog is scoped to the chapter document, refreshed
 * manually through the panel's refresh command (an outline edit is never
 * polled for), and a failed read stays visible instead of degrading to an
 * empty catalog.
 *
 * Failure semantics: responses from a superseded request never publish —
 * the in-flight controller is aborted and the request epoch invalidated on
 * document change, so a slow read for chapter A cannot repopulate chapter
 * B's catalog.
 */
export function useBeatCandidates(projectId: string, documentId: string) {
  const controllerRef = useRef<AbortController | null>(null);
  const requestEpochRef = useRef(0);
  const [state, setState] = useState<BeatCandidatesState>(() => ({
    documentId,
    candidates: [],
    outline: null,
    isLoading: true,
    error: null,
  }));

  const load = useCallback(async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const requestEpoch = ++requestEpochRef.current;
    const isCurrentRequest = () =>
      !controller.signal.aborted && requestEpochRef.current === requestEpoch;
    setState((current) => ({
      documentId,
      candidates: current.documentId === documentId ? current.candidates : [],
      outline: current.documentId === documentId ? current.outline : null,
      isLoading: true,
      error: null,
    }));

    try {
      const response = await api.chapterBeat(projectId, documentId, { signal: controller.signal });
      if (!isCurrentRequest()) return;
      setState({
        documentId,
        candidates: response.candidates,
        outline: response.outline,
        isLoading: false,
        error: null,
      });
    } catch (reason) {
      if (!isCurrentRequest()) return;
      setState((current) => ({
        documentId,
        candidates: current.documentId === documentId ? current.candidates : [],
        outline: current.documentId === documentId ? current.outline : null,
        isLoading: false,
        error: toErrorMessage(reason, translateActive("errors.loadBeats")),
      }));
    }
  }, [documentId, projectId]);

  useEffect(() => {
    void load();
    return () => {
      controllerRef.current?.abort();
      controllerRef.current = null;
      requestEpochRef.current += 1;
    };
  }, [load]);

  const stateIsCurrent = state.documentId === documentId;
  return {
    candidates: stateIsCurrent ? state.candidates : [],
    outline: stateIsCurrent ? state.outline : null,
    isLoading: stateIsCurrent ? state.isLoading : true,
    error: stateIsCurrent ? state.error : null,
    refresh: load,
  };
}
