import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import type { BeatCandidate, BeatOutlineAuthority } from "@/app/beatContract";
import { translateActive } from "@/app/i18n/translate";
import { toErrorMessage } from "./toErrorMessage";

interface BeatCandidatesState {
  readonly projectId: string;
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
 * Failure semantics: a response from a superseded request never publishes —
 * the in-flight controller is aborted, the request epoch is invalidated on
 * document change, and the active-project ref gates every write, so neither a
 * slow read for chapter A nor a previous project's late read can repopulate
 * the current catalog. The returned projection is scope-checked against the
 * project as well as the document, so a project switch reads as unloaded
 * instead of showing the previous project's catalog.
 */
export function useBeatCandidates(projectId: string, documentId: string) {
  const controllerRef = useRef<AbortController | null>(null);
  const requestEpochRef = useRef(0);
  const activeProjectIdRef = useRef(projectId);
  const [state, setState] = useState<BeatCandidatesState>(() => ({
    projectId,
    documentId,
    candidates: [],
    outline: null,
    isLoading: true,
    error: null,
  }));

  useEffect(() => {
    activeProjectIdRef.current = projectId;
  }, [projectId]);

  const load = useCallback(async () => {
    if (activeProjectIdRef.current !== projectId) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const requestEpoch = ++requestEpochRef.current;
    const isCurrentRequest = () =>
      !controller.signal.aborted &&
      requestEpochRef.current === requestEpoch &&
      activeProjectIdRef.current === projectId;
    const sameScope = (candidate: { readonly projectId: string; readonly documentId: string }) =>
      candidate.projectId === projectId && candidate.documentId === documentId;
    setState((current) => ({
      projectId,
      documentId,
      candidates: sameScope(current) ? current.candidates : [],
      outline: sameScope(current) ? current.outline : null,
      isLoading: true,
      error: null,
    }));

    try {
      const response = await api.chapterBeat(projectId, documentId, { signal: controller.signal });
      if (!isCurrentRequest()) return;
      setState({
        projectId,
        documentId,
        candidates: response.candidates,
        outline: response.outline,
        isLoading: false,
        error: null,
      });
    } catch (reason) {
      if (!isCurrentRequest()) return;
      setState((current) => ({
        projectId,
        documentId,
        candidates: sameScope(current) ? current.candidates : [],
        outline: sameScope(current) ? current.outline : null,
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

  const stateIsCurrent = state.projectId === projectId && state.documentId === documentId;
  return {
    candidates: stateIsCurrent ? state.candidates : [],
    outline: stateIsCurrent ? state.outline : null,
    isLoading: stateIsCurrent ? state.isLoading : true,
    error: stateIsCurrent ? state.error : null,
    refresh: load,
  };
}
