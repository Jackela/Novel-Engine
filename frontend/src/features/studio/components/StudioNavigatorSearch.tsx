import { Loader2, Search } from "lucide-react";
import type { FormEvent } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

interface SearchResult {
  document_id: string;
  title: string;
  excerpt: string;
  match_term: string;
}

interface StudioNavigatorSearchProps {
  search: string;
  isSearching: boolean;
  searchResults: SearchResult[];
  /** The server's honest project-wide match count of the shown query (DR-029). */
  searchTotal: number;
  hasMoreResults: boolean;
  isLoadingMore: boolean;
  /** A completed search whose query is still typed and found nothing (DR-029). */
  searchedEmpty: boolean;
  onSearchChange: (value: string) => void;
  onSearchSubmit: (event: FormEvent) => void;
  onLoadMore: () => void;
  onSelectResult: (result: SearchResult) => void;
}

/**
 * The Navigator's project search input and its results list (DR-029): a
 * zero-result hint, the honest match count, a "more" affordance while the
 * server reports further pages, and result buttons that open the document
 * and locate the hit through the result's `match_term`.
 */
export function StudioNavigatorSearch({
  search,
  isSearching,
  searchResults,
  searchTotal,
  hasMoreResults,
  isLoadingMore,
  searchedEmpty,
  onSearchChange,
  onSearchSubmit,
  onLoadMore,
  onSelectResult,
}: StudioNavigatorSearchProps) {
  const { t } = useTranslation();
  return (
    <>
      <form
        aria-busy={isSearching}
        className="studio-nav__search"
        onSubmit={(event) => {
          if (isSearching) {
            event.preventDefault();
            return;
          }
          onSearchSubmit(event);
        }}
      >
        {isSearching ? (
          <Loader2 aria-hidden="true" className="ui-spin" />
        ) : (
          <Search aria-hidden="true" />
        )}
        <input
          aria-busy={isSearching}
          aria-label={t("navigator.search.label")}
          maxLength={200}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={t("navigator.search.placeholder")}
          readOnly={isSearching}
          value={search}
        />
      </form>
      {searchResults.length ? (
        <section aria-label={t("navigator.search.results")} className="studio-nav__search-results">
          <p className="studio-nav__search-count">
            {t("navigator.search.count", {
              count: searchTotal,
              unit:
                searchTotal === 1
                  ? t("navigator.search.resultSingular")
                  : t("navigator.search.resultPlural"),
            })}
          </p>
          {searchResults.map((result) => (
            <button
              aria-label={t("navigator.search.open", { title: result.title })}
              key={result.document_id}
              onClick={() => onSelectResult(result)}
              type="button"
            >
              <strong>{result.title}</strong>
              <span>{result.excerpt}</span>
            </button>
          ))}
          {hasMoreResults ? (
            <button
              aria-busy={isLoadingMore || undefined}
              className="studio-nav__search-more"
              disabled={isLoadingMore || isSearching}
              onClick={onLoadMore}
              type="button"
            >
              {isLoadingMore ? <Loader2 aria-hidden="true" className="ui-spin" /> : null}
              {t("navigator.search.more")}
            </button>
          ) : null}
        </section>
      ) : searchedEmpty ? (
        <p className="studio-nav__search-empty" role="status">
          {t("navigator.search.empty")}
        </p>
      ) : null}
    </>
  );
}
