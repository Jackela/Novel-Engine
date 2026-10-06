import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useCallback, useEffect, useReducer, useRef } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import { toErrorMessage } from "./toErrorMessage";

export interface SearchResult {
  readonly document_id: string;
  readonly title: string;
  readonly excerpt: string;
  /** DR-029: the first reduced match element the editor locates in the body. */
  readonly match_term: string;
}

/** DR-029: the page-level intent that opens a document and locates one hit. */
export interface SearchReveal {
  readonly documentId: string;
  readonly term: string;
  /** Monotonic token so re-clicking the same hit re-runs the editor find. */
  readonly token: number;
}

interface SearchState {
  readonly projectId: string;
  readonly search: string;
  readonly isSearching: boolean;
  readonly isLoadingMore: boolean;
  readonly searchResults: SearchResult[];
  /** The server's honest project-wide match count of the shown query. */
  readonly total: number;
  /** The offset walking the remaining pages; null when all rows arrived. */
  readonly nextOffset: number | null;
  /** The query (as typed) whose page is shown; null before any success. */
  readonly searchedQuery: string | null;
}

type SearchAction =
  | { readonly type: "searchChanged"; readonly projectId: string; readonly search: string }
  | { readonly type: "searchStarted"; readonly projectId: string }
  | {
      readonly type: "searchSucceeded";
      readonly projectId: string;
      readonly query: string;
      readonly results: SearchResult[];
      readonly total: number;
      readonly nextOffset: number | null;
    }
  | { readonly type: "searchFailed"; readonly projectId: string }
  | { readonly type: "moreStarted"; readonly projectId: string }
  | {
      readonly type: "moreSucceeded";
      readonly projectId: string;
      readonly results: SearchResult[];
      readonly total: number;
      readonly nextOffset: number | null;
    }
  | { readonly type: "moreFailed"; readonly projectId: string };

function emptySearchState(projectId: string): SearchState {
  return {
    projectId,
    search: "",
    isSearching: false,
    isLoadingMore: false,
    searchResults: [],
    total: 0,
    nextOffset: null,
    searchedQuery: null,
  };
}

function reduceSearchState(state: SearchState, action: SearchAction): SearchState {
  const current = state.projectId === action.projectId ? state : emptySearchState(action.projectId);
  switch (action.type) {
    case "searchChanged":
      return action.search.trim()
        ? { ...current, search: action.search }
        : {
            ...current,
            search: action.search,
            searchResults: [],
            total: 0,
            nextOffset: null,
            searchedQuery: null,
          };
    case "searchStarted":
      return { ...current, isSearching: true, isLoadingMore: false };
    case "searchSucceeded":
      return {
        ...current,
        isSearching: false,
        searchResults: action.results,
        total: action.total,
        nextOffset: action.nextOffset,
        searchedQuery: action.query,
      };
    case "searchFailed":
      return { ...current, isSearching: false };
    case "moreStarted":
      return { ...current, isLoadingMore: true };
    case "moreSucceeded":
      return {
        ...current,
        isLoadingMore: false,
        searchResults: [...current.searchResults, ...action.results],
        total: action.total,
        nextOffset: action.nextOffset,
      };
    case "moreFailed":
      return { ...current, isLoadingMore: false };
  }
  const unreachable: never = action;
  return unreachable;
}

/**
 * Project-scoped ranked search (DR-029): the first page plus `next_offset`
 * paging, whose appended pages keep the server's `(rank, document_id)` order
 * duplicate-free. `searchedEmpty` marks the one state the navigator renders a
 * hint for: a completed search whose query is still the typed input and whose
 * honest result set is empty.
 */
