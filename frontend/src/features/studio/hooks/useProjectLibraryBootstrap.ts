import { useCallback, useEffect, useRef, useState } from "react";

import { api, HttpError } from "@/app/api";
import type { ProjectsPage } from "@/app/projectShellContract";
import type { ProjectCatalogItem } from "@/app/types/studio";

import { appendUniqueById, useKeysetOlderPages } from "./keysetHistory";
import { toErrorMessage } from "./toErrorMessage";

interface ProjectLibraryBootstrapState {
  readonly projects: ProjectCatalogItem[];
  readonly nextCursor: string | null;
  readonly error: string | null;
  readonly isLoading: boolean;
  readonly hasLoaded: boolean;
}

const INITIAL_STATE: ProjectLibraryBootstrapState = {
  projects: [],
  nextCursor: null,
  error: null,
  isLoading: true,
  hasLoaded: false,
};

/**
 * Verifies the session before loading projects and owns the bounded catalog
 * reads: one cursorless first page, with explicit older-page continuation.
 */
export function useProjectLibraryBootstrap(onUnauthenticated: () => void) {
  const [state, setState] = useState<ProjectLibraryBootstrapState>(INITIAL_STATE);
  const mountedRef = useRef(false);
  const requestRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const inFlightReloadRef = useRef<Promise<void> | null>(null);

  const olderPages = useKeysetOlderPages<ProjectsPage>({
    cleanupKey: "project-library",
    isEnabled: () => mountedRef.current,
    isBlocked: () => state.isLoading,
    nextCursor: state.nextCursor,
    fetchPage: (cursor, signal) => api.projects({ cursor, signal }),
    commitPage: (page) =>
      setState((current) => ({
        ...current,
        projects: appendUniqueById(current.projects, page.projects, (project) => project.id),
        nextCursor: page.next_cursor,
      })),
    onSessionLost: onUnauthenticated,
    busyErrorMessage: "Unable to load older projects.",
  });
  const abortInFlightOlder = olderPages.abortInFlight;

  const reload = useCallback((): Promise<void> => {
    if (inFlightReloadRef.current !== null) return inFlightReloadRef.current;
    const run = (async () => {
      abortInFlightOlder();
      const request = requestRef.current + 1;
      requestRef.current = request;
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      const isCurrent = () =>
        mountedRef.current && requestRef.current === request && !controller.signal.aborted;

      setState((current) => ({ ...current, isLoading: true }));
      try {
        await api.session({ signal: controller.signal });
        if (!isCurrent()) return;
        const response = await api.projects({ signal: controller.signal });
        if (isCurrent()) {
          setState({
            projects: response.projects,
            nextCursor: response.next_cursor,
            error: null,
            isLoading: false,
            hasLoaded: true,
          });
        }
      } catch (reason) {
        if (!isCurrent()) return;
        if (reason instanceof HttpError && reason.status === 401) {
          onUnauthenticated();
          return;
        }
        setState((current) => ({
          ...current,
          error: toErrorMessage(reason, "Unable to load projects."),
          isLoading: false,
        }));
      } finally {
        // First-page busy cleanup never depends on request currency: a
        // superseded read still releases the busy flag it raised.
        setState((current) => (current.isLoading ? { ...current, isLoading: false } : current));
      }
    })();

    let tracked: Promise<void>;
    tracked = run.finally(() => {
      if (inFlightReloadRef.current === tracked) inFlightReloadRef.current = null;
    });
    inFlightReloadRef.current = tracked;
    return tracked;
  }, [abortInFlightOlder, onUnauthenticated]);

  useEffect(() => {
    mountedRef.current = true;
    void reload();
    return () => {
      mountedRef.current = false;
      requestRef.current += 1;
      inFlightReloadRef.current = null;
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, [reload]);

  return {
    ...state,
    isLoadingOlder: olderPages.isLoadingOlder,
    olderError: olderPages.olderError,
    reload,
    loadOlder: olderPages.loadOlder,
    mountedRef,
  };
}
