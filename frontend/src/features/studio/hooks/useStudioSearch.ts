import { useCallback, useReducer } from 'react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';

import { api } from '@/app/api';

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
  | { readonly type: 'searchChanged'; readonly search: string }
  | { readonly type: 'searchStarted' }
  | { readonly type: 'searchSucceeded'; readonly results: SearchResult[] }
  | { readonly type: 'searchFailed' };

function reduceSearchState(state: SearchState, action: SearchAction): SearchState {
  switch (action.type) {
    case 'searchChanged':
      return {
        ...state,
        search: action.search,
        searchResults: action.search.trim() ? state.searchResults : [],
      };
    case 'searchStarted':
      return { ...state, isSearching: true };
    case 'searchSucceeded':
      return { ...state, isSearching: false, searchResults: action.results };
    case 'searchFailed':
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
    search: '',
    isSearching: false,
    searchResults: [],
  });

  const setSearch = useCallback<Dispatch<SetStateAction<string>>>(
    (nextSearch) => {
      dispatch({
        type: 'searchChanged',
        search: typeof nextSearch === 'function' ? nextSearch(search) : nextSearch,
      });
    },
    [search],
  );

  const runSearch = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (!search.trim()) {
        dispatch({ type: 'searchChanged', search });
        return;
      }
      dispatch({ type: 'searchStarted' });
      try {
        const response = await api.search(projectId, search);
        dispatch({ type: 'searchSucceeded', results: response.results });
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Search failed.');
        dispatch({ type: 'searchFailed' });
      }
    },
    [projectId, search, setError],
  );

  return { search, setSearch, isSearching, searchResults, runSearch };
}
