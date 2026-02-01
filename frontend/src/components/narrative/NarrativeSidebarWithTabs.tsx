/**
 * NarrativeSidebarWithTabs - Tabbed sidebar with Outline and World views.
 *
 * Why: Integrates world entities (characters, locations) into the narrative editor
 * sidebar, allowing writers to reference and insert world elements while writing.
 * Uses lazy loading for world data to minimize initial load time.
 */
import { useState, useCallback } from 'react';
import { FileText, Globe } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { NarrativeSidebar, type OutlinerChapter, type SceneMoveResult } from './NarrativeSidebar';
import { WorldSidebarTab } from './WorldSidebarTab';
import { useWorldSidebarData } from '@/lib/api/worldDataApi';

interface NarrativeSidebarWithTabsProps {
  /** List of chapters with their nested scenes */
  chapters: OutlinerChapter[];
  /** Currently selected scene ID */
  activeSceneId?: string | undefined;
  /** Called when a scene is selected */
  onSceneSelect?: ((sceneId: string, chapterId: string) => void) | undefined;
  /** Called when a scene is moved (for API integration) */
  onSceneMove?: ((result: SceneMoveResult) => void) | undefined;
  /** Called when a character is selected in the World tab */
  onCharacterSelect?: ((characterId: string) => void) | undefined;
  /** Called when a location is selected in the World tab */
  onLocationSelect?: ((locationId: string) => void) | undefined;
  /** Additional CSS classes */
  className?: string | undefined;
}

/** Tab header with triggers */
function TabHeader() {
  return (
    <div className="border-b border-border px-2 pt-2">
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="outline" className="text-xs">
          <FileText className="mr-1.5 h-3.5 w-3.5" />
          Outline
        </TabsTrigger>
        <TabsTrigger value="world" className="text-xs">
          <Globe className="mr-1.5 h-3.5 w-3.5" />
          World
        </TabsTrigger>
      </TabsList>
    </div>
  );
}

/** Outline tab content wrapper */
interface OutlineTabContentProps {
  chapters: OutlinerChapter[];
  activeSceneId?: string | undefined;
  onSceneSelect?: ((sceneId: string, chapterId: string) => void) | undefined;
  onSceneMove?: ((result: SceneMoveResult) => void) | undefined;
}

function OutlineTabContent({
  chapters,
  activeSceneId,
  onSceneSelect,
  onSceneMove,
}: OutlineTabContentProps) {
  const sceneCount = chapters.reduce((acc, ch) => acc + ch.scenes.length, 0);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-2">
        <p className="text-xs text-muted-foreground">
          {chapters.length} chapter{chapters.length !== 1 ? 's' : ''} ·{' '}
          {sceneCount} scene{sceneCount !== 1 ? 's' : ''}
        </p>
      </div>
      <div className="flex-1 overflow-hidden">
        <NarrativeSidebar
          chapters={chapters}
          activeSceneId={activeSceneId}
          onSceneSelect={onSceneSelect}
          onSceneMove={onSceneMove}
          className="h-full border-r-0"
        />
      </div>
    </div>
  );
}

/** World tab content wrapper */
interface WorldTabContentProps {
  hasLoadedWorld: boolean;
  worldData: ReturnType<typeof useWorldSidebarData>;
  selectedCharacterId: string | null;
  selectedLocationId: string | null;
  onCharacterSelect: (id: string) => void;
  onLocationSelect: (id: string) => void;
}

function WorldTabContent({
  hasLoadedWorld,
  worldData,
  selectedCharacterId,
  selectedLocationId,
  onCharacterSelect,
  onLocationSelect,
}: WorldTabContentProps) {
  const worldCounts = hasLoadedWorld && !worldData.isLoading
    ? `${worldData.characters.length} characters, ${worldData.locations.length} locations`
    : 'Loading...';

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-2">
        <p className="text-xs text-muted-foreground">{worldCounts}</p>
      </div>
      <WorldSidebarTab
        characters={worldData.characters}
        locations={worldData.locations}
        isLoading={!hasLoadedWorld || worldData.isLoading}
        selectedCharacterId={selectedCharacterId}
        selectedLocationId={selectedLocationId}
        onCharacterSelect={onCharacterSelect}
        onLocationSelect={onLocationSelect}
        className="flex-1"
      />
    </div>
  );
}

/**
 * NarrativeSidebarWithTabs provides a tabbed interface combining the story outline
 * and world entities into a unified sidebar experience.
 */
export function NarrativeSidebarWithTabs({
  chapters,
  activeSceneId,
  onSceneSelect,
  onSceneMove,
  onCharacterSelect,
  onLocationSelect,
  className,
}: NarrativeSidebarWithTabsProps) {
  const [activeTab, setActiveTab] = useState<string>('outline');
  const [hasLoadedWorld, setHasLoadedWorld] = useState(false);
  const [selectedCharacterId, setSelectedCharacterId] = useState<string | null>(null);
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(null);

  const worldData = useWorldSidebarData({ enabled: hasLoadedWorld });

  const handleTabChange = useCallback((value: string) => {
    setActiveTab(value);
    if (value === 'world' && !hasLoadedWorld) {
      setHasLoadedWorld(true);
    }
  }, [hasLoadedWorld]);

  const handleCharacterSelect = useCallback((id: string) => {
    setSelectedCharacterId(id);
    onCharacterSelect?.(id);
  }, [onCharacterSelect]);

  const handleLocationSelect = useCallback((id: string) => {
    setSelectedLocationId(id);
    onLocationSelect?.(id);
  }, [onLocationSelect]);

  return (
    <aside
      className={cn(
        'flex h-full flex-col border-r border-border bg-background',
        className
      )}
      data-testid="narrative-sidebar-with-tabs"
    >
      <Tabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="flex h-full flex-col"
      >
        <TabHeader />
        <TabsContent value="outline" className="m-0 flex-1 overflow-hidden">
          <OutlineTabContent
            chapters={chapters}
            activeSceneId={activeSceneId}
            onSceneSelect={onSceneSelect}
            onSceneMove={onSceneMove}
          />
        </TabsContent>
        <TabsContent value="world" className="m-0 flex-1 overflow-hidden">
          <WorldTabContent
            hasLoadedWorld={hasLoadedWorld}
            worldData={worldData}
            selectedCharacterId={selectedCharacterId}
            selectedLocationId={selectedLocationId}
            onCharacterSelect={handleCharacterSelect}
            onLocationSelect={handleLocationSelect}
          />
        </TabsContent>
      </Tabs>
    </aside>
  );
}

export default NarrativeSidebarWithTabs;
