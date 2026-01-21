/**
 * CharacterForm - Form for creating/editing characters
 */
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import type { CharacterDetail, CreateCharacterInput } from '@/shared/types/character';
import { WorkspaceCharacterCreateSchema } from '@/types/schemas';

interface CharacterFormProps {
  character?: CharacterDetail;
  onSubmit: (data: CreateCharacterInput) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const emptyDefaults: CreateCharacterInput = {
  agent_id: '',
  name: '',
  background_summary: '',
  personality_traits: '',
  skills: {},
  relationships: {},
  current_location: '',
  inventory: [],
  metadata: {},
  structured_data: {},
};

export function CharacterForm({
  character,
  onSubmit,
  onCancel,
  isLoading = false,
}: CharacterFormProps) {
  const form = useForm<CreateCharacterInput>({
    resolver: zodResolver(WorkspaceCharacterCreateSchema),
    defaultValues: character
      ? {
          ...emptyDefaults,
          agent_id: character.agent_id,
          name: character.name,
          background_summary: character.background_summary,
          personality_traits: character.personality_traits,
          current_location: character.current_location,
          inventory: character.inventory,
          skills: character.skills,
          relationships: character.relationships,
          metadata: character.metadata,
          structured_data: character.structured_data,
        }
      : emptyDefaults,
    mode: 'onBlur',
  });

  const inventoryFieldArray = useFieldArray({
    control: form.control,
    name: 'inventory',
  });

  const handleAddInventory = () => {
    inventoryFieldArray.append('');
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="agent_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Agent ID</FormLabel>
              <FormControl>
                <Input placeholder="unique-agent-id" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="Character name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="background_summary"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Background Summary</FormLabel>
              <FormControl>
                <Textarea rows={4} placeholder="Short background summary" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="personality_traits"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Personality Traits</FormLabel>
              <FormControl>
                <Textarea rows={3} placeholder="Traits and temperament" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="current_location"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Current Location</FormLabel>
              <FormControl>
                <Input placeholder="Current location" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <FormLabel>Inventory</FormLabel>
            <Button type="button" variant="outline" size="sm" onClick={handleAddInventory}>
              Add Item
            </Button>
          </div>
          {inventoryFieldArray.fields.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No inventory items yet.
            </p>
          ) : (
            <div className="space-y-2">
              {inventoryFieldArray.fields.map((field, index) => (
                <FormField
                  key={field.id}
                  control={form.control}
                  name={`inventory.${index}`}
                  render={({ field: itemField }) => (
                    <FormItem>
                      <FormControl>
                        <Input placeholder="Item name" {...itemField} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" loading={isLoading}>
            {character ? 'Update' : 'Create'} Character
          </Button>
        </div>
      </form>
    </Form>
  );
}