export function useStudioSearch(
  projectId: string,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const activeProjectIdRef = useRef<string | null>(null);
  const controllerRef = useRef<{
    readonly projectId: string;
    readonly controller: AbortController;
  } | null>(null);
  const moreInFlightRef = useRef(false);
  const requestEpochRef = useRef(0);
  const [state, dispatch] = useReducer(reduceSearchState, projectId, emptySearchState);
  // #446: mirrors the latest dispatched `search` so functional updates and
  // submits resolve against the committed value instead of the render-phase
  // closure (which goes stale when several updates land in one batch).
  const searchRef = useRef<{ projectId: string | null; value: string }>({
    projectId: null,
    value: "",
  });
  // DR-029: the last delivered page's query and offset, read by `loadMore`
  // without a stale render closure.
  const pageRef = useRef<{ projectId: string | null; query: string; nextOffset: number | null }>({
    projectId: null,
    query: "",
    nextOffset: null,
  });

  useEffect(() => {
    activeProjectIdRef.current = projectId;
    searchRef.current = { projectId, value: "" };
    pageRef.current = { projectId, query: "", nextOffset: null };
    return () => {
      if (activeProjectIdRef.current === projectId) {
        activeProjectIdRef.current = null;
      }
      if (searchRef.current.projectId === projectId) {
        searchRef.current = { projectId: null, value: "" };
      }
      if (pageRef.current.projectId === projectId) {
        pageRef.current = { projectId: null, query: "", nextOffset: null };
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
      controllerRef.current?.controller.abort();
      controllerRef.current = null;
      requestEpochRef.current += 1;
      if (!query.trim()) {
        pageRef.current = { projectId, query: "", nextOffset: null };
        dispatch({ type: "searchChanged", projectId, search: query });
        return;
      }
      const controller = new AbortController();
      controllerRef.current = { projectId, controller };
      const requestEpoch = requestEpochRef.current;
      const isCurrentRequest = () =>
        !controller.signal.aborted &&
        requestEpochRef.current === requestEpoch &&
        activeProjectIdRef.current === projectId;
      dispatch({ type: "searchStarted", projectId });

      try {
        const response = await api.search(projectId, query, { signal: controller.signal });
        if (!isCurrentRequest()) return;
        pageRef.current = { projectId, query, nextOffset: response.next_offset };
        dispatch({
          type: "searchSucceeded",
          projectId,
          query,
          results: response.results,
          total: response.total,
          nextOffset: response.next_offset,
        });
        setError(null);
      } catch (reason) {
        if (!isCurrentRequest()) return;
        setError(toErrorMessage(reason, translateActive("errors.search")));
        dispatch({ type: "searchFailed", projectId });
      } finally {
        if (controllerRef.current?.controller === controller) {
          controllerRef.current = null;
        }
      }
    },
    [projectId, setError],
  );

  /** Append the next ranked page; single-flight and stale-project guarded. */
  const loadMoreResults = useCallback(async () => {
    if (activeProjectIdRef.current !== projectId) return;
    const page = pageRef.current;
    if (page.projectId !== projectId || page.nextOffset === null) return;
    if (moreInFlightRef.current) return;
    moreInFlightRef.current = true;
    const controller = new AbortController();
    controllerRef.current = { projectId, controller };
    const requestEpoch = ++requestEpochRef.current;
    const isCurrentRequest = () =>
      !controller.signal.aborted &&
      requestEpochRef.current === requestEpoch &&
      activeProjectIdRef.current === projectId;
    dispatch({ type: "moreStarted", projectId });

    try {
      const response = await api.search(projectId, page.query, {
        offset: page.nextOffset,
        signal: controller.signal,
      });
      if (!isCurrentRequest()) return;
      pageRef.current = { projectId, query: page.query, nextOffset: response.next_offset };
      dispatch({
        type: "moreSucceeded",
        projectId,
        results: response.results,
        total: response.total,
        nextOffset: response.next_offset,
      });
      setError(null);
    } catch (reason) {
      if (!isCurrentRequest()) return;
      setError(toErrorMessage(reason, translateActive("errors.search")));
      dispatch({ type: "moreFailed", projectId });
    } finally {
      moreInFlightRef.current = false;
      if (controllerRef.current?.controller === controller) {
        controllerRef.current = null;
      }
    }
  }, [projectId, setError]);

  const stateIsCurrent = state.projectId === projectId;
  const search = stateIsCurrent ? state.search : "";
  const isSearching = stateIsCurrent ? state.isSearching : false;
  const isLoadingMore = stateIsCurrent ? state.isLoadingMore : false;
  const searchResults = stateIsCurrent ? state.searchResults : [];
  const total = stateIsCurrent ? state.total : 0;
  const nextOffset = stateIsCurrent ? state.nextOffset : null;
  const hasMoreResults = nextOffset !== null;
  const searchedEmpty =
    stateIsCurrent &&
    !state.isSearching &&
    state.searchedQuery !== null &&
    state.searchedQuery === search &&
    searchResults.length === 0;

  return {
    search,
    setSearch,
    isSearching,
    isLoadingMoreResults: isLoadingMore,
    searchResults,
    searchTotal: total,
    hasMoreResults,
    searchedEmpty,
    runSearch,
    loadMoreResults,
  };
}
