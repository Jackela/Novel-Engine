import { useMemo, useState } from 'react';
import { Loader2, Sparkles } from 'lucide-react';
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui';
import { useCharacterGeneration } from '../hooks/useCharacterGeneration';

type CharacterGenerationDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const toneOptions = [
  { value: 'auto', label: 'Auto' },
  { value: 'hopeful', label: 'Hopeful' },
  { value: 'noir', label: 'Noir' },
  { value: 'mystical', label: 'Mystical' },
  { value: 'gritty', label: 'Gritty' },
  { value: 'playful', label: 'Playful' },
];

export function CharacterGenerationDialog({
  open,
  onOpenChange,
}: CharacterGenerationDialogProps) {
  const generation = useCharacterGeneration();
  const [archetype, setArchetype] = useState('');
  const [tone, setTone] = useState('auto');

  const canSubmit = useMemo(() => archetype.trim().length > 0, [archetype]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || generation.isPending) return;

    const archetypeValue = archetype.trim();
    const toneValue = tone === 'auto' ? undefined : tone;

    generation.mutate({
      concept: archetypeValue,
      archetype: archetypeValue,
      tone: toneValue,
    });

    setArchetype('');
    setTone('auto');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            Generate Character
          </DialogTitle>
          <DialogDescription>
            Define an archetype and tone to synthesize a new Weaver character node.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="archetype">Archetype</Label>
            <Input
              id="archetype"
              placeholder="Wanderer, Mentor, Rebel..."
              value={archetype}
              onChange={(event) => setArchetype(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="tone">Tone</Label>
            <Select value={tone} onValueChange={setTone}>
              <SelectTrigger id="tone">
                <SelectValue placeholder="Select a tone" />
              </SelectTrigger>
              <SelectContent>
                {toneOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={!canSubmit || generation.isPending}>
              {generation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
