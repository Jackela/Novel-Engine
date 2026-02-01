import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { CharacterDetail } from '@/shared/types/character';
import InventoryTab from './components/InventoryTab';

type Props = {
  open: boolean;
  onClose: () => void;
  character: CharacterDetail | null;
};

export default function CharacterDetailsDialog({ open, onClose, character }: Props) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{character?.name || 'Character Details'}</DialogTitle>
        </DialogHeader>

        {character ? (
          <Tabs defaultValue="profile" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="profile">Profile</TabsTrigger>
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
                      Object.entries(character.relationships).map(([relation, value]) => (
                        <Badge key={relation} variant="secondary">
                          {relation}: {value}
                        </Badge>
                      ))
                    )}
                  </div>
                </section>
              </div>
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
