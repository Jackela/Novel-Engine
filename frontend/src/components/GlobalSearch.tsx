/**
 * GlobalSearch - Quick access command palette (Cmd+K / Ctrl+K).
 *
 * Why: Provides fast keyboard-driven search and navigation across the entire
 * world knowledge base (Characters, Locations, Lore, Chapters). Based on cmdk
 * for the command palette pattern used by Vercel, Linear, and other modern apps.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Users, MapPin, Book, FileText, Clock, Search, Loader2 } from 'lucide-react';
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from '@/components/ui/command';
import type {
  CharacterSummary,
  WorldLocation,
  LoreEntryResponse,
  ChapterResponse,
} from '@/types/schemas';

// ============ Types ============

interface SearchItem {
  id: string;
  name: string;
  type: 'character' | 'location' | 'lore' | 'chapter';
  description?: string | undefined;
  navigateTo: string;
}

interface RecentSearch {
  id: string;
  name: string;
  type: SearchItem['type'];
  navigateTo: string;
  timestamp: number;
}

type GroupedItems = Record<SearchItem['type'], SearchItem[]>;

// ============ Constants ============

const RECENT_SEARCHES_KEY = 'global-search-recent';
const MAX_RECENT_SEARCHES = 5;
const MAX_RESULTS_PER_GROUP = 5;

const TYPE_ICONS = {
  character: Users,
  location: MapPin,
  lore: Book,
  chapter: FileText,
} as const;

const TYPE_LABELS = {
  character: 'Characters',
  location: 'Locations',
  lore: 'Lore',
  chapter: 'Chapters',
} as const;

// ============ localStorage Utils ============

function loadRecentSearches(): RecentSearch[] {
  try {
    const stored = localStorage.getItem(RECENT_SEARCHES_KEY);
    return stored ? (JSON.parse(stored) as RecentSearch[]) : [];
  } catch {
    return [];
  }
}

function saveRecentSearch(item: SearchItem): void {
  try {
    const recent = loadRecentSearches();
    const filtered = recent.filter((r) => !(r.id === item.id && r.type === item.type));
    filtered.unshift({
      id: item.id,
      name: item.name,
      type: item.type,
      navigateTo: item.navigateTo,
      timestamp: Date.now(),
    });
    localStorage.setItem(
      RECENT_SEARCHES_KEY,
      JSON.stringify(filtered.slice(0, MAX_RECENT_SEARCHES))
    );
  } catch {
    // Ignore localStorage errors
  }
}

// ============ Transform Functions ============

function transformCharacters(data: CharacterSummary[]): SearchItem[] {
  return data.map((char) => ({
    id: char.id,
    name: char.name,
    type: 'character',
    description: char.archetype ?? undefined,
    navigateTo: '/characters',
  }));
}

function transformLocations(data: WorldLocation[]): SearchItem[] {
  return data.map((loc) => ({
    id: loc.id,
    name: loc.name,
    type: 'location',
    description: loc.location_type,
    navigateTo: '/world',
  }));
}

function transformLoreEntries(data: LoreEntryResponse[]): SearchItem[] {
  return data.map((entry) => ({
    id: entry.id,
    name: entry.title,
    type: 'lore',
    description: entry.category,
    navigateTo: '/world/wiki',
  }));
}

function transformChapters(data: ChapterResponse[]): SearchItem[] {
  return data.map((chapter) => ({
    id: chapter.id,
    name: chapter.title,
    type: 'chapter',
    description: `Chapter ${chapter.order_index + 1}`,
    navigateTo: '/stories',
  }));
}

// ============ API Fetch ============

async function fetchChaptersForStories(
  stories: { id: string }[]
): Promise<SearchItem[]> {
  const items: SearchItem[] = [];
  const promises = stories.map(async (story) => {
    try {
      const res = await fetch(`/api/structure/stories/${story.id}/chapters`);
      const data = await res.json();
      return (data.chapters || []) as ChapterResponse[];
    } catch {
      return [];
    }
  });
  const results = await Promise.allSettled(promises);
  for (const result of results) {
    if (result.status === 'fulfilled' && result.value.length > 0) {
      items.push(...transformChapters(result.value));
    }
  }
  return items;
}

async function fetchSearchData(): Promise<SearchItem[]> {
  const results = await Promise.allSettled([
    fetch('/api/characters').then((r) => r.json()),
    fetch('/api/locations').then((r) => r.json()),
    fetch('/api/lore').then((r) => r.json()),
    fetch('/api/structure/stories').then((r) => r.json()),
  ]);

  const items: SearchItem[] = [];

  if (results[0].status === 'fulfilled' && results[0].value.characters) {
    items.push(...transformCharacters(results[0].value.characters));
  }
  if (results[1].status === 'fulfilled' && results[1].value.locations) {
    items.push(...transformLocations(results[1].value.locations));
  }
  if (results[2].status === 'fulfilled' && results[2].value.entries) {
    items.push(...transformLoreEntries(results[2].value.entries));
  }
  if (results[3].status === 'fulfilled') {
    const stories = results[3].value.stories;
    if (stories && Array.isArray(stories)) {
      items.push(...(await fetchChaptersForStories(stories)));
    }
  }

  return items;
}

// ============ Sub-Components ============

function SearchItemRow({ item, onSelect }: { item: SearchItem; onSelect: () => void }) {
  const Icon = TYPE_ICONS[item.type];
  return (
    <CommandItem
      value={`${item.type}-${item.id}-${item.name}-${item.description ?? ''}`}
      onSelect={onSelect}
      className="flex items-center gap-3 py-3"
    >
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="truncate font-medium">{item.name}</span>
        {item.description && (
          <span className="truncate text-xs text-muted-foreground">
            {item.description}
          </span>
        )}
      </div>
    </CommandItem>
  );
}

function RecentSearchItem({
  item,
  onSelect,
}: {
  item: RecentSearch;
  onSelect: () => void;
}) {
  const Icon = TYPE_ICONS[item.type];
  return (
    <CommandItem
      value={`recent-${item.type}-${item.id}-${item.name}`}
      onSelect={onSelect}
      className="flex items-center gap-3 py-2"
    >
      <Clock className="h-4 w-4 shrink-0 text-muted-foreground" />
      <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      <span className="truncate">{item.name}</span>
    </CommandItem>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center gap-2 py-6 text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>Loading...</span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-8 text-muted-foreground">
      <Search className="h-8 w-8" />
      <p className="text-sm">Start typing to search...</p>
      <p className="text-xs">Characters, locations, lore entries, and chapters</p>
    </div>
  );
}

interface SearchResultsProps {
  groups: GroupedItems;
  onSelect: (item: SearchItem) => void;
}

function SearchResults({ groups, onSelect }: SearchResultsProps) {
  const order: SearchItem['type'][] = ['character', 'location', 'lore', 'chapter'];
  const nonEmpty = order.filter((t) => groups[t].length > 0);

  return (
    <>
      {nonEmpty.map((type, idx) => (
        <div key={type}>
          {idx > 0 && <CommandSeparator />}
          <CommandGroup heading={TYPE_LABELS[type]}>
            {groups[type].slice(0, MAX_RESULTS_PER_GROUP).map((item) => (
              <SearchItemRow
                key={`${type}-${item.id}`}
                item={item}
                onSelect={() => onSelect(item)}
              />
            ))}
          </CommandGroup>
        </div>
      ))}
    </>
  );
}

interface SearchContentProps {
  isLoading: boolean;
  hasResults: boolean;
  showRecent: boolean;
  hasSearchQuery: boolean;
  recentSearches: RecentSearch[];
  groupedItems: GroupedItems;
  onSelect: (item: SearchItem | RecentSearch) => void;
}

function SearchContent({
  isLoading,
  hasResults,
  showRecent,
  hasSearchQuery,
  recentSearches,
  groupedItems,
  onSelect,
}: SearchContentProps) {
  if (isLoading) return <LoadingState />;

  if (!hasResults && !showRecent && hasSearchQuery) {
    return <CommandEmpty>No results found.</CommandEmpty>;
  }

  if (showRecent) {
    return (
      <CommandGroup heading="Recent Searches">
        {recentSearches.map((item) => (
          <RecentSearchItem
            key={`recent-${item.type}-${item.id}`}
            item={item}
            onSelect={() => onSelect(item)}
          />
        ))}
      </CommandGroup>
    );
  }

  if (!hasResults && !hasSearchQuery) return <EmptyState />;

  if (hasResults) return <SearchResults groups={groupedItems} onSelect={onSelect} />;

  return null;
}

// ============ Custom Hook ============

function useGlobalSearchState() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    setRecentSearches(loadRecentSearches());
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || e.key === 'K') {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const handleSelect = useCallback(
    (item: SearchItem | RecentSearch) => {
      saveRecentSearch({
        id: item.id,
        name: item.name,
        type: item.type,
        description: undefined,
        navigateTo: item.navigateTo,
      });
      setRecentSearches(loadRecentSearches());
      navigate({ to: item.navigateTo });
      setOpen(false);
      setSearch('');
    },
    [navigate]
  );

  return { open, setOpen, search, setSearch, recentSearches, handleSelect };
}

// ============ Main Component ============

export function GlobalSearch() {
  const { open, setOpen, search, setSearch, recentSearches, handleSelect } =
    useGlobalSearchState();

  const shouldPrefetch = (() => {
    if (typeof window === 'undefined') return false;
    try {
      return window.localStorage.getItem('e2e_bypass_auth') === '1';
    } catch {
      return false;
    }
  })();

  const { data: searchItems = [], isLoading } = useQuery({
    queryKey: ['global-search'],
    queryFn: fetchSearchData,
    enabled: open || shouldPrefetch,
    staleTime: 60000,
  });

  const filteredItems = useMemo(() => {
    if (!search.trim()) return [];
    const q = search.toLowerCase();
    return searchItems.filter(
      (i) =>
        i.name.toLowerCase().includes(q) || i.description?.toLowerCase().includes(q)
    );
  }, [searchItems, search]);

  const groupedItems = useMemo<GroupedItems>(() => {
    const g: GroupedItems = { character: [], location: [], lore: [], chapter: [] };
    for (const item of filteredItems) g[item.type].push(item);
    return g;
  }, [filteredItems]);

  const hasResults = Object.values(groupedItems).some((g) => g.length > 0);
  const showRecent = !search.trim() && recentSearches.length > 0;
  const hasSearchQuery = !!search.trim();

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput
        placeholder="Search characters, locations, lore, chapters..."
        value={search}
        onValueChange={setSearch}
        autoFocus
        data-testid="global-search-input"
      />
      <CommandList>
        <SearchContent
          isLoading={isLoading}
          hasResults={hasResults}
          showRecent={showRecent}
          hasSearchQuery={hasSearchQuery}
          recentSearches={recentSearches}
          groupedItems={groupedItems}
          onSelect={handleSelect}
        />
      </CommandList>
    </CommandDialog>
  );
}

export default GlobalSearch;
