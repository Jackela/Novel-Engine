/**
 * WikiDashboard - Central database view for all world knowledge.
 *
 * Displays a unified table of Lore entries, Characters, Locations, and Items
 * with search and filtering capabilities. This serves as the "knowledge base"
 * for the narrative world.
 */
import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Search, Book, Users, MapPin, Package, Clock } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/components/ui/Card';
import { LoadingSpinner } from '@/shared/components/feedback';
import type {
  CharacterSummary,
  WorldLocation,
  ItemResponse,
  LoreEntryResponse,
} from '@/types/schemas';

/**
 * Entry types that can be displayed in the wiki.
 */
type WikiEntryType = 'all' | 'lore' | 'character' | 'location' | 'item';

/**
 * Unified wiki entry for display in the table.
 */
interface WikiEntry {
  id: string;
  name: string;
  type: WikiEntryType;
  tags: string[];
  updatedAt: string;
  subtype?: string | undefined;
}

const TYPE_ICONS: Record<Exclude<WikiEntryType, 'all'>, typeof Book> = {
  lore: Book,
  character: Users,
  location: MapPin,
  item: Package,
};

const TYPE_LABELS: Record<Exclude<WikiEntryType, 'all'>, string> = {
  lore: 'Lore',
  character: 'Character',
  location: 'Location',
  item: 'Item',
};

const TYPE_BADGE_VARIANTS: Record<Exclude<WikiEntryType, 'all'>, string> = {
  lore: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
  character: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  location: 'bg-green-500/10 text-green-600 dark:text-green-400',
  item: 'bg-orange-500/10 text-orange-600 dark:text-orange-400',
};

function transformLoreEntries(data: LoreEntryResponse[]): WikiEntry[] {
  return data.map((entry) => ({
    id: entry.id,
    name: entry.title,
    type: 'lore' as const,
    tags: entry.tags,
    updatedAt: entry.updated_at,
    subtype: entry.category,
  }));
}

function transformCharacters(data: CharacterSummary[]): WikiEntry[] {
  return data.map((char) => ({
    id: char.id,
    name: char.name,
    type: 'character' as const,
    tags: char.traits || [],
    updatedAt: char.updated_at,
    subtype: char.archetype ?? undefined,
  }));
}

function transformLocations(data: WorldLocation[]): WikiEntry[] {
  return data.map((loc) => ({
    id: loc.id,
    name: loc.name,
    type: 'location' as const,
    tags: loc.notable_features || [],
    updatedAt: new Date().toISOString(),
    subtype: loc.location_type,
  }));
}

function transformItems(data: ItemResponse[]): WikiEntry[] {
  return data.map((item) => ({
    id: item.id,
    name: item.name,
    type: 'item' as const,
    tags: item.effects || [],
    updatedAt: item.updated_at,
    subtype: item.item_type,
  }));
}

async function fetchWikiData(): Promise<WikiEntry[]> {
  const [loreRes, charactersRes, locationsRes, itemsRes] = await Promise.all([
    fetch('/api/lore').then((r) => r.json()),
    fetch('/api/characters').then((r) => r.json()),
    fetch('/api/locations').then((r) => r.json()),
    fetch('/api/items').then((r) => r.json()),
  ]);

  return [
    ...transformLoreEntries(loreRes.entries || []),
    ...transformCharacters(charactersRes.characters || []),
    ...transformLocations(locationsRes.locations || []),
    ...transformItems(itemsRes.items || []),
  ];
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return 'Unknown';
  }
}

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useMemo(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

interface WikiFiltersProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  typeFilter: WikiEntryType;
  onTypeChange: (value: WikiEntryType) => void;
}

