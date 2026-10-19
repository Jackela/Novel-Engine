import type { NavigateFunction } from "react-router-dom";

import type { Project } from "@/app/types/studio";
import { type StudioRouteState, studioInspectorPath } from "../studioRouteState";
import { documentKindForSection } from "./useActiveDocument";
import { useSearchReveal } from "./useSearchReveal";
import { useStudioSearch } from "./useStudioSearch";

interface SearchSelection {
  readonly project: Project | null;
  readonly route: StudioRouteState;
  readonly navigate: NavigateFunction;
  readonly setActiveId: (documentId: string) => void;
}

/**
 * DR-029 search wiring for the page model: the search hook's state (results,
 * honest total, paging) plus the reveal intent minted when a hit is clicked.
 * Splitting it out keeps `useStudioPageModel` inside the file-size budget.
 */
export function useStudioSearchModel(
  projectId: string,
  publishError: Parameters<typeof useStudioSearch>[1],
  { project, route, navigate, setActiveId }: SearchSelection,
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
    const target = project?.documents.find((document) => document.id === result.document_id);
    if (!target) return;
    setActiveId(result.document_id);
    const sectionKind = documentKindForSection(route.section);
    if (sectionKind !== null && target.kind !== sectionKind) {
      void navigate(studioInspectorPath(projectId, "manuscript", route.inspector));
    }
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
