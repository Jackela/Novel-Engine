import { useMemo, useState } from 'react';
import { Loader2, Film } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useSceneGeneration } from '../hooks/useSceneGeneration';

type SceneGenerationDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedCharacterNodeId: string | null;
  selectedCharacterName?: string | undefined;
};

const sceneTypeOptions = [
  { value: 'opening', label: 'Opening' },
  { value: 'action', label: 'Action' },
  { value: 'dialogue', label: 'Dialogue' },
  { value: 'climax', label: 'Climax' },
  { value: 'resolution', label: 'Resolution' },
];

const toneOptions = [
  { value: 'auto', label: 'Auto' },
  { value: 'hopeful', label: 'Hopeful' },
  { value: 'noir', label: 'Noir' },
  { value: 'mystical', label: 'Mystical' },
  { value: 'gritty', label: 'Gritty' },
  { value: 'playful', label: 'Playful' },
];

export function SceneGenerationDialog({
  open,
  onOpenChange,
  selectedCharacterNodeId,
  selectedCharacterName,
}: SceneGenerationDialogProps) {
  const generation = useSceneGeneration();
  const [sceneType, setSceneType] = useState('opening');
  const [tone, setTone] = useState('auto');

  const canSubmit = useMemo(
    () => sceneType.length > 0 && selectedCharacterNodeId !== null,
    [sceneType, selectedCharacterNodeId]
  );

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || generation.isPending || !selectedCharacterNodeId) return;

    const toneValue = tone === 'auto' ? undefined : tone;

    generation.mutate({
      sourceNodeId: selectedCharacterNodeId,
      sceneType: sceneType,
      tone: toneValue,
    });

    setSceneType('opening');
    setTone('auto');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Film className="h-4 w-4 text-primary" />
            Generate Scene
          </DialogTitle>
          <DialogDescription>
            {selectedCharacterName
              ? `Generate a scene featuring ${selectedCharacterName}.`
              : 'Select a character node to generate a scene.'}
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="scene-type">Scene Type</Label>
            <Select value={sceneType} onValueChange={setSceneType}>
              <SelectTrigger id="scene-type">
                <SelectValue placeholder="Select scene type" />
              </SelectTrigger>
              <SelectContent>
                {sceneTypeOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="scene-tone">Tone</Label>
            <Select value={tone} onValueChange={setTone}>
              <SelectTrigger id="scene-tone">
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
