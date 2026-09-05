import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { HttpError } from "@/app/api";

import { toErrorMessage } from "./toErrorMessage";

export type LazyResourcePhase = "idle" | "pending" | "success" | "failure";

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

function resolveStateAction<T>(current: T, action: SetStateAction<T>): T {
  return typeof action === "function" ? (action as (value: T) => T)(current) : action;
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
  const phaseRef = useRef<LazyResourcePhase>("idle");
  const [state, setState] = useState<LazyResourceState<T>>(() => ({
    projectId,
    phase: "idle",
    data: empty,
    error: null,
  }));

  useEffect(() => {
    activeRef.current = active;
    phaseRef.current = state.projectId === projectId ? state.phase : "idle";
  }, [active, projectId, state.phase, state.projectId]);

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
    phaseRef.current = "pending";
    setState((current) => ({ ...current, projectId, phase: "pending", error: null }));

    ownedRequest.promise = (async () => {
      try {
        const data = await request(controller.signal);
        if (!isCurrent(ownedRequest)) return;
        phaseRef.current = "success";
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
            phaseRef.current = "failure";
            setState((current) => ({
              ...current,
              projectId,
              phase: "failure",
              error: missingResourceMessage,
            }));
          } catch (recheckReason) {
            if (!isCurrent(ownedRequest)) return;
            phaseRef.current = "failure";
            setState((current) => ({
              ...current,
              projectId,
              phase: "failure",
              error: toErrorMessage(recheckReason, loadErrorMessage),
            }));
          }
          return;
        }
        phaseRef.current = "failure";
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
    if (active && phaseRef.current === "idle") void load();
    return () => {
      const inFlight = requestRef.current;
      if (inFlight) {
        requestRef.current = null;
        inFlight.controller.abort();
        epochRef.current += 1;
        phaseRef.current = "idle";
        setState((current) =>
          current.phase === "pending"
            ? { ...current, phase: current.error ? "failure" : "idle" }
            : current,
        );
      }
    };
  }, [active, load]);

  const setData = useCallback<Dispatch<SetStateAction<T>>>(
    (nextData) => {
      const inFlight = requestRef.current;
      if (inFlight) {
        requestRef.current = null;
        inFlight.controller.abort();
        epochRef.current += 1;
      }
      phaseRef.current = "success";
      setState((current) => ({
        projectId,
        phase: "success",
        data: resolveStateAction(current.projectId === projectId ? current.data : empty, nextData),
        error: null,
      }));
    },
    [empty, projectId],
  );

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
  };
}
