/**
 * CharacterForm - Form for creating/editing characters
 */
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button, Input, Label, Badge } from '@/shared/components/ui';
import { useState } from 'react';
import { X, Plus } from 'lucide-react';
import type { Character, CharacterRole, CreateCharacterInput } from '@/shared/types/character';

const characterSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  description: z.string().min(1, 'Description is required').max(1000),
  role: z.enum(['protagonist', 'antagonist', 'supporting', 'minor', 'npc']),
  stats: z.object({
    strength: z.number().min(1).max(20),
    intelligence: z.number().min(1).max(20),
    charisma: z.number().min(1).max(20),
    agility: z.number().min(1).max(20),
    wisdom: z.number().min(1).max(20),
    luck: z.number().min(1).max(20),
  }),
});

type CharacterFormData = z.infer<typeof characterSchema>;

interface CharacterFormProps {
  character?: Character;
  onSubmit: (data: CreateCharacterInput) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const roleOptions: { value: CharacterRole; label: string }[] = [
  { value: 'protagonist', label: 'Protagonist' },
  { value: 'antagonist', label: 'Antagonist' },
  { value: 'supporting', label: 'Supporting' },
  { value: 'minor', label: 'Minor' },
  { value: 'npc', label: 'NPC' },
];

const defaultStats = {
  strength: 10,
  intelligence: 10,
  charisma: 10,
  agility: 10,
  wisdom: 10,
  luck: 10,
};

export function CharacterForm({
  character,
  onSubmit,
  onCancel,
  isLoading = false,
}: CharacterFormProps) {
  const [traits, setTraits] = useState<string[]>(character?.traits || []);
  const [newTrait, setNewTrait] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CharacterFormData>({
    resolver: zodResolver(characterSchema),
    defaultValues: {
      name: character?.name || '',
      description: character?.description || '',
      role: character?.role || 'supporting',
      stats: character?.stats || defaultStats,
    },
  });

  const addTrait = () => {
    if (newTrait.trim() && !traits.includes(newTrait.trim())) {
      setTraits([...traits, newTrait.trim()]);
      setNewTrait('');
    }
  };

  const removeTrait = (trait: string) => {
    setTraits(traits.filter((t) => t !== trait));
  };

  const handleFormSubmit = (data: CharacterFormData) => {
    onSubmit({
      ...data,
      traits,
    });
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* Basic Info */}
      <div className="space-y-4">
        <div>
          <Label htmlFor="name" required>Name</Label>
          <Input
            id="name"
            {...register('name')}
            error={!!errors.name}
            placeholder="Character name"
          />
          {errors.name && (
            <p className="text-sm text-destructive mt-1">{errors.name.message}</p>
          )}
        </div>

        <div>
          <Label htmlFor="description" required>Description</Label>
          <textarea
            id="description"
            {...register('description')}
            className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            placeholder="Describe your character..."
          />
          {errors.description && (
            <p className="text-sm text-destructive mt-1">{errors.description.message}</p>
          )}
        </div>

        <div>
          <Label htmlFor="role" required>Role</Label>
          <select
            id="role"
            {...register('role')}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {roleOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Traits */}
      <div>
        <Label>Traits</Label>
        <div className="flex gap-2 mb-2">
          <Input
            value={newTrait}
            onChange={(e) => setNewTrait(e.target.value)}
            placeholder="Add a trait"
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTrait())}
          />
          <Button type="button" variant="outline" onClick={addTrait}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {traits.map((trait) => (
            <Badge key={trait} variant="secondary" className="pr-1">
              {trait}
              <button
                type="button"
                onClick={() => removeTrait(trait)}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div>
        <Label>Stats</Label>
        <div className="grid grid-cols-3 gap-4">
          {Object.entries(defaultStats).map(([stat]) => (
            <div key={stat}>
              <Label htmlFor={stat} className="text-xs uppercase">
                {stat.slice(0, 3)}
              </Label>
              <Input
                id={stat}
                type="number"
                min={1}
                max={20}
                {...register(`stats.${stat as keyof typeof defaultStats}`, {
                  valueAsNumber: true,
                })}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={isLoading}>
          {character ? 'Update' : 'Create'} Character
        </Button>
      </div>
    </form>
  );
}
