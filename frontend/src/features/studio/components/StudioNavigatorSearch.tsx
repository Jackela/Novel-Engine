import { Loader2, Search } from "lucide-react";
import type { FormEvent } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

interface SearchResult {
  document_id: string;
  title: string;
  excerpt: string;
}

interface StudioNavigatorSearchProps {
  search: string;
  isSearching: boolean;
  searchResults: SearchResult[];
  onSearchChange: (value: string) => void;
  onSearchSubmit: (event: FormEvent) => void;
  onSelectDocument: (documentId: string) => void;
}

/** The Navigator's project search input and its results list. */
export function StudioNavigatorSearch({
  search,
  isSearching,
  searchResults,
  onSearchChange,
  onSearchSubmit,
  onSelectDocument,
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
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={t("navigator.search.placeholder")}
          readOnly={isSearching}
          value={search}
        />
      </form>
      {searchResults.length ? (
        <section aria-label={t("navigator.search.results")} className="studio-nav__search-results">
          {searchResults.map((result) => (
            <button
              aria-label={t("navigator.search.open", { title: result.title })}
              key={result.document_id}
              onClick={() => onSelectDocument(result.document_id)}
              type="button"
            >
              <strong>{result.title}</strong>
              <span>{result.excerpt}</span>
            </button>
          ))}
        </section>
      ) : null}
    </>
  );
}
