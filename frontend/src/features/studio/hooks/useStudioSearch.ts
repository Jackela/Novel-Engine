import { useCallback, useEffect, useState } from 'react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';

import { api } from '@/app/api';

export function useStudioSearch(
  projectId: string,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const [search, setSearch] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<
    Array<{ document_id: string; title: string; excerpt: string }>
  >([]);

  useEffect(() => {
    if (!search.trim()) {
      setSearchResults([]);
    }
  }, [search]);

  const runSearch = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (!search.trim()) {
        setSearchResults([]);
        return;
      }
      setIsSearching(true);
      try {
        const response = await api.search(projectId, search);
        setSearchResults(response.results);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Search failed.');
      } finally {
        setIsSearching(false);
      }
    },
    [projectId, search, setError],
  );

  return { search, setSearch, isSearching, searchResults, runSearch };
}
