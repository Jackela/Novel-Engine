import { Loader2, Search } from "lucide-react";
import type { FormEvent } from "react";

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
          aria-label="Search project"
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search documents"
          readOnly={isSearching}
          value={search}
        />
      </form>
      {searchResults.length ? (
        <section aria-label="Search results" className="studio-nav__search-results">
          {searchResults.map((result) => (
            <button
              aria-label={`Open ${result.title}`}
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
