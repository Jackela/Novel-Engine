import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Download, Loader2 } from 'lucide-react';
import type { CharacterDetail } from '@/shared/types/character';
import InventoryTab from './components/InventoryTab';
import MemoryTimeline from './components/MemoryTimeline';
import PsychologyChart from './components/PsychologyChart';
import GoalsList from './components/GoalsList';
import {
  getCharacterRelationships,
  buildCharacterExportData,
  downloadAsJson,
} from '@/lib/api';

type Props = {
  open: boolean;
  onClose: () => void;
  character: CharacterDetail | null;
};

export default function CharacterDetailsDialog({ open, onClose, character }: Props) {
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    if (!character) return;

    setIsExporting(true);
    try {
      // Fetch relationships for this character
      const relationshipData = await getCharacterRelationships(character.agent_id);

      // Build export data with character and relationships
      const exportData = buildCharacterExportData(
        character,
        relationshipData.relationships
      );

      // Generate filename from character name (sanitized)
      const sanitizedName = character.name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      const filename = `character-${sanitizedName}-${new Date().toISOString().split('T')[0]}`;

      // Trigger download
      downloadAsJson(exportData, filename);
    } catch (error) {
      console.error('Failed to export character:', error);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader className="flex flex-row items-center justify-between gap-4">
          <DialogTitle>{character?.name || 'Character Details'}</DialogTitle>
          {character && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={isExporting}
              className="shrink-0"
            >
              {isExporting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Export
            </Button>
          )}
        </DialogHeader>

        {character ? (
          <Tabs defaultValue="profile" className="w-full">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="profile">Profile</TabsTrigger>
              <TabsTrigger value="psychology">Psychology</TabsTrigger>
              <TabsTrigger value="memories">Memories</TabsTrigger>
              <TabsTrigger value="goals">Goals</TabsTrigger>
              <TabsTrigger value="inventory">Inventory</TabsTrigger>
            </TabsList>

            <TabsContent value="profile" className="mt-4">
              <div className="space-y-6 text-sm">
                <section className="space-y-2">
                  <div className="text-muted-foreground">Agent ID</div>
                  <div className="font-medium">{character.agent_id}</div>
                </section>

                <section className="space-y-2">
                  <div className="text-muted-foreground">Background Summary</div>
                  <div>{character.background_summary || 'No summary provided.'}</div>
                </section>

                <section className="space-y-2">
                  <div className="text-muted-foreground">Personality Traits</div>
                  <div>{character.personality_traits || 'No traits provided.'}</div>
                </section>

                <section className="space-y-2">
                  <div className="text-muted-foreground">Current Location</div>
                  <div>{character.current_location || 'Unknown'}</div>
                </section>

                <section className="space-y-2">
                  <div className="text-muted-foreground">Skills</div>
                  <div className="flex flex-wrap gap-2">
                    {Object.keys(character.skills || {}).length === 0 ? (
                      <span className="text-muted-foreground">No skills recorded.</span>
                    ) : (
                      Object.entries(character.skills).map(([skill, value]) => (
                        <Badge key={skill} variant="outline">
                          {skill}: {value}
                        </Badge>
                      ))
                    )}
                  </div>
                </section>

                <section className="space-y-2">
                  <div className="text-muted-foreground">Relationships</div>
                  <div className="flex flex-wrap gap-2">
                    {Object.keys(character.relationships || {}).length === 0 ? (
                      <span className="text-muted-foreground">
                        No relationships recorded.
                      </span>
                    ) : (
                      Object.entries(character.relationships).map(
                        ([relation, value]) => (
                          <Badge key={relation} variant="secondary">
                            {relation}: {value}
                          </Badge>
                        )
                      )
                    )}
                  </div>
                </section>
              </div>
            </TabsContent>

            <TabsContent value="psychology" className="mt-4">
              <PsychologyChart psychology={character.psychology} />
            </TabsContent>

            <TabsContent value="memories" className="mt-4">
              <MemoryTimeline memories={character.memories} />
            </TabsContent>

            <TabsContent value="goals" className="mt-4">
              <GoalsList goals={character.goals} />
            </TabsContent>

            <TabsContent value="inventory" className="mt-4">
              <InventoryTab characterId={character.character_id} />
            </TabsContent>
          </Tabs>
        ) : (
          <p className="text-sm text-muted-foreground">No character selected.</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
