import { ArrowDown, ArrowUp, FileText, Loader2, Plus, Search } from 'lucide-react';
import type { FormEvent } from 'react';

import type { DocumentKind, Project } from '@/app/types/studio';

import { GROUPS, SECTIONS } from './studioConstants';

interface SearchResult {
  document_id: string;
  title: string;
  excerpt: string;
}

interface StudioNavigatorProps {
  project: Project;
  section: string;
  activeId: string | null;
  search: string;
  isSearching: boolean;
  searchResults: SearchResult[];
  onSearchChange: (value: string) => void;
  onSearchSubmit: (event: FormEvent) => void;
  onNavigateSection: (section: string) => void;
  onSelectDocument: (documentId: string) => void;
  onCreateDocument: (kind: DocumentKind) => void;
  onMoveDocument: (documentId: string, direction: -1 | 1) => void;
}

export function StudioNavigator({
  project,
  section,
  activeId,
  search,
  isSearching,
  searchResults,
  onSearchChange,
  onSearchSubmit,
  onNavigateSection,
  onSelectDocument,
  onCreateDocument,
  onMoveDocument,
}: StudioNavigatorProps) {
  const visibleGroups = GROUPS.flatMap((group) => {
    if (section === 'outline' && group.kind !== 'outline') return [];
    if (section === 'characters' && group.kind !== 'character') return [];
    if (section === 'world' && group.kind !== 'world') return [];
    return [group];
  });

  return (
    <aside className="studio-nav">
      <nav className="section-nav" aria-label="Project sections">
        {SECTIONS.map(([path, label]) => (
          <button
            className={section === path ? 'active' : ''}
            key={path}
            onClick={() => onNavigateSection(path)}
            type="button"
          >
            {label}
          </button>
        ))}
      </nav>
      <form className="studio-search" onSubmit={onSearchSubmit}>
        {isSearching ? <Loader2 className="spin" /> : <Search />}
        <input
          aria-label="Search project"
          disabled={isSearching}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search documents"
          value={search}
        />
      </form>
      {searchResults.length ? (
        <div className="search-results">
          {searchResults.map((result) => (
            <button
              key={result.document_id}
              onClick={() => onSelectDocument(result.document_id)}
              type="button"
            >
              <strong>{result.title}</strong>
              <span>{result.excerpt}</span>
            </button>
          ))}
        </div>
      ) : null}
      <div className="document-tree">
        {visibleGroups.map(({ kind, label, icon: Icon }) => {
          const documents = project.documents?.filter((document) => document.kind === kind) ?? [];
          return (
            <section className="document-group" key={kind}>
              <header>
                <span>
                  <Icon /> {label}
                </span>
                <button onClick={() => onCreateDocument(kind)} title={`Add ${label}`} type="button">
                  <Plus />
                </button>
              </header>
              {documents.map((document, index) => (
                <div className="document-row-wrap" key={document.id}>
                  <button
                    className={
                      document.id === activeId
                        ? 'document-row document-row--active'
                        : 'document-row'
                    }
                    onClick={() => onSelectDocument(document.id)}
                    type="button"
                  >
                    <FileText />
                    <span>{document.title}</span>
                  </button>
                  <span className="document-order">
                    <button
                      disabled={index === 0}
                      onClick={() => onMoveDocument(document.id, -1)}
                      title="Move up"
                      type="button"
                    >
                      <ArrowUp />
                    </button>
                    <button
                      disabled={index === documents.length - 1}
                      onClick={() => onMoveDocument(document.id, 1)}
                      title="Move down"
                      type="button"
                    >
                      <ArrowDown />
                    </button>
                  </span>
                </div>
              ))}
            </section>
          );
        })}
      </div>
    </aside>
  );
}
