import { useCallback, useEffect, useRef, useState } from "react";

import { api, HttpError } from "@/app/api";
import type { SetupStatus } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";

interface EntryBootstrapState {
  readonly setup: SetupStatus | null;
  readonly error: string | null;
  readonly isLoading: boolean;
}

const INITIAL_STATE: EntryBootstrapState = {
  setup: null,
  error: null,
  isLoading: true,
};

/** Owns the entry session/setup reads and rejects every stale completion. */
export function useEntryBootstrap(onAuthenticated: () => void) {
  const [state, setState] = useState<EntryBootstrapState>(INITIAL_STATE);
  const mountedRef = useRef(false);
  const requestRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const inFlightReloadRef = useRef<Promise<void> | null>(null);

  const reload = useCallback((): Promise<void> => {
    if (inFlightReloadRef.current !== null) return inFlightReloadRef.current;
    const run = (async () => {
      const request = requestRef.current + 1;
      requestRef.current = request;
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      const isCurrent = () =>
        mountedRef.current && requestRef.current === request && !controller.signal.aborted;

      setState((current) => ({ ...current, isLoading: true }));
      try {
        try {
          await api.session({ signal: controller.signal });
          if (isCurrent()) onAuthenticated();
          return;
        } catch (reason) {
          if (!isCurrent()) return;
          if (!(reason instanceof HttpError) || reason.status !== 401) throw reason;
        }

        const setup = await api.setupStatus({ signal: controller.signal });
        if (isCurrent()) setState({ setup, error: null, isLoading: false });
      } catch (reason) {
        if (!isCurrent()) return;
        setState({
          setup: null,
          error: toErrorMessage(reason, "Unable to check the local owner."),
          isLoading: false,
        });
      }
    })();

    let tracked: Promise<void>;
    tracked = run.finally(() => {
      if (inFlightReloadRef.current === tracked) inFlightReloadRef.current = null;
    });
    inFlightReloadRef.current = tracked;
    return tracked;
  }, [onAuthenticated]);

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

  const markOwnerConfigured = useCallback(() => {
    setState((current) =>
      current.setup === null
        ? current
        : { ...current, setup: { ...current.setup, owner_configured: true } },
    );
  }, []);

  return { ...state, reload, mountedRef, markOwnerConfigured };
}
