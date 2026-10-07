import { useCallback, useEffect, useRef, useState } from "react";

import { toErrorMessage } from "./toErrorMessage";

interface ScopedProjectResourceState<T> {
  readonly projectId: string;
  readonly data: T | null;
  readonly isLoading: boolean;
  readonly error: string | null;
}

interface UseScopedProjectResourceOptions<T> {
  /** Whether the owning inspector tab is selected; activation triggers the first read. */
  readonly active: boolean;
  /** The project the resource is scoped to; a change discards the previous scope. */
  readonly projectId: string;
  /** The transport read for one signal; it must be stable per project. */
  readonly load: (signal: AbortSignal) => Promise<T>;
  /** Localized fallback for a failure whose reason carries no stable error code. */
  readonly loadErrorMessage: string;
}

export interface ScopedProjectResource<T> {
  readonly data: T | null;
  readonly isLoading: boolean;
  readonly error: string | null;
  readonly reload: () => Promise<void>;
}

/**
 * One project-scoped, lazily loaded inspector resource (#377 usage, #653
 * writing stats): the first activation of the tab reads it once, an explicit
 * `reload` aborts whatever is in flight and supersedes it, and a project
 * switch or unmount aborts the outstanding read, so a reverse-order
 * completion can never publish a previous project's payload.
 *
 * Scope lives in three refs and one epoch counter: the active-project ref
 * gates every publish and clears on the scope effect's cleanup, the controller
 * ref holds at most one in-flight read for the current project, and the epoch
 * invalidates closures captured before the most recent abort. `data`,
 * `isLoading` and `error` are projected through the scope check, so a switched
 * project reads as unloaded instead of showing the previous project's payload.
 *
 * Failure semantics: transport failures reduce to one localized message
 * through `toErrorMessage` (a code-bearing reason keeps its dictionary
 * message, anything else keeps its own) and stay published until a read
 * succeeds. Aborted, superseded and out-of-scope reads resolve to nothing at
 * all — they publish neither data nor error.
 *
 * This is deliberately not built on `useLazyInspectorResource`: that hook owns
 * a phase machine, joins a duplicate refresh to the in-flight read, and treats
 * 404 as a project recheck plus 401 as session loss. These two resources need
 * the opposite refresh contract (a duplicate refresh aborts and supersedes the
 * pending read) and no session-loss branch, so sharing that base would mean
 * duplicating its semantics rather than reusing them.
 */
export function useScopedProjectResource<T>({
  active,
  projectId,
  load,
  loadErrorMessage,
}: UseScopedProjectResourceOptions<T>): ScopedProjectResource<T> {
  const activeProjectIdRef = useRef<string | null>(null);
  const controllerRef = useRef<{
    readonly projectId: string;
    readonly controller: AbortController;
  } | null>(null);
  const requestEpochRef = useRef(0);
  const autoLoadedProjectIdRef = useRef<string | null>(null);
  const [state, setState] = useState<ScopedProjectResourceState<T>>(() => ({
    projectId,
    data: null,
    isLoading: false,
    error: null,
  }));

  useEffect(() => {
    activeProjectIdRef.current = projectId;
    return () => {
      if (activeProjectIdRef.current === projectId) {
        activeProjectIdRef.current = null;
      }
      if (controllerRef.current?.projectId === projectId) {
        controllerRef.current.controller.abort();
        controllerRef.current = null;
      }
      if (autoLoadedProjectIdRef.current === projectId) {
        autoLoadedProjectIdRef.current = null;
      }
      requestEpochRef.current += 1;
    };
  }, [projectId]);

  const reload = useCallback(async () => {
    if (activeProjectIdRef.current !== projectId) return;
    controllerRef.current?.controller.abort();
    const controller = new AbortController();
    controllerRef.current = { projectId, controller };
    const requestEpoch = ++requestEpochRef.current;
    setState((current) => ({
      projectId,
      data: current.projectId === projectId ? current.data : null,
      isLoading: true,
      error: current.projectId === projectId ? current.error : null,
    }));

    const isCurrentRequest = () =>
      !controller.signal.aborted &&
      requestEpochRef.current === requestEpoch &&
      activeProjectIdRef.current === projectId;

    try {
      const response = await load(controller.signal);
      if (!isCurrentRequest()) return;
      setState({ projectId, data: response, isLoading: false, error: null });
    } catch (reason) {
      if (!isCurrentRequest()) return;
      setState((current) => ({
        projectId,
        data: current.projectId === projectId ? current.data : null,
        isLoading: false,
        error: toErrorMessage(reason, loadErrorMessage),
      }));
    }
  }, [load, loadErrorMessage, projectId]);

  useEffect(() => {
    if (active && autoLoadedProjectIdRef.current !== projectId) {
      autoLoadedProjectIdRef.current = projectId;
      void reload();
    }
  }, [active, projectId, reload]);

  const stateIsCurrent = state.projectId === projectId;
  return {
    data: stateIsCurrent ? state.data : null,
    isLoading: stateIsCurrent ? state.isLoading : false,
    error: stateIsCurrent ? state.error : null,
    reload,
  };
}
