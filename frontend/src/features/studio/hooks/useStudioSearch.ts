import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useCallback, useEffect, useReducer, useRef } from "react";

import { api } from "@/app/api";

import { toErrorMessage } from "./toErrorMessage";

interface SearchResult {
  readonly document_id: string;
  readonly title: string;
  readonly excerpt: string;
}

interface SearchState {
  readonly projectId: string;
  readonly search: string;
  readonly isSearching: boolean;
  readonly searchResults: SearchResult[];
}

type SearchAction =
  | { readonly type: "searchChanged"; readonly projectId: string; readonly search: string }
  | { readonly type: "searchStarted"; readonly projectId: string }
  | {
      readonly type: "searchSucceeded";
      readonly projectId: string;
      readonly results: SearchResult[];
    }
  | { readonly type: "searchFailed"; readonly projectId: string };

function emptySearchState(projectId: string): SearchState {
  return { projectId, search: "", isSearching: false, searchResults: [] };
}

function reduceSearchState(state: SearchState, action: SearchAction): SearchState {
  const current = state.projectId === action.projectId ? state : emptySearchState(action.projectId);
  switch (action.type) {
    case "searchChanged":
      return {
        ...current,
        search: action.search,
        searchResults: action.search.trim() ? current.searchResults : [],
      };
    case "searchStarted":
      return { ...current, isSearching: true };
    case "searchSucceeded":
      return { ...current, isSearching: false, searchResults: action.results };
    case "searchFailed":
      return { ...current, isSearching: false };
  }
  const unreachable: never = action;
  return unreachable;
}

export function useStudioSearch(
  projectId: string,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const activeProjectIdRef = useRef<string | null>(null);
  const controllerRef = useRef<{
    readonly projectId: string;
    readonly controller: AbortController;
  } | null>(null);
  const requestEpochRef = useRef(0);
  const [state, dispatch] = useReducer(reduceSearchState, projectId, emptySearchState);
  // #446: mirrors the latest dispatched `search` so functional updates and
  // submits resolve against the committed value instead of the render-phase
  // closure (which goes stale when several updates land in one batch).
  const searchRef = useRef<{ projectId: string | null; value: string }>({
    projectId: null,
    value: "",
  });

  useEffect(() => {
    activeProjectIdRef.current = projectId;
    searchRef.current = { projectId, value: "" };
    return () => {
      if (activeProjectIdRef.current === projectId) {
        activeProjectIdRef.current = null;
      }
      if (searchRef.current.projectId === projectId) {
        searchRef.current = { projectId: null, value: "" };
      }
      if (controllerRef.current?.projectId === projectId) {
        controllerRef.current.controller.abort();
        controllerRef.current = null;
      }
      requestEpochRef.current += 1;
    };
  }, [projectId]);

  const setSearch = useCallback<Dispatch<SetStateAction<string>>>(
    (nextSearch) => {
      if (activeProjectIdRef.current !== projectId) return;
      const currentSearch =
        searchRef.current.projectId === projectId ? searchRef.current.value : "";
      const resolved = typeof nextSearch === "function" ? nextSearch(currentSearch) : nextSearch;
      searchRef.current = { projectId, value: resolved };
      dispatch({ type: "searchChanged", projectId, search: resolved });
    },
    [projectId],
  );

  const runSearch = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (activeProjectIdRef.current !== projectId) return;
      const query = searchRef.current.projectId === projectId ? searchRef.current.value : "";
      if (!query.trim()) {
        controllerRef.current?.controller.abort();
        requestEpochRef.current += 1;
        dispatch({ type: "searchChanged", projectId, search: query });
        return;
      }
      controllerRef.current?.controller.abort();
      const controller = new AbortController();
      controllerRef.current = { projectId, controller };
      const requestEpoch = ++requestEpochRef.current;
      dispatch({ type: "searchStarted", projectId });

      const isCurrentRequest = () =>
        !controller.signal.aborted &&
        requestEpochRef.current === requestEpoch &&
        activeProjectIdRef.current === projectId;

      try {
        const response = await api.search(projectId, query, { signal: controller.signal });
        if (!isCurrentRequest()) return;
        dispatch({ type: "searchSucceeded", projectId, results: response.results });
        setError(null);
      } catch (reason) {
        if (!isCurrentRequest()) return;
        setError(toErrorMessage(reason, "Search failed."));
        dispatch({ type: "searchFailed", projectId });
      }
    },
    [projectId, setError],
  );

  const stateIsCurrent = state.projectId === projectId;
  const search = stateIsCurrent ? state.search : "";
  const isSearching = stateIsCurrent ? state.isSearching : false;
  const searchResults = stateIsCurrent ? state.searchResults : [];

  return { search, setSearch, isSearching, searchResults, runSearch };
}
