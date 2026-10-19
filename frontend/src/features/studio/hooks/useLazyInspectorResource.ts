import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { HttpError } from "@/app/api";

import { resolveStateAction } from "./resolveStateAction";
import { toErrorMessage } from "./toErrorMessage";

type LazyResourcePhase = "idle" | "pending" | "success" | "failure";

interface LazyResourceState<T> {
  readonly projectId: string;
  readonly phase: LazyResourcePhase;
  readonly data: T;
  readonly error: string | null;
}

interface LazyResourceRequest {
  readonly controller: AbortController;
  readonly epoch: number;
  promise: Promise<void>;
}

interface UseLazyInspectorResourceOptions<T> {
  readonly active: boolean;
  readonly projectId: string;
  readonly empty: T;
  readonly request: (signal: AbortSignal) => Promise<T>;
  readonly recheckProject: (signal: AbortSignal) => Promise<boolean>;
  readonly onSessionLost: () => void;
  readonly missingResourceMessage: string;
  readonly loadErrorMessage: string;
}

/**
 * One URL-selected Inspector history owns one request, cache, error and retry.
 * Inactive panels neither prefetch nor publish late transport outcomes.
 */
export function useLazyInspectorResource<T>({
  active,
  projectId,
  empty,
  request,
  recheckProject,
  onSessionLost,
  missingResourceMessage,
  loadErrorMessage,
}: UseLazyInspectorResourceOptions<T>) {
  const activeRef = useRef(active);
  const epochRef = useRef(0);
  const requestRef = useRef<LazyResourceRequest | null>(null);
  const [state, setState] = useState<LazyResourceState<T>>(() => ({
    projectId,
    phase: "idle",
    data: empty,
    error: null,
  }));

  useEffect(() => {
    activeRef.current = active;
  }, [active]);

  const isCurrent = useCallback(
    (ownedRequest: LazyResourceRequest) =>
      activeRef.current &&
      !ownedRequest.controller.signal.aborted &&
      requestRef.current === ownedRequest &&
      epochRef.current === ownedRequest.epoch,
    [],
  );

  const load = useCallback((): Promise<void> => {
    if (!activeRef.current) return Promise.resolve();
    const inFlight = requestRef.current;
    if (inFlight && !inFlight.controller.signal.aborted) return inFlight.promise;

    const controller = new AbortController();
    const ownedRequest: LazyResourceRequest = {
      controller,
      epoch: ++epochRef.current,
      promise: Promise.resolve(),
    };
    requestRef.current = ownedRequest;
    setState((current) => ({ ...current, projectId, phase: "pending", error: null }));

    ownedRequest.promise = (async () => {
      try {
        const data = await request(controller.signal);
        if (!isCurrent(ownedRequest)) return;
        setState({ projectId, phase: "success", data, error: null });
      } catch (reason) {
        if (!isCurrent(ownedRequest)) return;
        if (reason instanceof HttpError && reason.status === 401) {
          onSessionLost();
          return;
        }
        if (reason instanceof HttpError && reason.status === 404) {
          try {
            const projectExists = await recheckProject(controller.signal);
            if (!isCurrent(ownedRequest) || !projectExists) return;
            setState((current) => ({
              ...current,
              projectId,
              phase: "failure",
              error: missingResourceMessage,
            }));
          } catch (recheckReason) {
            if (!isCurrent(ownedRequest)) return;
            setState((current) => ({
              ...current,
              projectId,
              phase: "failure",
              error: toErrorMessage(recheckReason, loadErrorMessage),
            }));
          }
          return;
        }
        setState((current) => ({
          ...current,
          projectId,
          phase: "failure",
          error: toErrorMessage(reason, loadErrorMessage),
        }));
      } finally {
        if (requestRef.current === ownedRequest) requestRef.current = null;
      }
    })();

    return ownedRequest.promise;
  }, [
    isCurrent,
    loadErrorMessage,
    missingResourceMessage,
    onSessionLost,
    projectId,
    recheckProject,
    request,
  ]);

  useEffect(() => {
    if (active && (state.projectId !== projectId || state.phase === "idle")) void load();
  }, [active, load, projectId, state.phase, state.projectId]);

  useEffect(() => {
    if (!active) return;
    return () => {
      const inFlight = requestRef.current;
      if (inFlight) {
        requestRef.current = null;
        inFlight.controller.abort();
        epochRef.current += 1;
        setState((current) =>
          current.projectId === projectId && current.phase === "pending"
            ? { ...current, phase: current.error ? "failure" : "idle" }
            : current,
        );
      }
    };
  }, [active, projectId]);

  const setData = useCallback<Dispatch<SetStateAction<T>>>(
    (nextData) => {
      const inFlight = requestRef.current;
      if (inFlight) {
        requestRef.current = null;
        inFlight.controller.abort();
        epochRef.current += 1;
      }
      setState((current) => ({
        projectId,
        phase: "success",
        data: resolveStateAction(current.projectId === projectId ? current.data : empty, nextData),
        error: null,
      }));
    },
    [empty, projectId],
  );

  /** Discard this resource era; only an active consumer starts its replacement read. */
  const invalidate = useCallback((): void => {
    const inFlight = requestRef.current;
    requestRef.current = null;
    epochRef.current += 1;
    inFlight?.controller.abort();
    setState({ projectId, phase: "idle", data: empty, error: null });
  }, [empty, projectId]);

  const current =
    state.projectId === projectId
      ? state
      : { projectId, phase: "idle" as const, data: empty, error: null };
  return {
    data: current.data,
    error: current.error,
    phase: current.phase,
    initialized: current.phase === "success",
    isLoading: active && (current.phase === "idle" || current.phase === "pending"),
    retry: load,
    setData,
    invalidate,
  };
}