function WikiFilters({ searchQuery, onSearchChange, typeFilter, onTypeChange }: WikiFiltersProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Search & Filter</CardTitle>
        <CardDescription>Find entries across all categories</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-4 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name, tags, or type..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-9"
              data-testid="wiki-search-input"
            />
          </div>
          <Select value={typeFilter} onValueChange={(v) => onTypeChange(v as WikiEntryType)}>
            <SelectTrigger className="w-full sm:w-[180px]" data-testid="wiki-type-filter">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="lore">Lore</SelectItem>
              <SelectItem value="character">Characters</SelectItem>
              <SelectItem value="location">Locations</SelectItem>
              <SelectItem value="item">Items</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}

interface WikiTableRowProps {
  entry: WikiEntry;
  onClick: () => void;
}

function WikiTableRow({ entry, onClick }: WikiTableRowProps) {
  const Icon = TYPE_ICONS[entry.type as Exclude<WikiEntryType, 'all'>];
  const typeBadgeClass = TYPE_BADGE_VARIANTS[entry.type as Exclude<WikiEntryType, 'all'>];

  return (
    <TableRow
      className="cursor-pointer"
      onClick={onClick}
      data-testid={`wiki-row-${entry.id}`}
    >
      <TableCell className="font-medium">
        <div className="flex items-center gap-2">
          {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
          <span>{entry.name}</span>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant="secondary" className={typeBadgeClass}>
          {TYPE_LABELS[entry.type as Exclude<WikiEntryType, 'all'>]}
          {entry.subtype && <span className="ml-1 opacity-70">/ {entry.subtype}</span>}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1">
          {entry.tags.slice(0, 3).map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
          ))}
          {entry.tags.length > 3 && (
            <Badge variant="outline" className="text-xs">+{entry.tags.length - 3}</Badge>
          )}
        </div>
      </TableCell>
      <TableCell className="text-muted-foreground">{formatDate(entry.updatedAt)}</TableCell>
    </TableRow>
  );
}

export default function WikiDashboard() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<WikiEntryType>('all');
  const debouncedSearch = useDebounce(searchQuery, 300);

  const { data: entries = [], isLoading, error } = useQuery({
    queryKey: ['wiki-entries'],
    queryFn: fetchWikiData,
    staleTime: 30000,
  });

  const filteredEntries = useMemo(() => {
    let filtered = entries;
    if (typeFilter !== 'all') {
      filtered = filtered.filter((entry) => entry.type === typeFilter);
    }
    if (debouncedSearch) {
      const query = debouncedSearch.toLowerCase();
      filtered = filtered.filter(
        (e) => e.name.toLowerCase().includes(query) ||
          e.tags.some((t) => t.toLowerCase().includes(query)) ||
          (e.subtype?.toLowerCase().includes(query) ?? false)
      );
    }
    return [...filtered].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  }, [entries, typeFilter, debouncedSearch]);

  const handleRowClick = useCallback((entry: WikiEntry) => {
    navigate({ to: entry.type === 'character' ? '/characters' : '/world' });
  }, [navigate]);

  if (isLoading) return <LoadingSpinner text="Loading wiki..." />;
  if (error) {
    return (
      <Card><CardContent className="py-8 text-center">
        <p className="text-muted-foreground">Failed to load wiki data.</p>
      </CardContent></Card>
    );
  }

  return (
    <div className="space-y-6" data-testid="wiki-dashboard">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">World Wiki</h1>
        <p className="text-muted-foreground">Central knowledge base for your narrative world</p>
      </div>
      <WikiFilters searchQuery={searchQuery} onSearchChange={setSearchQuery} typeFilter={typeFilter} onTypeChange={setTypeFilter} />
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>Showing {filteredEntries.length} of {entries.length} entries</span>
      </div>
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[300px]">Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Tags</TableHead>
              <TableHead className="w-[140px]">
                <div className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />Last Updated</div>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEntries.length === 0 ? (
              <TableRow><TableCell colSpan={4} className="h-24 text-center">No entries found.</TableCell></TableRow>
            ) : (
              filteredEntries.map((entry) => (
                <WikiTableRow key={`${entry.type}-${entry.id}`} entry={entry} onClick={() => handleRowClick(entry)} />
              ))
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
