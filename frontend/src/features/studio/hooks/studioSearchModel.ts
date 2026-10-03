import { useSearchReveal } from "./useSearchReveal";
import { useStudioSearch } from "./useStudioSearch";

/**
 * DR-029 search wiring for the page model: the search hook's state (results,
 * honest total, paging) plus the reveal intent minted when a hit is clicked.
 * Splitting it out keeps `useStudioPageModel` inside the file-size budget.
 */
export function useStudioSearchModel(
  projectId: string,
  publishError: Parameters<typeof useStudioSearch>[1],
  setActiveId: (documentId: string) => void,
) {
  const {
    search,
    setSearch,
    isSearching,
    searchResults,
    searchTotal,
    hasMoreResults,
    isLoadingMoreResults,
    searchedEmpty,
    runSearch,
    loadMoreResults,
  } = useStudioSearch(projectId, publishError);
  const { reveal, requestReveal } = useSearchReveal();
  const onSelectResult = (result: Parameters<typeof requestReveal>[0]) => {
    setActiveId(result.document_id);
    requestReveal(result);
  };
  return {
    reveal,
    model: {
      search,
      isSearching,
      searchResults,
      searchTotal,
      // DR-029: the paging/empty flags travel as one object (NavigatorSearchState).
      searchState: {
        hasMoreResults,
        isLoadingMore: isLoadingMoreResults,
        searchedEmpty,
      },
      onSearchChange: setSearch,
      onSearchSubmit: runSearch,
      onSelectResult,
      onLoadMore: loadMoreResults,
    },
  };
}
