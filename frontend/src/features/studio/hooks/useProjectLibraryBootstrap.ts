import { useCallback, useEffect, useRef, useState } from "react";

import { api, HttpError } from "@/app/api";
import type { ProjectCatalogItem } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";

interface ProjectLibraryBootstrapState {
  readonly projects: ProjectCatalogItem[];
  readonly nextCursor: string | null;
  readonly error: string | null;
  readonly olderError: string | null;
  readonly isLoading: boolean;
  readonly isLoadingOlder: boolean;
  readonly hasLoaded: boolean;
}

const INITIAL_STATE: ProjectLibraryBootstrapState = {
  projects: [],
  nextCursor: null,
  error: null,
  olderError: null,
  isLoading: true,
  isLoadingOlder: false,
  hasLoaded: false,
};

function appendUniqueProjects(
  current: readonly ProjectCatalogItem[],
  older: readonly ProjectCatalogItem[],
): ProjectCatalogItem[] {
  const known = new Set(current.map((project) => project.id));
  const uniqueOlder = older.filter((project) => {
    if (known.has(project.id)) return false;
    known.add(project.id);
    return true;
  });
  return [...current, ...uniqueOlder];
}

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
  const olderRef = useRef<{ cursor: string; promise: Promise<void> } | null>(null);

  const reload = useCallback((): Promise<void> => {
    if (inFlightReloadRef.current !== null) return inFlightReloadRef.current;
    const run = (async () => {
      olderRef.current = null;
      const request = requestRef.current + 1;
      requestRef.current = request;
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      const isCurrent = () =>
        mountedRef.current && requestRef.current === request && !controller.signal.aborted;

      setState((current) => ({
        ...current,
        isLoading: true,
        olderError: null,
        isLoadingOlder: false,
      }));
      try {
        await api.session({ signal: controller.signal });
        if (!isCurrent()) return;
        const response = await api.projects({ signal: controller.signal });
        if (isCurrent()) {
          setState({
            projects: response.projects,
            nextCursor: response.next_cursor,
            error: null,
            olderError: null,
            isLoading: false,
            isLoadingOlder: false,
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
          isLoadingOlder: false,
        }));
      }
    })();

    let tracked: Promise<void>;
    tracked = run.finally(() => {
      if (inFlightReloadRef.current === tracked) inFlightReloadRef.current = null;
    });
    inFlightReloadRef.current = tracked;
    return tracked;
  }, [onUnauthenticated]);

  const loadOlder = useCallback((): Promise<void> => {
    const activeOlder = olderRef.current;
    if (activeOlder !== null) return activeOlder.promise;
    const cursor = state.nextCursor;
    if (cursor === null || state.isLoading || state.isLoadingOlder) return Promise.resolve();
    const request = requestRef.current + 1;
    requestRef.current = request;
    const controller = new AbortController();
    controllerRef.current = controller;
    const isCurrent = () =>
      mountedRef.current && requestRef.current === request && !controller.signal.aborted;

    setState((current) => ({ ...current, isLoadingOlder: true, olderError: null }));
    let promise: Promise<void> = Promise.resolve();
    promise = (async () => {
      try {
        const response = await api.projects({ cursor, signal: controller.signal });
        if (!isCurrent()) return;
        setState((current) => ({
          ...current,
          projects: appendUniqueProjects(current.projects, response.projects),
          nextCursor: response.next_cursor,
          isLoadingOlder: false,
          olderError: null,
        }));
      } catch (reason) {
        if (!isCurrent()) return;
        if (reason instanceof HttpError && reason.status === 401) {
          onUnauthenticated();
          return;
        }
        setState((current) => ({
          ...current,
          isLoadingOlder: false,
          olderError: toErrorMessage(reason, "Unable to load older projects."),
        }));
      } finally {
        if (olderRef.current?.promise === promise) olderRef.current = null;
      }
    })();
    olderRef.current = { cursor, promise };
    return promise;
  }, [onUnauthenticated, state.isLoading, state.isLoadingOlder, state.nextCursor]);

  useEffect(() => {
    mountedRef.current = true;
    void reload();
    return () => {
      mountedRef.current = false;
      requestRef.current += 1;
      inFlightReloadRef.current = null;
      olderRef.current = null;
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, [reload]);

  return { ...state, reload, loadOlder, mountedRef };
}
