import { ArrowDown, ArrowUp, ChevronDown, FileText, Loader2, Plus, Search } from 'lucide-react';
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
  isCreatingDocument?: boolean;
  isMovingDocument?: boolean;
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
  isCreatingDocument = false,
  isMovingDocument = false,
}: StudioNavigatorProps) {
  const visibleGroups = GROUPS.flatMap((group) => {
    if (section === 'outline' && group.kind !== 'outline') return [];
    if (section === 'characters' && group.kind !== 'character') return [];
    if (section === 'world' && group.kind !== 'world') return [];
    return [group];
  });

  return (
    <aside className="studio-nav">
      <details className="studio-nav__disclosure" open>
        <summary className="studio-nav__summary">
          <span>Project navigation</span>
          <ChevronDown aria-hidden="true" />
        </summary>
        <div className="studio-nav__content">
          <nav className="section-nav" aria-label="Project sections">
            {SECTIONS.map(([path, label]) => (
              <button
                aria-current={section === path ? 'page' : undefined}
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
            {isSearching ? (
              <Loader2 aria-hidden="true" className="spin" />
            ) : (
              <Search aria-hidden="true" />
            )}
            <input
              aria-label="Search project"
              disabled={isSearching}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search documents"
              value={search}
            />
          </form>
          {searchResults.length ? (
            <section aria-label="Search results" className="search-results">
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
          <div className="document-tree">
            {visibleGroups.map(({ kind, label, icon: Icon }) => {
              const documents =
                project.documents?.filter((document) => document.kind === kind) ?? [];
              return (
                <section className="document-group" key={kind}>
                  <header>
                    <span>
                      <Icon aria-hidden="true" /> {label}
                    </span>
                    <button
                      aria-busy={isCreatingDocument || undefined}
                      aria-label={isCreatingDocument ? `Adding ${label}` : `Add ${label}`}
                      disabled={isCreatingDocument}
                      onClick={() => onCreateDocument(kind)}
                      title={isCreatingDocument ? `Adding ${label}` : `Add ${label}`}
                      type="button"
                    >
                      {isCreatingDocument ? (
                        <Loader2 aria-hidden="true" className="spin" />
                      ) : (
                        <Plus aria-hidden="true" />
                      )}
                    </button>
                  </header>
                  {documents.map((document, index) => (
                    <div className="document-row-wrap" key={document.id}>
                      <button
                        aria-current={document.id === activeId ? 'page' : undefined}
                        className={
                          document.id === activeId
                            ? 'document-row document-row--active'
                            : 'document-row'
                        }
                        onClick={() => onSelectDocument(document.id)}
                        type="button"
                      >
                        <FileText aria-hidden="true" />
                        <span>{document.title}</span>
                      </button>
                      <span className="document-order" aria-label={`Reorder ${document.title}`}>
                        <button
                          aria-label={`Move ${document.title} up`}
                          aria-busy={isMovingDocument || undefined}
                          disabled={isMovingDocument || index === 0}
                          onClick={() => onMoveDocument(document.id, -1)}
                          title={isMovingDocument ? 'Reordering documents' : 'Move up'}
                          type="button"
                        >
                          <ArrowUp aria-hidden="true" />
                        </button>
                        <button
                          aria-label={`Move ${document.title} down`}
                          aria-busy={isMovingDocument || undefined}
                          disabled={isMovingDocument || index === documents.length - 1}
                          onClick={() => onMoveDocument(document.id, 1)}
                          title={isMovingDocument ? 'Reordering documents' : 'Move down'}
                          type="button"
                        >
                          <ArrowDown aria-hidden="true" />
                        </button>
                      </span>
                    </div>
                  ))}
                </section>
              );
            })}
          </div>
        </div>
      </details>
    </aside>
  );
}
