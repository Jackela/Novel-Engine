import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useCallback, useReducer, useRef } from "react";

import { api } from "@/app/api";

import { toErrorMessage } from "./toErrorMessage";

interface SearchResult {
  readonly document_id: string;
  readonly title: string;
  readonly excerpt: string;
}

interface SearchState {
  readonly search: string;
  readonly isSearching: boolean;
  readonly searchResults: SearchResult[];
}

type SearchAction =
  | { readonly type: "searchChanged"; readonly search: string }
  | { readonly type: "searchStarted" }
  | { readonly type: "searchSucceeded"; readonly results: SearchResult[] }
  | { readonly type: "searchFailed" };

function reduceSearchState(state: SearchState, action: SearchAction): SearchState {
  switch (action.type) {
    case "searchChanged":
      return {
        ...state,
        search: action.search,
        searchResults: action.search.trim() ? state.searchResults : [],
      };
    case "searchStarted":
      return { ...state, isSearching: true };
    case "searchSucceeded":
      return { ...state, isSearching: false, searchResults: action.results };
    case "searchFailed":
      return { ...state, isSearching: false };
  }
  const unreachable: never = action;
  return unreachable;
}

export function useStudioSearch(
  projectId: string,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const [{ search, isSearching, searchResults }, dispatch] = useReducer(reduceSearchState, {
    search: "",
    isSearching: false,
    searchResults: [],
  });
  // #446: mirrors the latest dispatched `search` so functional updates and
  // submits resolve against the committed value instead of the render-phase
  // closure (which goes stale when several updates land in one batch).
  const searchRef = useRef(search);

  const setSearch = useCallback<Dispatch<SetStateAction<string>>>((nextSearch) => {
    const resolved = typeof nextSearch === "function" ? nextSearch(searchRef.current) : nextSearch;
    searchRef.current = resolved;
    dispatch({ type: "searchChanged", search: resolved });
  }, []);

  const runSearch = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      const query = searchRef.current;
      if (!query.trim()) {
        dispatch({ type: "searchChanged", search: query });
        return;
      }
      dispatch({ type: "searchStarted" });
      try {
        const response = await api.search(projectId, query);
        dispatch({ type: "searchSucceeded", results: response.results });
      } catch (reason) {
        setError(toErrorMessage(reason, "Search failed."));
        dispatch({ type: "searchFailed" });
      }
    },
    [projectId, setError],
  );

  return { search, setSearch, isSearching, searchResults, runSearch };
}
